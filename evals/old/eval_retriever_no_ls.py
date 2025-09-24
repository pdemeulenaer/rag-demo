import os
import sys
import json
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.api.core.config import config
from src.api.rag.retrieval import rag_pipeline

from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_groq import ChatGroq

# from ragas.llms import OpenAILLM
# from ragas.embeddings import OpenAIEmbeddings
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


os.environ["EVALUATION_MODE"] = "true"
# os.environ["LANGCHAIN_TRACING_V2"] = "false"  # 💡 Add this line to disable LangSmith tracing
os.environ["GROQ_API_KEY"] = config.GROQ_API_KEY
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
# os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["QDRANT_API_KEY"] = config.QDRANT_API_KEY  # For Qdrant Cloud only
os.environ["QDRANT_URL"] = config.QDRANT_URL
debug_mode = False

# -------------------------------
# Init Qdrant + Models
# -------------------------------
qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY
)



# ragas_llm = OpenAILLM(model="gpt-4o-mini", api_key=config.OPENAI_API_KEY)
# ragas_embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=config.OPENAI_API_KEY)
ragas_llm = LangchainLLMWrapper(ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=config.GROQ_API_KEY))
# ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1-mini", openai_api_key=config.OPENAI_API_KEY))
ragas_embeddings = LangchainEmbeddingsWrapper(
    OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY)
)


# -------------------------------
# Evaluators (local, no LangSmith)
# -------------------------------
async def ragas_faithfulness(run):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = Faithfulness(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)


async def ragas_response_relevancy(run):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
    return await scorer.single_turn_ascore(sample)


async def ragas_context_precision(run):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = LLMContextPrecisionWithoutReference(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)


async def ragas_context_recall_llm_based(run, reference_answer):
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        reference=reference_answer,
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = LLMContextRecall(llm=ragas_llm)
    return await scorer.single_turn_ascore(sample)


async def ragas_context_recall_non_llm(run, reference_contexts):
    sample = SingleTurnSample(
        retrieved_contexts=run["retrieved_context"],
        reference_contexts=reference_contexts
    )
    scorer = NonLLMContextRecall()
    return await scorer.single_turn_ascore(sample)


# -------------------------------
# Runner
# -------------------------------
import json
import asyncio

async def evaluate_local(dataset_path="notebooks/rag_evaluation_dataset.json"):
    # Load dataset
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    results = []

    for i, example in enumerate(dataset, 1):
        question = example["question"]
        print(f"\n🔍 [{i}/{len(dataset)}] Evaluating: {question[:80]}...")

        reference_answer = example.get("answer_example")
        reference_contexts = example.get("chunk_ids", [])

        # Run your pipeline
        rag_result = rag_pipeline(question, qdrant_client, session_id=0)

        run = {
            "question": question,
            "answer": rag_result["answer"],
            "retrieved_context": rag_result["retrieved_context"],
            "sources": rag_result["sources"],
        }

        # Compute metrics
        scores = {}
        try:
            scores["faithfulness"] = await ragas_faithfulness(run)
            scores["response_relevancy"] = await ragas_response_relevancy(run)
            scores["context_precision"] = await ragas_context_precision(run)

            if reference_answer:
                scores["context_recall_llm"] = await ragas_context_recall_llm_based(run, reference_answer)

            if reference_contexts:
                scores["context_recall_non_llm"] = await ragas_context_recall_non_llm(run, reference_contexts)

        except Exception as e:
            print(f"⚠️ Error while scoring example {i}: {e}")

        # Print live results
        print("✅ Scores:", scores)

        results.append({
            "question": question,
            "answer": run["answer"],
            "scores": scores
        })

    return results

if __name__ == "__main__":
    results = asyncio.run(evaluate_local())
    print("\n🎯 Finished all evaluations!")
    print(f"Total examples evaluated: {len(results)}")


# if __name__ == "__main__":
#     dataset_path = os.path.join("notebooks", "rag_evaluation_dataset.json")
#     final_results = asyncio.run(evaluate_local(dataset_path))

#     import pprint
#     pprint.pprint(final_results)
