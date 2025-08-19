import os
import json
from typing import List, Optional, Any
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from deepeval import evaluate
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from utils import get_reranked_qdrant_retriever, get_conversation_chain

# Load .env
load_dotenv()

# Define expected return format for DeepEval
class JudgeOutput(BaseModel):
    output: str
    statements: List[str]
    verdicts: Optional[List[Any]] = None

# Custom LLM for DeepEval
class GroqJudgeLLM(DeepEvalBaseLLM):
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, **kwargs) -> JudgeOutput:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2048
        )
        content = response.choices[0].message.content.strip()

        statements = []
        verdicts = []  # Initialize verdicts as an empty list

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                if "statements" in parsed:
                    statements = parsed["statements"]
                if "verdicts" in parsed and isinstance(parsed["verdicts"], list):
                    verdicts = parsed["verdicts"]
            elif isinstance(parsed, list):
                statements = parsed
        except json.JSONDecodeError:
            # Fallback to newline split for statements if JSON parsing fails
            statements = [line.strip() for line in content.split("\n") if line.strip()]
        except Exception as e:
            print(f"Warning: Failed to parse JSON or extract verdicts/statements: {e}")
            statements = [line.strip() for line in content.split("\n") if line.strip()]


        # Ensure verdicts is always a list, even if empty
        return JudgeOutput(output=content, statements=statements, verdicts=verdicts)

    async def a_generate(self, prompt: str, **kwargs) -> JudgeOutput:
        return self.generate(prompt, **kwargs)

    def get_model_name(self):
        return self.model_name

# --- Main Script ---

# Load dataset
with open("qa_dataset.json", "r", encoding="utf-8") as f:
    qa_dataset = json.load(f)

# Setup retriever and RAG chain
retriever = get_reranked_qdrant_retriever()
conversation = get_conversation_chain(retriever)

# Run RAG predictions
results = []
for qa in qa_dataset:
    response = conversation.invoke({"question": qa["question"]})
    results.append({
        "question": qa["question"],
        "ground_truth": qa["ground_truth"],
        "generated_answer": response["answer"]
    })

print("Generated Answers:")
for r in results:
    print(f"Q: {r['question']}")
    print(f"A: {r['generated_answer']}\n")

# Define test cases
test_cases = [
    LLMTestCase(
        input=r["question"],
        actual_output=r["generated_answer"],
        expected_output=r["ground_truth"]
    )
    for r in results
]

# Use Groq-backed judge LLM
judge_llm = GroqJudgeLLM()
metric = AnswerRelevancyMetric(model=judge_llm)

# Run evaluation
evaluation_results = evaluate(test_cases, [metric])

# Print detailed results
print("Evaluation Results:")
for result in evaluation_results:
    print(f"Question: {result.input}")
    print(f"Score: {result.metric_scores[0].score:.3f}")
    print(f"Success: {result.success}")
    print(f"Statements: {result.metric_scores[0].statements}\n")

# Print average score
average = sum(r.metric_scores[0].score for r in evaluation_results) / len(evaluation_results)
print(f"Average Score: {average:.3f}")