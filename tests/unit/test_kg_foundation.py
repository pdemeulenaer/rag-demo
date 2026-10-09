"""Offline KG foundation tests: no services, .env, model calls or embeddings."""
from copy import deepcopy
import json
from pathlib import Path
import shlex
import subprocess
import sys
from uuid import UUID

import pytest
from pydantic import ValidationError
import yaml

from src.api.kg.__main__ import main
from src.api.kg.contracts import ExtractionBatch, SourceChunk
from src.api.kg.preview import DEFAULT_PILOT, PilotSelection, preview


ROOT = Path(__file__).resolve().parents[2]
PAPER = "00000000-0000-0000-0000-000000000001"
BUILD = "00000000-0000-0000-0000-000000000002"
POINT = "00000000-0000-0000-0000-000000000003"
OTHER = "00000000-0000-0000-0000-000000000004"


@pytest.fixture
def source():
    return dict(paper_id=PAPER, build_id=BUILD, collection="arxiv_papers_v2",
                point_id=POINT, source="arxiv", page_number=3,
                section_header="Results", text="M22 has distance 3.27 ± 0.14 kpc.")


@pytest.fixture
def batch(source):
    evidence = {key: value for key, value in source.items() if key != "text"}
    evidence["quote"] = source["text"]
    return dict(
        paper_id=PAPER, build_id=BUILD, extraction_model="test-model",
        extraction_revision="test-prompt-v1",
        entities=[dict(id="object-1", kind="astronomical_object", name="M22",
                       aliases=[], evidence=[deepcopy(evidence)])],
        observations=[dict(id="observation-1", subject_id="object-1", kind="measurement",
                           statement=source["text"], quantity="distance", value_text="3.27",
                           unit_text="kpc", uncertainty_text="± 0.14",
                           conditions=["RR Lyrae sample"], evidence=[deepcopy(evidence)])],
        relationships=[],
    )


def test_schema_preserves_measurement_uncertainty_and_provenance(batch, source):
    extraction = ExtractionBatch.model_validate(batch)
    extraction.validate_sources([SourceChunk.model_validate(source)])
    observation = extraction.observations[0]
    assert observation.value_text == "3.27"
    assert observation.uncertainty_text == "± 0.14"
    assert observation.evidence[0].point_id == UUID(POINT)
    assert observation.conditions == ["RR Lyrae sample"]


def test_conflicting_measurements_are_separate_observations(batch, source):
    alternative = deepcopy(batch["observations"][0])
    alternative.update(id="observation-2", value_text="3.31", uncertainty_text="± 0.17",
                       conditions=["SX Phe sample"], statement="Distance 3.31 ± 0.17 kpc.")
    alternative["evidence"][0]["quote"] = alternative["statement"]
    batch["observations"].append(alternative)
    source["text"] += " " + alternative["statement"]
    extraction = ExtractionBatch.model_validate(batch)
    extraction.validate_sources([SourceChunk.model_validate(source)])
    assert len(extraction.observations) == 2


@pytest.mark.parametrize("field", ["paper_id", "build_id"])
def test_cross_build_or_paper_evidence_is_rejected(batch, field):
    batch["observations"][0]["evidence"][0][field] = OTHER
    with pytest.raises(ValidationError, match="extraction build"):
        ExtractionBatch.model_validate(batch)


@pytest.mark.parametrize("field,value", [
    ("point_id", OTHER), ("collection", "old_collection"), ("page_number", 4),
    ("section_header", "Methods"), ("source", "uploads"),
    ("quote", "M22 has distance 9.99 kpc."),
])
def test_stale_metadata_or_invented_quote_is_rejected(batch, source, field, value):
    batch["observations"][0]["evidence"][0][field] = value
    extraction = ExtractionBatch.model_validate(batch)
    with pytest.raises(ValueError):
        extraction.validate_sources([SourceChunk.model_validate(source)])


def test_empty_evidence_is_rejected(batch):
    batch["entities"][0]["evidence"] = []
    with pytest.raises(ValidationError):
        ExtractionBatch.model_validate(batch)


def test_duplicate_record_ids_are_rejected(batch):
    batch["observations"][0]["id"] = "object-1"
    with pytest.raises(ValidationError, match="unique"):
        ExtractionBatch.model_validate(batch)


def test_dangling_observation_is_rejected(batch):
    batch["observations"][0]["subject_id"] = "invented-object"
    with pytest.raises(ValidationError, match="declared entity"):
        ExtractionBatch.model_validate(batch)


def test_dangling_relationship_is_rejected(batch):
    batch["relationships"] = [dict(
        id="edge-1", subject_id="object-1", predicate="located_in", object_id="missing",
        epistemic_status="reported", evidence=deepcopy(batch["entities"][0]["evidence"]),
    )]
    with pytest.raises(ValidationError, match="declared nodes"):
        ExtractionBatch.model_validate(batch)


def test_origin_hypothesis_cannot_be_promoted_to_established_relationship(batch):
    batch["relationships"] = [dict(
        id="edge-1", subject_id="object-1", predicate="proposes_origin",
        object_id="object-1", epistemic_status="reported",
        evidence=deepcopy(batch["entities"][0]["evidence"]),
    )]
    with pytest.raises(ValidationError, match="hypotheses"):
        ExtractionBatch.model_validate(batch)
    batch["relationships"][0]["epistemic_status"] = "hypothesis"
    assert ExtractionBatch.model_validate(batch).relationships[0].epistemic_status == "hypothesis"


def test_duplicate_source_chunks_are_rejected(batch, source):
    chunk = SourceChunk.model_validate(source)
    with pytest.raises(ValueError, match="Duplicate"):
        ExtractionBatch.model_validate(batch).validate_sources([chunk, chunk])


