import os
import sys
import asyncio
from langsmith import Client
from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.api.core.config import config
from src.api.rag.retrieval import rag_pipeline

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithoutReference,
    LLMContextRecall,
    NonLLMContextRecall,
)

os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
os.environ["EVALUATION_MODE"] = "true"
debug_mode = False

# --- Initialize clients ---
ls_client = Client(api_key=config.LANGSMITH_API_KEY)
qdrant_client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)

ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1", openai_api_key=config.OPENAI_API_KEY))
ragas_embeddings = LangchainEmbeddingsWrapper(
    OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY)
)

# --- Define async rag_pipeline wrapper ---
async def rag_pipeline_for_eval(example):
    # question = example.inputs["question"]
    question = example["question"] 
    result = rag_pipeline(question, qdrant_client, session_id=0)

    return {
        "answer": result["answer"],
        "question": question,
        "retrieved_context": result["retrieved_context"],
        "sources": result["sources"],
    }

# --- Define async evaluators ---
async def ragas_faithfulness(run, example):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"],
    )
    scorer = Faithfulness(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)

async def ragas_response_relevancy(run, example):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"],
    )
    scorer = ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
    return await scorer.single_turn_ascore(sample)

async def ragas_context_precision(run, example):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"],
    )
    scorer = LLMContextPrecisionWithoutReference(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)

async def ragas_context_recall_llm_based(run, example):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        reference=example.outputs["ground_truth"],
        retrieved_contexts=run["retrieved_context"],
    )
    scorer = LLMContextRecall(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)

async def ragas_context_recall_non_llm(run, example):
    sample = SingleTurnSample(
        retrieved_contexts=run["retrieved_context"],
        reference_contexts=example.outputs["contexts"],
    )
    scorer = NonLLMContextRecall()
    return await scorer.single_turn_ascore(sample)

# # --- Async main ---
# async def main():
#     # Fetch dataset and examples
#     # dataset = ls_client.read_dataset(dataset_name="rag-evaluation-dataset")
#     # examples = dataset.examples

#     # Read the dataset
#     dataset = ls_client.read_dataset(dataset_name="rag-evaluation-dataset")

#     # Use the `ls_client.list_examples` method to get all examples in that dataset
#     examples = list(ls_client.list_examples(dataset_id=dataset.id))

#     # Run all examples asynchronously
#     async def evaluate_example(example):
#         run = await rag_pipeline_for_eval(example)
#         scores = await asyncio.gather(
#             ragas_faithfulness(run, example),
#             ragas_response_relevancy(run, example),
#             ragas_context_precision(run, example),
#             ragas_context_recall_llm_based(run, example),
#             ragas_context_recall_non_llm(run, example),
#         )
#         return {
#             "example_id": example.id,
#             "run": run,
#             "scores": scores,
#         }

#     all_results = await asyncio.gather(*(evaluate_example(ex) for ex in examples))
#     # print(all_results)

# # Run the async evaluation
# asyncio.run(main())


async def evaluate_and_log(dataset_name: str):
    # 1️⃣ Get the dataset
    dataset = ls_client.read_dataset(dataset_name=dataset_name)
    examples = list(ls_client.list_examples(dataset_id=dataset.id))  # fetch all examples

    results = []

    for example in examples:
        # 2️⃣ Run your RAG pipeline
        result = await rag_pipeline_for_eval({"question": example.inputs["question"]})

        # 3️⃣ Log the run to LangSmith
        ls_client.create_run(
            name=f"eval-{example.id}",
            run_type="llm",
            inputs={"question": example.inputs["question"]},
            outputs={
                "answer": result["answer"],
                "retrieved_context": result["retrieved_context"],
                "sources": result["sources"],
            },
        )

        # 4️⃣ Optionally store locally
        results.append(result)

    return results

async def main():
    results = await evaluate_and_log("rag-evaluation-dataset")
    print("Evaluation finished:", results)

if __name__ == "__main__":
    asyncio.run(main())