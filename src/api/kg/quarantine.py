"""Deterministic holding rules; no inferred endpoints or scientific auto-approval."""
from .scientific_schema import role_issues

POLICY_VERSION = "record-quarantine-v1"


def quarantine_report(batch):
    reasons = {}
    kinds = {}
    paths = {}

    def hold(record, kind, code, path=None):
        reasons.setdefault(record.id, [])
        if code not in reasons[record.id]:
            reasons[record.id].append(code)
        kinds[record.id] = kind
        if path:
            paths.setdefault(record.id, []).append(path)

    for record in batch.observations:
        for flag in getattr(record, "quality_flags", []):
            hold(record, "observation", flag)
    if batch.schema_version == "scientific-kg-v3":
        entities = {record.id for record in batch.entities}
        nodes = entities | {record.id for record in batch.observations}
        for index, record in enumerate(batch.observations):
            if record.subject_id not in entities:
                hold(record, "observation", "undeclared_observation_subject", f"observations.{index}.subject_id")
        for index, record in enumerate(batch.relationships):
            for field in ("subject_id", "object_id"):
                if getattr(record, field) not in nodes:
                    hold(record, "relationship", "undeclared_relationship_endpoint", f"relationships.{index}.{field}")
        for issue in role_issues(batch.entities, batch.observations, batch.relationships):
            index = int(issue["path"].split(".")[1])
            hold(batch.relationships[index], "relationship", "invalid_relationship_role", issue["path"])
    excluded = set(reasons)
    for record in batch.relationships:
        if record.subject_id in excluded or record.object_id in excluded:
            hold(record, "relationship", "quarantined_endpoint")
    return [dict(record_id=record.id, record_type=kinds[record.id], reasons=reasons[record.id])
            | (dict(paths=paths[record.id]) if record.id in paths else {})
            for record in [*batch.entities, *batch.observations, *batch.relationships] if record.id in reasons]
