import os
import sys
import json
import pandas as pd
import random

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.api.core.config import config
from src.api.rag.retrieval import rag_pipeline

from langsmith import Client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import openai
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper


os.environ["EVALUATION_MODE"] = "true"
os.environ["GROQ_API_KEY"] = config.GROQ_API_KEY
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # 💡 Add this line to disable LangSmith tracing
os.environ["QDRANT_API_KEY"] = config.QDRANT_API_KEY  # For Qdrant Cloud only
os.environ["QDRANT_URL"] = config.QDRANT_URL

# 0. Set LangSmith & Qdrant clients
ls_client = Client(api_key=config.LANGSMITH_API_KEY)

qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only
)



# 1. Collect some chunks from the Vector DB 

# Deprecated: collect first 50 chunks (not random)
# all_chunks = qdrant_client.scroll(
#     collection_name=config.QDRANT_COLLECTION_NAME,
#     limit=50
# )[0]
# all_chunks

# Randomly sample 50 chunks from the collection for diversity
# 1.1: Get all point IDs from the collection
# A large number like 10,000 should be sufficient for most use cases
all_points = qdrant_client.scroll(
    collection_name=config.QDRANT_COLLECTION_NAME,
    limit=10000,
    with_payload=False, # We don't need the payload for this step
    with_vectors=False # We don't need the vectors either
)[0]

# Extract all point IDs
all_point_ids = [point.id for point in all_points]

# 1.2: Set a seed and randomly sample
random.seed(42)  # 💡 Use any integer as your seed for reproducibility
random_point_ids = random.sample(all_point_ids, 20)

# 1.3: Fetch the randomly selected chunks from Qdrant
# Use the `retrieve` method to get the full points by their IDs
random_chunks = qdrant_client.retrieve(
    collection_name=config.QDRANT_COLLECTION_NAME,
    ids=random_point_ids,
    with_payload=True
)

# You now have your reproducible, random set of 50 chunks
print(f"Randomly selected {len(random_chunks)} chunks.")
print(random_chunks) # Uncomment to see the chunks
print()



# 2. Use LLM to generate synthetic eval data based on the chunks

# 2.1 Grab the text of the chunks
# data_to_embed = [point.payload["text"] for point in random_chunks]
data_to_embed = [{"id": point.id, "text": point.payload["text"]} for point in random_chunks]


print("Chunks used to generate eval dataset:")
print(data_to_embed[0])
print()


# 2.2 Define the JSON schema for the dataset
output_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Suggested question.",
            },
            "chunk_ids": {
                "type": "array",
                "items": {
                    "type": "integer",
                    "description": "Indexes of the chunks used to answer the question.",
                },
            },
            "answer_example": {
                "type": "string",
                "description": "Ground-truth answer based only on the chunks.",
            },
            "reasoning": {
                "type": "string",
                "description": "Why these chunks support the answer.",
            },
        },
    },
}

# 2.3 Define system and user prompts for LLM

SYSTEM_PROMPT = f"""
I am building a Retrieval-Augmented Generation (RAG) application. 
It should answer questions about scientific literature from provided chunks. 

You will receive a list of chunks (with IDs and text).
Your task is to generate 10 evaluation questions.

Guidelines:
- Questions must be grounded in the content of the chunks.
- Provide a diverse set of questions (factual, multi-hop, entity-based, etc).
- At least 2 questions should be unanswerable with the given chunks.
- For each question, provide:
  * The question itself
  * The IDs of chunks that contain the answer
  * An example answer (based only on those chunks)
  * A short reasoning why those chunks support the answer

Return ONLY valid JSON following this schema:

<OUTPUT JSON SCHEMA>
{json.dumps(output_schema, indent=2)}
</OUTPUT JSON SCHEMA>
"""

USER_PROMPT = f"""
Here is the list of chunks:
{data_to_embed}
"""


# 2.4 Generate synthetic eval reference data

response = openai.chat.completions.create(
    model="gpt-5-mini",
    # temperature=0.7, # unsupported in gpt-5-mini
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ]
)

raw_output = response.choices[0].message.content

# 2.5 Save to JSON
generated_dataset = json.loads(raw_output)
with open("evals/rag_evaluation_dataset_random.json", "w") as f:
    json.dump(generated_dataset, f, indent=2)

# # or read from an existing file
# with open("evals/rag_evaluation_dataset_random.json", "r") as f:
#     # json.load() reads the file object and returns a Python dictionary
#     generated_dataset = json.load(f)

# 3. Upload the dataset to LangSmith  

client = Client(api_key=os.environ["LANGSMITH_API_KEY"])

dataset_name = "rag-evaluation-dataset-random"
try:
    # Try to get the dataset if it already exists to prevent re-creation
    dataset = client.read_dataset(dataset_name=dataset_name)
    print(f"Dataset '{dataset_name}' already exists. Appending new examples.")
except Exception as e:
    # If the dataset does not exist, create it
    print(f"Dataset '{dataset_name}' not found. Creating a new one.")
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Dataset for evaluating RAG pipeline"
    )

# Now, iterate over the data loaded from the JSON file
for item in generated_dataset:
    # Use the retrieved chunk IDs to get the contexts from Qdrant
    records = qdrant_client.retrieve(
        collection_name=config.QDRANT_COLLECTION_NAME,
        ids=item["chunk_ids"],
        with_payload=True
    )
    # Extract the text content from the retrieved records
    contexts = [rec.payload["text"] for rec in records]

    client.create_example(
        dataset_id=dataset.id,
        inputs={"question": item["question"]},
        outputs={
            "ground_truth": item["answer_example"],
            "context_ids": item["chunk_ids"],
            "contexts": contexts
        }
    )

print(f"Successfully uploaded {len(generated_dataset)} examples to LangSmith dataset '{dataset_name}'.")














# dataset_name = "rag-evaluation-dataset-random"
# dataset = client.create_dataset(
#     dataset_name=dataset_name,
#     description="Dataset for evaluating RAG pipeline"
# )

# for item in dataset:
#     records = qdrant_client.retrieve(
#         collection_name=config.QDRANT_COLLECTION_NAME,
#         ids=item["chunk_ids"],
#         with_payload=True
#     )
#     contexts = [rec.payload["text"] for rec in records]

#     client.create_example(
#         dataset_id=dataset.id,
#         inputs={"question": item["question"]},
#         outputs={
#             "ground_truth": item["answer_example"],
#             "context_ids": item["chunk_ids"],
#             "contexts": contexts
#         }
#     )