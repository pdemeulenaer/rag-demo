import os
import sys

# Add the project root to sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
# os.chdir("..") # Change working directory to project root

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.api.core.config import config
from src.api.rag.retrieval import rag_pipeline

import asyncio
from langsmith import Client
from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from ragas.dataset_schema import SingleTurnSample 
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithoutReference, LLMContextRecall, NonLLMContextRecall


os.environ["EVALUATION_MODE"] = "true"

# Initialize LangSmith & Qdrant clients

ls_client = Client(api_key=config.LANGSMITH_API_KEY)

# qdrant_client = QdrantClient(
#     url=f"http://localhost:6333"
# )
qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only
)


ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1", openai_api_key=config.OPENAI_API_KEY))
ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY))

async def ragas_faithfulness(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
    sample = SingleTurnSample(
            user_input=run.outputs["question"],
            response=run.outputs["answer"],
            retrieved_contexts=run.outputs["retrieved_context"]
        )
    scorer = Faithfulness(llm=ragas_llm)

    return await scorer.single_turn_ascore(sample)


async def ragas_response_relevancy(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/
    sample = SingleTurnSample(
            user_input=run.outputs["question"],
            response=run.outputs["answer"],
            retrieved_contexts=run.outputs["retrieved_context"]
        )
    scorer = ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)

    return await scorer.single_turn_ascore(sample)


async def ragas_context_precision(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/
    sample = SingleTurnSample(
            user_input=run.outputs["question"],
            response=run.outputs["answer"],
            retrieved_contexts=run.outputs["retrieved_context"]
        )
    scorer = LLMContextPrecisionWithoutReference(llm=ragas_llm)

    return await scorer.single_turn_ascore(sample)


async def ragas_context_recall_llm_based(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/
    sample = SingleTurnSample(
            user_input=run.outputs["question"],
            response=run.outputs["answer"],
            reference=example.outputs["ground_truth"],
            retrieved_contexts=run.outputs["retrieved_context"]
        )
    scorer = LLMContextRecall(llm=ragas_llm)

    return await scorer.single_turn_ascore(sample)


async def ragas_context_recall_non_llm(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/
    sample = SingleTurnSample(
            retrieved_contexts=run.outputs["retrieved_context"],
            reference_contexts=example.outputs["contexts"]
        )
    scorer = NonLLMContextRecall()

    return await scorer.single_turn_ascore(sample)


results = ls_client.evaluate(
    lambda x: rag_pipeline(x["question"], qdrant_client, session_id=0),
    data="rag-evaluation-dataset",
    evaluators=[
        ragas_faithfulness,
        ragas_response_relevancy,
        ragas_context_precision,
        ragas_context_recall_llm_based,
        ragas_context_recall_non_llm
    ],
    experiment_prefix="rag-evaluation-dataset"
)
