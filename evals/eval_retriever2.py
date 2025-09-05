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
from langchain_groq import ChatGroq
from langchain_openai import OpenAIEmbeddings

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from ragas.dataset_schema import SingleTurnSample 
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithoutReference, LLMContextRecall, NonLLMContextRecall


os.environ["EVALUATION_MODE"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # 💡 Add this line to disable LangSmith tracing
os.environ["GROQ_API_KEY"] = config.GROQ_API_KEY
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["QDRANT_API_KEY"] = config.QDRANT_API_KEY  # For Qdrant Cloud only
os.environ["QDRANT_URL"] = config.QDRANT_URL
debug_mode = False

# Initialize LangSmith & Qdrant clients

ls_client = Client(api_key=config.LANGSMITH_API_KEY)

# qdrant_client = QdrantClient(
#     url=f"http://localhost:6333"
# )
qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY  # For Qdrant Cloud only
)

# Initialize the Groq model for Ragas evaluation
ragas_llm = LangchainLLMWrapper(ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=config.GROQ_API_KEY))
# ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1-mini", openai_api_key=config.OPENAI_API_KEY))
ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY))



async def ragas_faithfulness(run, example):
    # https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/

    # # Fail-fast checks
    if debug_mode:
        print("🛠️ Debug mode is ON")
        print("📝 example.inputs =", example.inputs)
        # print("📝 example.outputs =", example.outputs)
        print("🔍 run.outputs =", run.outputs)

    if not run.outputs:
        raise KeyError("run.outputs is missing in ragas_faithfulness")

    required = ["question", "answer", "retrieved_context"]
    missing = [k for k in required if k not in run.outputs]
    if missing:
        raise KeyError(f"Missing keys in run.outputs: {missing}. Available keys: {list(run.outputs.keys())}")


    sample = SingleTurnSample(
            user_input=example.inputs.get("question"), #run.outputs["question"],
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


# def rag_pipeline_for_eval(inputs):
#     result = rag_pipeline(inputs["question"], qdrant_client, session_id=0)
#     return {
#         "answer": result["answer"],
#         "question": inputs["question"],
#         "retrieved_context": result["retrieved_context"],
#         "sources": result["sources"],
#     }

def rag_pipeline_for_eval(inputs): 
    result = rag_pipeline(inputs["question"], qdrant_client, session_id=0)
    return {
        "answer": result["answer"],
        "question": inputs["question"],
        "retrieved_context": result["retrieved_context"],
        "sources": result["sources"], 
        }

# results = ls_client.evaluate(
#     rag_pipeline_for_eval,
#     data="rag-evaluation-dataset",
#     evaluators=[
#         ragas_faithfulness,
#         ragas_response_relevancy,
#         ragas_context_precision,
#         ragas_context_recall_llm_based,
#         ragas_context_recall_non_llm,
#     ],
#     experiment_prefix="rag-evaluation-dataset"
# )

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
