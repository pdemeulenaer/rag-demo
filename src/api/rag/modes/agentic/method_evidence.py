"""Conservative routing hints for explicitly named reported-method roles.

Not a method inventory or entailment engine. Typed reviewers still compare the
claimed role to independently quoted, citation-scoped source operations.
"""
import re


def reported_method_names(text: str) -> list[str]:
    names = []
    for clause in re.split(r"[.;!?]", text):
        # A proposal alone is not a reported operation. Mixed claims must keep
        # reported premises in a separate clause and audit them normally.
        for match in re.finditer(r"\b([\w-]{2,})\s+(algorithm|method)\b", clause, re.I):
            name = match.group(1)
            # Generic descriptions such as "measured method" are not names.
            # Lowercase named algorithms are common; bare "X method" cues use
            # a proper-name spelling. This is deliberately not an exhaustive classifier.
            if match.group(2).casefold() == "method" and not name[0].isupper():
                continue
            if re.search(r"\b(?:we propose|could use|could be used|proposed use|might use)\b",
                         clause[:match.start()], re.I) and not re.search(
                             r"\b(?:which|that|whose)\b", clause[match.end():], re.I):
                continue
            if name.casefold() not in {"a", "an", "the", "this", "that", "our", "their", "unnamed"}:
                names.append(name)
    return list(dict.fromkeys(names))
