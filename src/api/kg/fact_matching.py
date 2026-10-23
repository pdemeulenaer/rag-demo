"""Conservative lexical assertion targeting inside explicitly resolved named papers.

This is a retrieval signal, not entailment, numeric validation or an answer judge.
Only validated/approved records enter this helper; no reference answers are inputs.
"""
import re
import unicodedata

from .entities import mentioned
from .scientific_schema import Entity, Observation
from src.api.rag.title_matching import QUOTED_TEXT, normalized_title


MIN_FACT_TERMS = 2
FACT_MATCHING_POLICY = "named-assertion-literal-overlap-v1"
# English function/reporting words, not a scientific-topic or object blacklist.
_STOP = frozenset("""a an the and or of to in on at by for from with without as is are was were
be been being it its their these those this that which what how who do does did say says
said about according between within into than then also both each such rather versus vs
we they he she our your you give state describe discuss identify compare contrast explain
report reported reporting show observed measured measurement study paper author result
observation population star cluster object system analysis source supplied indexed
different difference finding method model main original including respectively specifically
test set training class value number use using used
""".split())
_WORDS = re.compile(r"[^\W\d_]+", re.UNICODE)


def _terms(text):
    result = set()
    for word in _WORDS.findall(unicodedata.normalize("NFKC", str(text)).casefold()):
        if word in _STOP:
            continue
        # Limited English plural normalization, never synonyms/semantic rewriting.
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = word[:-1]
        if len(word) >= 2 and word not in _STOP:
            result.add(word)
    return result


def requested_fact_matches(parsed, query, required_papers):
    """Return direct assertion/own-quote witnesses; never license neighbouring records.

    Two distinct requested content terms must occur in BOTH an assertion's
    statement/quantity and one of its own exact source quotes. Titles and matched
    entity names cannot supply those terms. All source identities stay unchanged.
    """
    requested = {(p.collection, p.build_id) for p in required_papers}
    if not requested:
        return {}
    titles = {normalized_title(p.title) for p in required_papers if getattr(p, "title", None)}
    content = QUOTED_TEXT.sub(lambda match: " " if normalized_title(match[1]) in titles else match[0], query)
    names = {name for _, record in parsed.values() if isinstance(record, Entity) and record.kind != "physical_process"
             for name in [record.name, *record.aliases] if mentioned(name, content)}
    wanted = _terms(content) - set().union(*(_terms(name) for name in names))
    if len(wanted) < MIN_FACT_TERMS:
        return {}
    matches = {}
    for key, (props, record) in parsed.items():
        if (not isinstance(record, Observation) or record.quarantined
                or (props["collection"], props["build_id"]) not in requested):
            continue
        assertion_terms = wanted & _terms(f"{record.statement} {record.quantity or ''}")
        if len(assertion_terms) < MIN_FACT_TERMS:
            continue
        source_matches = []
        for evidence in record.evidence:
            shared = sorted(assertion_terms & _terms(evidence.quote))
            if len(shared) >= MIN_FACT_TERMS:
                source_matches.append(dict(collection=evidence.collection, id=str(evidence.point_id),
                                           matched_terms=shared))
        if source_matches:
            matches[key] = dict(kind=record.kind, source_matches=source_matches)
    return matches
