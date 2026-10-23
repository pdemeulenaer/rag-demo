"""Conservative read-time object identity; no graph writes or fuzzy name merging.

Only M/NGC/IC catalogue spelling is normalized. Cross-catalogue bridges require
approved astronomical-object names/aliases supported by their source quotations.
Conflicting components are not resolved. Scientific assertions remain separate.
"""
from collections import defaultdict
import re
import unicodedata

from .scientific_schema import Entity


CATALOGUE = re.compile(r"(?<!\w)(ngc|ic|m)\s*([0-9]+[a-z]?)(?!\w)", re.IGNORECASE)
# Conservative promotion anchors, not a semantic relevance classifier. Population,
# process and property matches remain useful traversal seeds but cannot alone evict
# Hybrid evidence. No object-name blacklist or query-specific exceptions.
PROMOTION_ENTITY_KINDS = {"astronomical_object", "spatial_region", "instrument", "method"}


def promotion_anchors(parsed, query):
    return {key: dict(kind=record.kind, names=sorted({name for name in
                [record.name, *record.aliases] if mentioned(name, query)}))
            for key, (_, record) in parsed.items()
            if isinstance(record, Entity) and record.kind in PROMOTION_ENTITY_KINDS
            and any(mentioned(name, query) for name in [record.name, *record.aliases])}


def normalized(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    value = CATALOGUE.sub(lambda m: m[1] + m[2], value)
    return " ".join(re.findall(r"\w+", value))


def catalogue_ids(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return {match[1]+match[2] for match in CATALOGUE.finditer(value)}


def mentioned(name, query):
    name = normalized(name)
    return len(name) >= 2 and f" {name} " in f" {normalized(query)} "


def resolve(parsed, seeds):
    """Linear-size union/find index; never materialize an all-pairs identity clique."""
    by_id, keys = defaultdict(list), {}
    parent = {}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for key, (_, record) in parsed.items():
        if not isinstance(record, Entity) or record.kind != "astronomical_object":
            continue
        supported = set().union(*(catalogue_ids(e.quote) for e in record.evidence))
        identifiers = set()
        for name in [record.name, *record.aliases]:
            candidate = normalized(name)
            # Names must be WHOLE catalogue IDs, not 'M22 stars sample' etc.
            if CATALOGUE.fullmatch(candidate) and candidate in supported:
                identifiers.add(candidate)
        if not identifiers:
            continue
        keys[key] = identifiers
        parent[key] = key
        for identifier in sorted(identifiers):
            if by_id[identifier]:
                a, b = root(key), root(by_id[identifier][0])
                parent[a] = b
            by_id[identifier].append(key)
    groups = defaultdict(list)
    for key in keys:
        groups[root(key)].append(key)
    expanded, resolved_ids, used, conflicts = set(seeds), set(), [], []
    for members in groups.values():
        identifiers = set().union(*(keys[k] for k in members))
        prefixes = [re.match(r"[a-z]+", value)[0] for value in identifiers]
        if len(prefixes) != len(set(prefixes)):
            conflicts.append(sorted(identifiers))
            continue
        if set(members).intersection(seeds):
            expanded.update(members)
            resolved_ids.update(identifiers)
            if len({parsed[k][0]["paper_id"] for k in members}) > 1:
                used.append(dict(catalogue_ids=sorted(identifiers), record_ids=sorted(members),
                    paper_ids=sorted({parsed[k][0]["paper_id"] for k in members})))
    return expanded, dict(resolved_catalogue_ids=sorted(resolved_ids),
        cross_paper_entity_groups=used, entity_resolution_conflicts=conflicts,
        identity_expanded_seed_count=len(expanded-set(seeds)))
