"""Regression coverage for the first pilot's sampling and answerability failures."""
import json
import random
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from evals import generate_questions as gen
from evals.quality import POLICY, evidence_priority
from tests.unit.test_eval_generation import chunk, fake_client, prepared, proposal


@pytest.mark.parametrize("text,section", [
    ("A bibliography entry " * 15, "References"),
    ("Funding was supplied by the observatory. " * 10, "ACKNOWLEDGMENTS"),
    ("## **REFERENCES**\n\nEntries " * 15, ""),
    ("- Ivans et al. 1999, AJ, 118, doi: 10.1/a\n- Jones et al. 2005, MNRAS, doi: 10.1/b", ""),
    ("**==> picture [410 x 185] intentionally omitted <==**\n" * 10, "Results"),
])
def test_unhelpful_evidence_excluded(text, section):
    assert evidence_priority(text, section) is None


def test_caption_with_scientific_content_is_retained():
    text = "**==> picture [410 x 185] intentionally omitted <==**\n" + (
        "Figure 2 shows a 0.15 dex iron abundance difference producing a 0.03 mag color variation.")
    assert evidence_priority(text, "Results") == 0


def test_sampler_prefers_substantive_sections_with_deterministic_fallback():
    text = "The measured iron abundance difference is 0.15 dex and the corresponding color shift is 0.03 mag. " * 3
    sections = ["References", "Acknowledgments", "Introduction", "Methods", "Results", "Conclusions"]
    points = [SimpleNamespace(id=str(i), payload={"text": text, "type": "text",
        "build_id": "b", "paper_id": "p", "paper_version": 1, "section_header": section})
        for i, section in enumerate(sections)]
    build = {"id": "b", "paper_id": "p", "version": 1, "source": "arxiv", "collection": "c",
             "metadata": {"title": "Cluster colors"}, "manifest": {"point_ids": [p.id for p in points]}}
    client = Mock()
    client.retrieve.return_value = points
    selected = gen.sample_evidence(client, build, random.Random(42), 2)
    assert all(p["section_header"] in {"Methods", "Results", "Conclusions"} for p in selected)
    assert all(p["text"] == text for p in selected)
    client.retrieve.return_value = list(reversed(points))
    assert gen.sample_evidence(client, build, random.Random(42), 2) == selected
    assert len(gen.sample_evidence(client, build, random.Random(42), 5)) == 4


@pytest.mark.parametrize("answer", [
    "The provided excerpts do not give explicit numeric ranges for Teff or metallicity.",
    "Abstain. The minimum detectable metallicity cannot be determined from the provided excerpts.",
    "The precision is not specified, so additional information is required.",
    "A minimum difference cannot be calculated without the uncertainties.",
])
def test_answerable_missing_information_rejected(answer):
    candidate = proposal(question="According to Cluster masses, what is the measurement?")
    candidate.candidate.reference_answer = answer
    with pytest.raises(gen.EvaluationError, match="answerable_candidate_missing_information"):
        gen.validate_candidate(candidate, {"id": "q1", "kind": "single_paper", "evidence_ids": ["e1"]},
                               {"e1": chunk()}, set(), quality_policy=POLICY)


def test_supported_negative_finding_is_not_an_abstention():
    candidate = proposal(question="According to Cluster masses, did the color change?")
    candidate.candidate.reference_answer = "The authors found no significant color change."
    result = gen.validate_candidate(candidate, {"id": "q1", "kind": "single_paper", "evidence_ids": ["e1"]},
                                    {"e1": chunk()}, set(), quality_policy=POLICY)
    assert result["review_status"] == "needs_review"


def test_abstaining_negative_remains_excerpt_scoped():
    candidate = proposal([], question="According to Cluster masses, what is the distance error?")
    candidate.candidate.reference_answer = "Abstain: the distance uncertainty is not provided."
    result = gen.validate_candidate(candidate, {"id": "q1", "kind": "unanswerable_candidate", "evidence_ids": ["e1"]},
                                    {"e1": chunk()}, set(), quality_policy=POLICY)
    assert result["reference_evidence"] == []
    assert result["answerability_scope"] == "supplied_excerpts_only"


def test_cross_paper_requires_both_titles():
    evidence = {"e1": chunk(), "e2": {**chunk("e2", "p2"), "title": "Cluster colors"}}
    job = {"id": "q1", "kind": "cross_paper", "evidence_ids": list(evidence)}
    candidate = proposal(["e1", "e2"], question="How do Cluster masses and this paper compare?")
    with pytest.raises(gen.EvaluationError, match="question_missing_paper_title"):
        gen.validate_candidate(candidate, job, evidence, set(), quality_policy=POLICY)
    candidate.candidate.question = 'How do “Cluster masses” and “Cluster colors” compare?'
    assert gen.validate_candidate(candidate, job, evidence, set(), quality_policy=POLICY)


def test_metadata_discovery_hides_title_in_question_and_names_it_in_answer():
    evidence = {"e1": chunk()}
    job = {"id": "q1", "kind": "single_paper", "profile": "metadata_discovery",
           "evidence_ids": ["e1"]}
    candidate = proposal(question="Which stellar-dynamics study estimated a mass of 100 solar masses?")
    candidate.candidate.reference_answer = "Cluster masses reports an estimate of 100 solar masses."
    assert gen.validate_candidate(candidate, job, evidence, set(), quality_policy=POLICY)
    candidate.candidate.question = "What mass was estimated in Cluster masses?"
    with pytest.raises(gen.EvaluationError, match="reveals_paper_title"):
        gen.validate_candidate(candidate, job, evidence, set(), quality_policy=POLICY)


def test_new_policy_rejects_bad_drafts_and_completed_rerun_stays_free(prepared):
    plan = json.loads((prepared / "plan.json").read_text())
    plan["quality_policy"] = POLICY
    gen.write_json(prepared / "plan.json", plan)
    client = fake_client()  # Valid IDs but unnamed papers: these must now fail review gates.
    gen.generate(prepared, lambda: client)
    state = json.loads((prepared / "results.json").read_text())
    assert all(r["rejection"] == "question_missing_paper_title" for r in state["results"])
    gen.generate(prepared, Mock(side_effect=AssertionError("Completed results are immutable")))
