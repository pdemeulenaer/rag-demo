"""Small, deterministic checks for parts of the original user question."""
from __future__ import annotations

import re


_PART_LABEL = re.compile(r"\(([a-z])\)\s*", re.I)
_COMPARISON_WORD = re.compile(
    r"\b(?:below|above|within|lower\s+than|higher\s+than|less\s+than|"
    r"greater\s+than|outside|inside|overlaps?|exceeds?)\b|"
    r"(?<=\d)\s*[<>]\s*(?=\d)",
    re.I,
)


def original_question_parts(question: str) -> list[tuple[str, str]]:
    """Keep the user's enumerated requests independent of the agent's plan."""
    matches = list(_PART_LABEL.finditer(question))
    if len(matches) < 2 or len({match.group(1).lower() for match in matches}) != len(matches):
        return [("q_original", question[:1800])]
    return [
        (
            f"q_{match.group(1).lower()}",
            f"Original question part ({match.group(1).lower()}): "
            + question[match.end():matches[index + 1].start() if index + 1 < len(matches)
                       else len(question)].strip(" ,;?.\n")[:1700],
        )
        for index, match in enumerate(matches)
    ]


def requests_explicit_comparison(text: str) -> bool:
    """Detect an explicit choice among directional relationships."""
    return sum(bool(re.search(rf"\b{word}\b", text, re.I))
               for word in ("within", "below", "above")) >= 2


def has_explicit_comparison(text: str) -> bool:
    return bool(_COMPARISON_WORD.search(text))
