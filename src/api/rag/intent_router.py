# src/api/rag/intent_router.py
from pydantic import BaseModel
from typing import Literal, Optional
import instructor
import openai
import logging
from src.api.core.config import config
from src.api.rag.utils.utils import prompt_template_config

logger = logging.getLogger(__name__)


# ---------- Intent schema ----------
class MetadataIntent(BaseModel):
    intent: Literal[
        "list_titles", 
        "list_authors", 
        "titles_by_author",
        "authors_by_year", 
        "author_of_title",
        "summarize_paper",
        "chat_followup", 
        "rag",            # fallback → run semantic RAG
    ]
    author: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None

# ---------- LLM router ----------
router_llm = instructor.from_openai(
    openai.OpenAI(api_key=config.OPENAI_API_KEY)   # or Groq/OpenAI as you prefer
)

# ---------- INTENT CLASSIFIER ----------
def classify_question(question: str, chat_history: str = "") -> MetadataIntent:

    prompt_template = prompt_template_config(config.RAG_PROMPT_TEMPLATE_PATH, "intent_classification")

    messages = [
        {"role": "system", "content": prompt_template["system"].render()},
        {
            "role": "user",
            "content": prompt_template["user"].render(
                question=question,
                chat_history=chat_history or "",
            ),
        },
    ]

    raw = router_llm.chat.completions.create(
        model="gpt-4o-mini",
        response_model=MetadataIntent,
        temperature=0,
        messages=messages,
    )
    logger.info("Raw classifier output: %s", raw)

    intent = MetadataIntent.model_validate(raw)

    # 🛡️ Guardrail: correct obvious contradictions
    if intent.intent == "list_titles" and (intent.author or intent.year):
        logger.info("Guardrail: upgrading intent to titles_by_author")
        intent.intent = "titles_by_author"        

    return intent
