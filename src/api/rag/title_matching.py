"""Configuration-free literal title normalization shared by catalogue and KG tools."""
import re
import unicodedata


QUOTED_TEXT = re.compile(r'["“]([^"”]{8,300})["”]')


def normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", normalized).split())
