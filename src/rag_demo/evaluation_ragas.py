import os
import json
from typing import List, Optional, Any
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    answer_correctness
)
from langchain_groq import ChatGroq
from utils import (
    get_qdrant_vectorstore,
    get_reranked_qdrant_retriever,
    get_conversation_chain,
    RemoteEmbeddingsAPI,
)

# Load environment variables
load_dotenv()

# Load dataset
with open("qa_dataset.json", "r", encoding="utf-8") as f:
    qa_dataset = json.load(f)

# Setup retriever and RAG chain
retriever = get_qdrant_vectorstore() # Naive RAG
# retriever = get_reranked_qdrant_retriever() # Reranked RAG
conversation = get_conversation_chain(retriever)

# Initialize Groq LLM for RAGAS evaluation
eval_llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# Initialize Remote Embeddings API for RAGAS evaluation
eval_embeddings = RemoteEmbeddingsAPI(endpoint_url=os.getenv("EMBEDDING_API_URL")) 

# Generate answers and collect contexts
eval_data = {
    "question": [],
    "answer": [],
    "contexts": [],
    "ground_truth": []
}

for item in qa_dataset:
    question = item["question"]
    ground_truth = item.get("ground_truth", item.get("answer"))  # Handle both keys
    
    # Get response from RAG chain
    response = conversation({"question": question})
    generated_answer = response["answer"]
    
    # Get retrieved contexts (assuming retriever returns LangChain-compatible documents)
    retrieved_docs = retriever.get_relevant_documents(question)
    contexts = [doc.page_content for doc in retrieved_docs]
    
    # Store data for evaluation
    eval_data["question"].append(question)
    eval_data["answer"].append(generated_answer)
    eval_data["contexts"].append(contexts)
    eval_data["ground_truth"].append(ground_truth)

# Convert to Hugging Face Dataset
eval_dataset = Dataset.from_dict(eval_data)

# Define metrics for evaluation
metrics = [
    faithfulness,
    answer_relevancy,
    answer_correctness
]

# Run RAGAS evaluation
results = evaluate(
    dataset=eval_dataset,
    metrics=metrics,
    llm=eval_llm,
    embeddings=eval_embeddings
)

# Print results
print("Evaluation Results:")
print(results)