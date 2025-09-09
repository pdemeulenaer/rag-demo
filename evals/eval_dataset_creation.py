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
all_points = qdrant_client.scroll(
    collection_name=config.QDRANT_COLLECTION_NAME,
    limit=10000,
    with_payload=False, 
    with_vectors=False 
)[0]
all_point_ids = [point.id for point in all_points]

random.seed(42)  
random_point_ids = random.sample(all_point_ids, 50)

random_chunks = qdrant_client.retrieve(
    collection_name=config.QDRANT_COLLECTION_NAME,
    ids=random_point_ids,
    with_payload=True
)

print(f"Randomly selected {len(random_chunks)} chunks.")
print(random_chunks) 
print()

# 2. Use LLM to generate synthetic eval data based on the chunks

# 2.1 Create a list of dictionaries with sequential IDs and the actual Qdrant IDs
# This is the crucial mapping step
data_for_llm = []
id_mapping = {} # 💡 We'll use this dict to map the LLM's integer IDs to Qdrant's UUIDs
for i, point in enumerate(random_chunks):
    data_for_llm.append({"id": i, "text": point.payload["text"]})
    id_mapping[str(i)] = point.id # Store the mapping from integer to UUID

print("Chunks used to generate eval dataset:")
print(data_for_llm[0])
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

You will receive a list of chunks (with sequential IDs and text).
Your task is to generate 30 evaluation questions.

Guidelines:
- Questions must be grounded in the content of the chunks.
- Provide a diverse set of questions (factual, multi-hop, entity-based, etc).
- At least 5 questions should be unanswerable with the given chunks.
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
{data_for_llm}
"""

# 2.4 Generate synthetic eval reference data
response = openai.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ]
)
raw_output = response.choices[0].message.content

# 2.5 Transform and save to JSON
# 💡 Correct approach: Map the IDs before saving the JSON file

generated_dataset = json.loads(raw_output)

# Create a final dataset with UUIDs
final_dataset_with_uuids = []
for item in generated_dataset:
    # Map the integer IDs from the LLM's output to the original UUIDs
    try:
        qdrant_ids = [id_mapping[str(idx)] for idx in item["chunk_ids"]]
    except KeyError as e:
        print(f"Error: Missing ID mapping for integer {e}. This likely means the LLM hallucinated an ID.")
        continue # Skip this item and continue with the next one

    # Create a new item with the correct UUIDs
    new_item = {
        "question": item["question"],
        "chunk_ids": qdrant_ids,
        "answer_example": item["answer_example"],
        "reasoning": item["reasoning"]
    }
    final_dataset_with_uuids.append(new_item)

# Save the transformed dataset to JSON
with open("evals/rag_evaluation_dataset_random.json", "w") as f:
    json.dump(final_dataset_with_uuids, f, indent=2)

# The rest of your code to upload to LangSmith is now simplified
# because the JSON file is already correct. You would simply load it
# and upload.

# 3. Upload the dataset to LangSmith
client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
dataset_name = "rag-evaluation-dataset-random"

try:
    dataset = client.read_dataset(dataset_name=dataset_name)
    print(f"Dataset '{dataset_name}' already exists. Appending new examples.")
except Exception as e:
    print(f"Dataset '{dataset_name}' not found. Creating a new one.")
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Dataset for evaluating RAG pipeline"
    )

# Load the already-corrected JSON file
with open("evals/rag_evaluation_dataset_random.json", "r") as f:
    upload_dataset = json.load(f)

for item in upload_dataset:
    # Use the retrieved chunk IDs (now UUIDs) to get the contexts
    records = qdrant_client.retrieve(
        collection_name=config.QDRANT_COLLECTION_NAME,
        ids=item["chunk_ids"],
        with_payload=True
    )
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

print(f"Successfully uploaded {len(upload_dataset)} examples to LangSmith dataset '{dataset_name}'.")
