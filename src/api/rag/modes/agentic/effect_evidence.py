"""Small literal binding checks around native parameter-effect assessments.

These validate identity/qualifiers, not scientific entailment. They do not guess
numbers, inject expected answers, or restrict evidence to the tool that found it.
"""
import re
import unicodedata


def words(text):
    return re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold())


def literal_span(text, quote):
    def normalized(value):
        value = unicodedata.normalize("NFKC", value).casefold().replace("−", "-")
        value = re.sub(r"[_*`]", "", value)
        value = re.sub(r"(?<=[a-z])[-‐‑](?=[a-z])", " ", value)
        return " ".join(value.split())
    source, target = normalized(text), normalized(quote)
    # Keep signs, numeric values, punctuation and ellipses. No stitched passages,
    # invented OCR substitutions or word-only matching that discards a minus sign.
    return bool(target) and target in source


def names_parameter(quote, parameter):
    # Word order/punctuation can differ (e.g. "disk outer radius" / "outer disk
    # radius"). Keep every meaningful qualifier; no fuzzy alias inference.
    terms = set(words(parameter)) - {"a", "an", "the", "of"}
    return bool(terms) and terms.issubset(set(words(quote)))