def test_unknown_extraction_fields_are_rejected(batch):
    batch["gold_answer"] = "must not enter the extraction contract"
    with pytest.raises(ValidationError):
        ExtractionBatch.model_validate(batch)


@pytest.fixture
def snapshot(tmp_path):
    pilot = PilotSelection.model_validate_json(DEFAULT_PILOT.read_text(encoding="utf-8"))
    papers = [dict(paper_id=str(paper.paper_id), build_id=str(UUID(int=index + 100)),
                   title=paper.title, source="arxiv", collection="arxiv_papers_v2", version=2)
              for index, paper in enumerate(pilot.papers)]
    papers.append(dict(paper_id=OTHER, build_id=BUILD, title="Unrelated paper",
                       source="arxiv", collection="arxiv_papers_v2", version=1))
    payload = dict(schema_version=1, corpus_fingerprint="fixture-corpus", papers=papers,
                   active_build_ids=[paper["build_id"] for paper in papers])
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_pilot_is_explicit_and_preview_is_read_only(snapshot, monkeypatch):
    path, _ = snapshot
    original = path.read_bytes()
    original_read = Path.read_text

    def safe_read(self, *args, **kwargs):
        assert self.name != ".env"
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", safe_read)
    result = preview(path)
    assert result["papers_selected"] == 7
    assert result["papers_available"] == 8
    assert {paper["group"] for paper in result["papers"]} == {
        "M22", "omega-centauri", "47-tucanae", "connecting-survey",
    }
    assert result["model_calls"] == result["database_writes"] == 0
    assert result["graph_ready"] is False
    assert path.read_bytes() == original


def test_all_selection_includes_disconnected_papers(snapshot):
    result = preview(snapshot[0], selection="all", pilot_path=Path("does-not-exist.json"))
    assert result["papers_selected"] == 8
    assert any(paper["title"] == "Unrelated paper" for paper in result["papers"])


def test_missing_pilot_paper_fails_instead_of_silent_subset(snapshot):
    path, payload = snapshot
    payload["papers"].pop(0)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Pilot papers missing"):
        preview(path)


@pytest.mark.parametrize("mutation", ["duplicate_paper", "duplicate_build", "outside_scope"])
def test_ambiguous_or_out_of_scope_snapshot_is_rejected(snapshot, mutation):
    path, payload = snapshot
    if mutation == "duplicate_paper":
        payload["papers"][1]["paper_id"] = payload["papers"][0]["paper_id"]
    elif mutation == "duplicate_build":
        payload["papers"][1]["build_id"] = payload["papers"][0]["build_id"]
    else:
        payload["active_build_ids"] = []
    path.write_text(json.dumps(payload))
    with pytest.raises(ValidationError):
        preview(path)


def test_invalid_selection_fails(snapshot):
    with pytest.raises(ValueError, match="Selection"):
        preview(snapshot[0], selection="unknown")


def test_pilot_contains_no_duplicates():
    payload = json.loads(DEFAULT_PILOT.read_text(encoding="utf-8"))
    payload["papers"].append(payload["papers"][0])
    with pytest.raises(ValidationError, match="duplicate"):
        PilotSelection.model_validate(payload)


def test_cli_preview_and_schema(snapshot, capsys):
    main(["preview", "--snapshot", str(snapshot[0])])
    assert json.loads(capsys.readouterr().out)["papers_selected"] == 7
    main(["schema"])
    assert "EvidenceReference" in json.loads(capsys.readouterr().out)["$defs"]


def test_cli_malformed_input_fails_without_exposing_input(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text('{"secret": "do-not-print-this"}')
    with pytest.raises(SystemExit) as error:
        main(["preview", "--snapshot", str(path)])
    assert error.value.code == 1
    assert "do-not-print-this" not in capsys.readouterr().err


def test_cli_does_not_import_application_settings():
    result = subprocess.run([sys.executable, "-c", (
        "import sys; import src.api.kg.__main__; "
        "assert 'src.api.core.config' not in sys.modules; "
        "assert 'src.api.papers.settings' not in sys.modules; "
        "assert 'dotenv' not in sys.modules"
    )], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_make_preview_preserves_quoted_paths():
    result = subprocess.run([
        "make", "--no-print-directory", "--dry-run", "kg-preview",
        "KG_SNAPSHOT=data/my snapshot.json", "KG_SELECTION=all", "KG_PILOT=my pilot.json",
    ], cwd=ROOT, capture_output=True, text=True, check=True)
    assert shlex.split(result.stdout) == [
        "uv", "run", "python", "-m", "src.api.kg", "preview", "--snapshot",
        "data/my snapshot.json", "--selection", "all", "--pilot", "my pilot.json",
    ]


def test_neo4j_is_optional_pinned_local_and_durable():
    compose = yaml.safe_load((ROOT / "docker-compose.kg.yml").read_text())
    service = compose["services"]["neo4j"]
    assert service["profiles"] == ["kg"]
    assert service["image"] == "neo4j:2026.09.0"
    assert all(port.startswith("127.0.0.1:") for port in service["ports"])
    assert "neo4j_data:/data" in service["volumes"]
    assert "env_file" not in service
    assert "neo4j" not in yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]


def test_make_kg_up_only_announces_success_and_does_not_remove_volumes():
    result = subprocess.run(["make", "--no-print-directory", "--dry-run", "kg-up", "kg-stop"],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()
    assert lines[0] == "set -e"
    assert "up -d --wait neo4j" in lines[1]
    assert "Neo4j Browser" in lines[2]
    assert "stop neo4j" in lines[3]
    assert "down" not in result.stdout
