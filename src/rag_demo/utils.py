import os
import yaml
# from PyPDF2 import PdfReader
import streamlit as st
import pymupdf
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
# from langchain.vectorstores import FAISS
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores import Qdrant
from huggingface_hub import InferenceClient
from typing import List
from huggingface_hub import InferenceClient
from langchain.embeddings.base import Embeddings
# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_groq import ChatGroq
# from langchain.chat_models import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.prompts import PromptTemplate
from qdrant_client import QdrantClient
import requests
from typing import Any, List

from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.llm import LLMChain
from langchain.schema import BasePromptTemplate

from langchain.retrievers import ContextualCompressionRetriever
# from langchain.retrievers.document_compressors import CohereRerank
from langchain_cohere import CohereRerank


def load_config(config_path="config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
    
config = load_config()

def get_pdf_text(pdf_docs):
    """
    Based on PyMuPDF for better text extraction then PyPDF2.
    Source: https://pymupdf.readthedocs.io/en/latest/the-basics.html

    See in there how to expand on other document types and images
    """
    text = ""
    for pdf in pdf_docs:
        with pymupdf.open(stream=pdf.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    return text


def get_text_chunks_naive(text):
    """
    Split text into chunks for embedding using LangChain CharacterTextSplitter
    
    Caveats:
    * Naive chunk boundaries: chunks might cut off mid-sentence or mid-thought.
    * Treats all line breaks equally — which ignores paragraph or section logic.
    """
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_text_chunks_recursive(text):
    """
    Split text into chunks for embedding using LangChain RecursiveCharacterTextSplitter
    
    Caveats:
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=2000,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)


# Custom multimodal embedding wrapper
class HFCLIPTextEmbedding(Embeddings):
    def __init__(self, model_name: str, api_token: str):
        self.client = InferenceClient(model=model_name, token=api_token)
    
    def embed_query(self, text: str) -> List[float]:
        return self.client.feature_extraction(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]


# def get_vectorstore(text_chunks):
#     # embeddings = OpenAIEmbeddings()
#     # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl") # said to be better than OpenAIEmbeddings
#     embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") # 384 for all-MiniLM-L6-v2, 768 for all-mpnet-base-v2      
#     vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
#     return vectorstore


def get_vectorstore(text_chunks):
    """
    Create a vector store using Hugging Face Inference API embeddings with fallback.
    
    Args:
        text_chunks (list): List of text chunks to embed
    
    Returns:
        FAISS: A FAISS vector store with embedded text chunks
    """
    # Ensure Hugging Face API token is set
    if 'HUGGINGFACE_API_TOKEN' not in os.environ:
        raise ValueError("Please set the HUGGINGFACE_API_TOKEN environment variable")
    
    # List of models to try in order
    models_to_try = [
        # "intfloat/e5-base-v2",
        "sentence-transformers/clip-ViT-B-32",  # Primary model HF API NOT WORKING AS OF NOW
        "laion/CLIP-ViT-B-32-laion2B-s34B-b79K", # Fallback model HF API NOT WORKING AS OF NOW
        "openai/clip-vit-base-patch32", # Another fallback HF API NOT WORKING AS OF NOW
        "Salesforce/blip-image-captioning-base", # Another fallback HF API NOT WORKING AS OF NOW
        "sentence-transformers/all-MiniLM-L6-v2" # embedding model for TEXT ONLY        
    ]
    
    # Try each model until one works
    for model_name in models_to_try:
        try:
            # # Use LangChain's built-in Hugging Face Inference API Embeddings
            # embeddings = HuggingFaceInferenceAPIEmbeddings(
            #     api_key=os.environ['HUGGINGFACE_API_TOKEN'],
            #     model_name=model_name
            # )

            # Use HuggingFaceHub directly
            embeddings = HFCLIPTextEmbedding(
                model_name=model_name,
                api_token=os.environ['HUGGINGFACE_API_TOKEN']
            )        
            
            # Create and return FAISS vector store
            vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
            print(f"Successfully used model: {model_name}")
            return vectorstore
        
        except Exception as e:
            print(f"Failed to use model {model_name}: {e}")
            continue
    
    # If all models fail
    raise ValueError("Could not create embeddings with any of the specified models")


def build_context_and_references(documents):
    context = "\n\n".join(doc.page_content for doc in documents)

    references = "\n".join(
        f"[{i+1}] {doc.metadata.get('source', 'Unknown Source')}, page {doc.metadata.get('page', 'N/A')}"
        for i, doc in enumerate(documents)
    )

    return context, references


def format_documents(docs):
    context = "\n\n".join(doc.page_content for doc in docs)
    references = "\n".join(
        f"[{i+1}] {doc.metadata.get('source', 'Unknown Source')}, page {doc.metadata.get('page', 'N/A')}"
        for i, doc in enumerate(docs)
    )
    return {"context": context, "references": references}


# Custom prompt template
custom_prompt_template = PromptTemplate.from_template(
    """
    You are a helpful assistant. Use only the following pieces of context to answer the question.

    Please attempt to answer the question based on the context provided. If the context does not contain enough information to answer the question, you can mention that you don't know the answer based on the context.    
    
    --- 
    Context:
    {context}
    ---
    Chat history:
    {chat_history}
    ---
    Question: {question}
    Answer:
    """
)# If you don't know the answer based on the context, say, you can mention this first and then (in a new paragraph), you can generate a concise answer based on your internal knowledge.

# custom_prompt_template = PromptTemplate.from_template("""
# You are a helpful AI assistant answering questions based on context from PDF documents.

# If you don't know the answer based on the context, say, you can mention this first and then you can generate a concise answer based on your internal knowledge.
# When answering, if the answer is based on the context, cite the sources using the academic style [1], [2], etc. Use the reference list provided below, which includes metadata (e.g., file name and page number).

# ---

# CONTEXT:
# {context}

# ---

# CHAT HISTORY:
# {chat_history}

# ---

# QUESTION:
# {question}

# ---

# ANSWER:
# """) 

# custom_prompt_template = PromptTemplate.from_template("""
# You are a helpful AI assistant answering questions based on context from PDF documents.

# If you don't know the answer based on the context, say, you can mention this first and then you can generate a concise answer based on your internal knowledge.
# When answering, if the answer is based on the context, cite the sources using the academic style [1], [2], etc. Use the reference list provided below, which includes metadata (e.g., file name and page number).

# ---

# CONTEXT:
# {context}
                                                      
# ---

# REFERENCES:
# {references}

# ---

# CHAT HISTORY:
# {chat_history}

# ---

# QUESTION:
# {question}

# ---

# ANSWER:
# """)   


def get_conversation_chain(retriever):
    """
    Create conversation chain with Groq LLM and vectorstore.
    """

    # Retrieve the API key from environment variables
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")

    # llm = ChatOllama(model="mistral")
    llm = ChatGroq(
        groq_api_key = groq_api_key,
        # model_name="llama3-8b-8192" , #"mixtral-8x7b-32768" is deprecated,  # Example model; check Groq’s docs for available options
        model_name="llama-3.3-70b-versatile", # longer context: 128K
        temperature=0.5
    )
    
    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
 
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": custom_prompt_template},
    )

    return conversation_chain

# def get_conversation_chain(retriever):
#     groq_api_key = os.getenv("GROQ_API_KEY")
#     if not groq_api_key:
#         raise ValueError("GROQ_API_KEY not found in .env file")

#     llm = ChatGroq(
#         groq_api_key=groq_api_key,
#         model_name="llama-3.3-70b-versatile",
#         temperature=0.5,
#     )

#     memory = ConversationBufferMemory(
#         memory_key='chat_history',
#         return_messages=True
#     )

#     llm_chain = LLMChain(llm=llm, prompt=custom_prompt_template)

#     stuff_chain = StuffDocumentsChain(
#         llm_chain=llm_chain,
#         document_variable_name="context",
#         document_prompt=PromptTemplate.from_template("{page_content}"),  # default
#         # input_variables=["context", "references", "chat_history", "question"]
#     )

#     class CustomStuffChainWrapper:
#         def __init__(self, chain):
#             self.chain = chain

#         def __call__(self, inputs):
#             docs = inputs.pop("docs")
#             formatted = format_documents(docs)
#             return self.chain.run({
#                 **inputs,
#                 **formatted
#             })

#     chain_wrapper = CustomStuffChainWrapper(stuff_chain)

#     return ConversationalRetrievalChain(
#         retriever=retriever,
#         memory=memory,
#         combine_docs_chain=chain_wrapper,
#         return_source_documents=True
#     )


class RemoteEmbeddingsAPI(Embeddings):
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url.rstrip("/") + "/embed"

    def embed_query(self, text: str) -> List[float]:
        response = requests.post(
            self.endpoint_url,
            json={"text": text},
            timeout=10
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

# class QdrantRetriever(BaseRetriever):
#     """Custom retriever for Qdrant that properly handles the text field."""
    
#     def __init__(self, qdrant_client, collection_name, embeddings, k=5):
#         super().__init__()
#         # Use object.__setattr__ to bypass Pydantic validation
#         object.__setattr__(self, 'qdrant_client', qdrant_client)
#         object.__setattr__(self, 'collection_name', collection_name)
#         object.__setattr__(self, 'embeddings', embeddings)
#         object.__setattr__(self, 'k', k)
    
#     def _get_relevant_documents(
#         self, 
#         query: str, 
#         *, 
#         run_manager: CallbackManagerForRetrieverRun = None
#     ) -> List[Document]:
#         # Embed the query
#         query_vector = self.embeddings.embed_query(query)
        
#         # Search in Qdrant
#         search_results = self.qdrant_client.search(
#             collection_name=self.collection_name,
#             query_vector=query_vector,
#             limit=self.k,
#             with_payload=True
#         )
        
#         # Convert to LangChain Documents
#         documents = []
#         for result in search_results:
#             # Extract text content from the payload
#             text_content = result.payload.get("text", "")
            
#             # Create metadata (exclude text content from metadata)
#             metadata = {k: v for k, v in result.payload.items() if k != "text"}
#             metadata["score"] = result.score
            
#             # Create Document object
#             doc = Document(
#                 page_content=text_content,
#                 metadata=metadata
#             )
#             documents.append(doc)
        
#         return documents

# class QdrantRetriever(BaseRetriever):
#     """Custom retriever for Qdrant that handles text field and adds source citation."""

#     def __init__(self, qdrant_client, collection_name, embeddings, k=5):
#         super().__init__()
#         object.__setattr__(self, 'qdrant_client', qdrant_client)
#         object.__setattr__(self, 'collection_name', collection_name)
#         object.__setattr__(self, 'embeddings', embeddings)
#         object.__setattr__(self, 'k', k)

#     def _get_relevant_documents(
#         self,
#         query: str,
#         *,
#         run_manager: CallbackManagerForRetrieverRun = None
#     ) -> List[Document]:
#         # Embed the query
#         query_vector = self.embeddings.embed_query(query)

#         # Search in Qdrant
#         search_results = self.qdrant_client.search(
#             collection_name=self.collection_name,
#             query_vector=query_vector,
#             limit=self.k,
#             with_payload=True
#         )

#         # Convert to LangChain Documents with source citation
#         documents = []
#         for result in search_results:
#             payload = result.payload
#             text_content = payload.get("text", "")

#             # Extract citation metadata
#             source = payload.get("source", "Unknown source")
#             page = payload.get("page", "n/a")

#             # Optional: add score if useful
#             metadata = {k: v for k, v in payload.items() if k != "text"}
#             metadata["score"] = result.score

#             # Embed the source citation into the content
#             formatted_content = f"[Source: {source}, page {page}]\n{text_content}"

#             documents.append(Document(
#                 page_content=formatted_content,
#                 metadata=metadata
#             ))

#         return documents

class QdrantRetriever(BaseRetriever):
    """Retriever that returns documents with metadata for academic-style citations."""

    def __init__(self, qdrant_client, collection_name, embeddings, k=5):
        super().__init__()
        object.__setattr__(self, 'qdrant_client', qdrant_client)
        object.__setattr__(self, 'collection_name', collection_name)
        object.__setattr__(self, 'embeddings', embeddings)
        object.__setattr__(self, 'k', k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        query_vector = self.embeddings.embed_query(query)

        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=self.k,
            with_payload=True
        )

        documents = []
        for idx, result in enumerate(search_results):
            payload = result.payload
            text_content = payload.get("text", "")
            source = payload.get("source", "Unknown source")
            page = payload.get("page", "n/a")

            # Reference number like [1], [2], etc.
            citation_number = f"[{idx + 1}]"

            # Add citation number as suffix to the content
            formatted_content = f"{text_content} {citation_number}"

            metadata = {
                "source": source,
                "page": page,
                "score": result.score,
                "reference_number": citation_number
            }

            documents.append(Document(
                page_content=formatted_content,
                metadata=metadata
            ))

        return documents



def get_qdrant_vectorstore():
    """
    Connect to existing Qdrant vector database and return vectorstore.
    """
    # Load environment variables
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", config["collection"]) 
    # HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
    EMBEDDING_API_URL = os.environ.get("EMBEDDING_API_URL")
    
    if not all([QDRANT_URL, QDRANT_API_KEY, EMBEDDING_API_URL]): #HUGGINGFACE_API_TOKEN
        raise ValueError("Missing required environment variables: QDRANT_URL, QDRANT_API_KEY, EMBEDDING_API_URL")
    # if not EMBEDDING_API_URL:
    #     raise ValueError("Please set the EMBEDDING_API_URL environment variable")

    # # Initialize embedding model (same as used during ingestion)
    # embedding_model = HFCLIPTextEmbedding(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2",
    #     api_token=HUGGINGFACE_API_TOKEN
    # )

    # Initialize embedding model using remote API
    embedding_model = RemoteEmbeddingsAPI(endpoint_url=EMBEDDING_API_URL)    
    
    # Initialize Qdrant client
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # Check if collection exists
    if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        raise ValueError(f"Collection '{COLLECTION_NAME}' does not exist in Qdrant database")
    
    # # Create Qdrant vectorstore
    # vectorstore = Qdrant(
    #     client=qdrant_client,
    #     collection_name=COLLECTION_NAME,
    #     embeddings=embedding_model
    # )

    # Create custom retriever
    retriever = QdrantRetriever(
        qdrant_client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embeddings=embedding_model,
        k=5
    )
    
    return retriever


def get_reranked_qdrant_retriever():
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", config["collection"])
    EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

    if not all([QDRANT_URL, QDRANT_API_KEY, EMBEDDING_API_URL, COHERE_API_KEY]):
        raise ValueError("Missing required environment variables for reranker setup.")

    # Create Qdrant retriever
    embedding_model = RemoteEmbeddingsAPI(endpoint_url=EMBEDDING_API_URL)
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        raise ValueError(f"Collection '{COLLECTION_NAME}' does not exist in Qdrant database")

    base_retriever = QdrantRetriever(
        qdrant_client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embeddings=embedding_model,
        k=25  # Over-retrieve before reranking
    )

    # Setup reranker
    # reranker = CohereRerank(cohere_api_key=COHERE_API_KEY, top_n=5)
    # Add Cohere reranker (v3.0)
    reranker = CohereRerank(
        cohere_api_key=COHERE_API_KEY,
        model="rerank-english-v3.0",
        top_n=5  # final documents to pass to the LLM
    )    
    
    # Wrap retriever
    reranked_retriever = ContextualCompressionRetriever(
        base_retriever=base_retriever,
        base_compressor=reranker
    )

    return reranked_retriever  


def display_database_info():
    """
    Display information about the connected Qdrant database.
    """
    try:
        QDRANT_URL = os.getenv("QDRANT_URL")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        COLLECTION_NAME = os.getenv("COLLECTION_NAME", config["collection"])
        
        if QDRANT_URL and QDRANT_API_KEY:
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            
            if qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
                collection_info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
                points_count = collection_info.points_count
                
                st.success(f"✅ Connected to Qdrant collection: **{COLLECTION_NAME}**")
                st.info(f"📊 Total documents indexed: **{points_count:,}** chunks")
                
                # Get sample of file names
                points, _ = qdrant_client.scroll(
                    collection_name=COLLECTION_NAME, 
                    limit=10,
                    with_payload=True
                )
                
                if points:
                    file_names = set()
                    for point in points:
                        if 'file_name' in point.payload:
                            file_names.add(point.payload['file_name'])
                    
                    if file_names:
                        st.info(f"📄 Sample files: {', '.join(list(file_names)[:5])}")
                        if len(file_names) > 5:
                            st.info(f"... and {len(file_names) - 5} more files")
            else:
                st.error(f"❌ Collection '{COLLECTION_NAME}' not found in database")
        else:
            st.warning("⚠️ Database connection not configured")
            
    except Exception as e:
        st.error(f"❌ Error connecting to database: {str(e)}")
