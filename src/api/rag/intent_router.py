# src/api/rag/intent_router.py
from pydantic import BaseModel
from typing import Literal, Optional
import instructor
import openai
import logging
from src.api.core.config import config

logger = logging.getLogger(__name__)


# ---------- Intent schema ----------
class MetadataIntent(BaseModel):
    intent: Literal[
        "list_titles", "list_authors", "titles_by_author",
        "authors_by_year", "author_of_title",
        "summarize_paper",
        "mixed",            # fallback → run semantic RAG
    ]
    author: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None

# ---------- LLM router ----------
router_prompt = """
You classify a user question about a scientific-paper database.

Return JSON:
{
 "intent": "...",
 "author": string|null,
 "year": string|null,
 "title": string|null
}
Valid intents:
- list_titles          (list all titles)
- list_authors         (list all authors)
- titles_by_author     (titles filtered by author/year)
- authors_by_year      (authors filtered by year)
- author_of_title      (who wrote a specific title)
- summarize_paper      (give a summary of a specific paper)
- mixed                (anything else → semantic RAG)
Question: "{q}"
"""

router_llm = instructor.from_openai(
    openai.OpenAI(api_key=config.OPENAI_API_KEY)   # or Groq/OpenAI as you prefer
)

def classify_question(question: str) -> MetadataIntent:
    raw = router_llm.chat.completions.create(
        model="gpt-4o-mini",
        response_model=MetadataIntent,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an intent classifier. "
                    "Return JSON strictly matching the MetadataIntent schema. "
                    "Choose one of: list_titles, list_authors, titles_by_author, "
                    "authors_by_year, author_of_title, summarize_paper, mixed. "
                    "If it is not about metadata, choose mixed."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    logger.info("Raw classifier output: %s", raw)  # <-- add this
    return MetadataIntent.model_validate(raw)


# def classify_question(question: str) -> MetadataIntent:
#     return router_llm.chat.completions.create(
#         model="gpt-4o-mini",        # cheap/fast model
#         response_model=MetadataIntent,
#         temperature=0,
#         messages=[{"role": "user", "content": router_prompt.format(q=question)}]
#     )
