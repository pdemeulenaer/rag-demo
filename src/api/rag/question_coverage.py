"""Small, deterministic checks for parts of the original user question."""
from __future__ import annotations

import re


_PART_LABEL = re.compile(r"\(([a-z]|\d{1,2})\)\s*", re.I)
_COMPARISON_WORD = re.compile(
    r"\b(?:below|above|within|lower\s+than|higher\s+than|less\s+than|"
    r"greater\s+than|outside|inside|overlaps?|exceeds?)\b|"
    r"(?<=\d)\s*[<>]\s*(?=\d)",
    re.I,
)
_PARAMETER_EFFECT_REQUEST = re.compile(
    r"\b(?:sensitivit(?:y|ies)|dependence|dependency)\b[^.!?;]{0,80}\b(?:to|on|with)\b|"
    r"\b(?:effect|impact)\s+of\b[^.!?;]{0,100}\bon\b|"
    r"\bhow\b[^.!?;]{0,80}\b(?:changes?|varies|responds?)\b[^.!?;]{0,40}\b(?:with|when|as)\b",
    re.I,
)


def requests_parameter_effect(text: str) -> bool:
    """Select reported parameter-dependence checks, not instrument sensitivity limits.

    This is a schema-routing hint, not a complexity classifier or scientific proof.
    Pure requests to design a prospective test do not demand an already reported effect.
    """
    if re.search(r"\b(?:how\s+(?:could|would)|propose|design)\b", text, re.I) and not re.search(
            r"\b(?:report(?:ed)?|observed|measured|findings)\b", text, re.I):
        return False
    return bool(_PARAMETER_EFFECT_REQUEST.search(text))


def original_question_parts(question: str) -> list[tuple[str, str]]:
    """Keep the user's enumerated requests independent of the agent's plan."""
    matches = list(_PART_LABEL.finditer(question))
    labels = [match.group(1).lower() for match in matches]
    bodies = [question[match.end():matches[index + 1].start() if index + 1 < len(matches)
                       else len(question)].strip(" ,;?.\n")
              for index, match in enumerate(matches)]
    if (not 2 <= len(matches) <= 20 or len(set(labels)) != len(matches)
            or any(not body or body.lower() in {"and", "or", "versus", "vs"} for body in bodies)
            or (any(label.isdigit() for label in labels)
                and labels != [str(i) for i in range(1, len(labels) + 1)])):
        return [("q_original", question[:1800])]
    return [
        (
            f"q_{match.group(1).lower()}",
            f"Original question part ({match.group(1).lower()}): "
            + bodies[index][:1700],
        )
        for index, match in enumerate(matches)
    ]


def requests_explicit_comparison(text: str) -> bool:
    """Detect an explicit choice among directional relationships."""
    return sum(bool(re.search(rf"\b{word}\b", text, re.I))
               for word in ("within", "below", "above")) >= 2


def has_explicit_comparison(text: str) -> bool:
    return bool(_COMPARISON_WORD.search(text))
