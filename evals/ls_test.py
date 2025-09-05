import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from langsmith import Client

from src.api.core.config import config


os.environ["LANGCHAIN_TRACING_V2"] = "false"  # 💡 Add this line to disable LangSmith tracing
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY


ls_client = Client(api_key=config.LANGSMITH_API_KEY)

try:
    # Check if the dataset can be fetched
    dataset = ls_client.read_dataset(dataset_name="rag-evaluation-dataset")
    print("Successfully connected to LangSmith and fetched dataset.")
except Exception as e:
    print(f"Failed to connect to LangSmith or fetch dataset: {e}")