"""Offline heuristics for draft question quality, not scientific entailment checks."""
import re
import unicodedata


POLICY = "fact-first-v1"
EXCLUDED_SECTION = re.compile(
    r"\b(references|bibliography|acknowledg(?:e)?ments?|funding|data availability|"
    r"author contributions?|conflicts? of interest)\b", re.I)
PREFERRED_SECTION = re.compile(
    r"\b(methods?|methodology|results?|conclusions?|discussion|analysis)\b", re.I)
REFERENCE_LINE = re.compile(r"\b(?:19|20)\d{2}[a-z]?,?\s+(?:[A-Z]|arXiv)|\bdoi\s*:|doi\.org/", re.I)
MISSING_ANSWER = re.compile(
    r"\babstain\b|\b(?:cannot|can't|could not)\s+(?:be\s+)?"
    r"(?:determined?|answered?|inferred?|estimated?|calculated?|established?|quantified?)\b|"
    r"\b(?:not|never)\s+(?:explicitly\s+)?(?:specified|provided|reported|given|available|stated)\b|"
    r"\b(?:do|does)\s+not\s+(?:give|provide|report|specify|include|state)\b|"
    r"\b(?:insufficient|missing|absent|additional|required)\s+(?:numeric\w*\s+)?"
    r"(?:information|evidence|data|ranges?|uncertainties|precision)\b|"
    r"\b(?:information|evidence|data|ranges?|uncertainties|precision)\s+"
    r"(?:\w+\s+){0,3}(?:missing|absent|needed|required)\b", re.I)


def words(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def evidence_priority(text, section="", kind="text"):
    """None excludes a chunk; 0 prefers substantive sections; 1 is other text."""
    headings = " ".join(re.findall(r"^\s*#{1,6}\s+(.+)$", text, re.M))
    if EXCLUDED_SECTION.search(section + " " + headings):
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Legacy payloads may lack heading metadata; detect citation-list dominated text.
    if len(lines) >= 2 and sum(bool(REFERENCE_LINE.search(line)) for line in lines) / len(lines) >= 0.6:
        return None
    if re.search(r"\b(?:acknowledge(?:s)? support|funding .* provided by)\b", text, re.I):
        return None
    visible = re.sub(r"\*\*[^\n]*?(?:intentionally omitted|Start of picture text|End of picture text)[^\n]*?\*\*", "", text)
    visible = re.sub(r"<br\s*/?>|[#*_~|]", " ", visible)
    if len(re.findall(r"[A-Za-z]{2,}", visible)) < 8:
        return None
    # Keep the original text, including Markdown, unchanged in the snapshot.
    if kind == "table_unstructured":
        return 1
    return 0 if PREFERRED_SECTION.search(section + " " + headings) else 1


def candidate_issue(candidate, kind, supplied, *, profile=None):
    if kind != "unanswerable_candidate" and MISSING_ANSWER.search(candidate.reference_answer):
        return "answerable_candidate_missing_information"
    named = words(candidate.question)
    papers = {row["paper_id"]: row["title"] for row in supplied.values()}
    if profile == "metadata_discovery":
        answer = words(candidate.reference_answer)
        if any(f" {words(title)} " in f" {named} " for title in papers.values()):
            return "metadata_question_reveals_paper_title"
        if any(not words(title) or f" {words(title)} " not in f" {answer} " for title in papers.values()):
            return "metadata_answer_missing_paper_title"
    elif any(not words(title) or f" {words(title)} " not in f" {named} " for title in papers.values()):
        return "question_missing_paper_title"
    if re.search(r"\b(?:provided|supplied) excerpts?\b|\bcontext (?:above|below)\b|\bevidence_ids?\b", candidate.question, re.I):
        return "question_not_standalone"
    return None
