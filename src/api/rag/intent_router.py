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
# router_prompt = """
# You classify a user question about a scientific-paper database.

# Return JSON:
# {
#  "intent": "...",
#  "author": string|null,
#  "year": string|null,
#  "title": string|null
# }
# Valid intents:
# - list_titles          (list all titles)
# - list_authors         (list all authors)
# - titles_by_author     (titles filtered by author/year)
# - authors_by_year      (authors filtered by year)
# - author_of_title      (who wrote a specific title)
# - summarize_paper      (give a summary of a specific paper)
# - mixed                (anything else → semantic RAG)
# Question: "{q}"
# """

router_prompt = """
You classify a user question about a scientific-paper database.

Return ONLY JSON:
{
 "intent": "...",
 "author": string|null,
 "year": string|null,
 "title": string|null
}

Valid intents:
- list_titles          (list all titles, ONLY when NO author/year constraint is present)
- list_authors         (list all authors)
- titles_by_author     (list titles filtered by author and/or year)
- authors_by_year      (authors filtered by year only)
- author_of_title      (who wrote a specific title)
- summarize_paper      (summary of a specific paper)
- mixed                (anything else → semantic RAG)

Rules:
* If the question mentions an author name (e.g. "Mark Gieles") and asks for titles,
  ALWAYS use intent "titles_by_author" and set the "author" field.
* If it asks for titles AND a year, use intent "titles_by_author" with both author and year.
* Only use "list_titles" when the user truly wants every title in the database,
  with no author or year restriction.

Question: "{q}"
"""

router_llm = instructor.from_openai(
    openai.OpenAI(api_key=config.OPENAI_API_KEY)   # or Groq/OpenAI as you prefer
)

# INTENT CLASSIFIER
def classify_question(question: str) -> MetadataIntent:
    raw = router_llm.chat.completions.create(
        model="gpt-4o-mini",
        response_model=MetadataIntent,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an intent classifier for a scientific-paper database.\n"
                    "Return JSON strictly matching the MetadataIntent schema.\n"
                    "Valid intents: list_titles, list_authors, titles_by_author,\n"
                    "authors_by_year, author_of_title, summarize_paper, mixed.\n"
                    "Rules:\n"
                    "- If a question asks for titles and mentions an author (and optional year), "
                    "use titles_by_author and fill the author/year fields.\n"
                    "- Use list_titles ONLY when the user wants ALL titles with no author/year filter.\n"
                    "- If it's not about metadata, use mixed."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    logger.info("Raw classifier output: %s", raw)

    intent = MetadataIntent.model_validate(raw)

    # 🛡️ Guardrail: correct obvious contradictions
    if intent.intent == "list_titles" and (intent.author or intent.year):
        logger.info("Guardrail: upgrading intent to titles_by_author")
        intent.intent = "titles_by_author"        

    return intent


# def classify_question(question: str) -> MetadataIntent:
#     return router_llm.chat.completions.create(
#         model="gpt-4o-mini",        # cheap/fast model
#         response_model=MetadataIntent,
#         temperature=0,
#         messages=[{"role": "user", "content": router_prompt.format(q=question)}]
#     )
