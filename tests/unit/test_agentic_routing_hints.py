"""Generic routing regressions, not scientific entailment or question-specific gold."""
import pytest

from src.api.rag.question_coverage import requests_baseline_and_effect
from src.api.rag.modes.agentic.method_evidence import reported_method_names


@pytest.mark.parametrize("question, expected", [
    ("Report the mass supply rate and sensitivity to disk outer radius.", True),
    ("Report baseline flux and its sensitivity to pressure.", True),
    ("Report sensitivity to pressure and the baseline flux.", True),
    ("Report sensitivity to pressure and report the measured flux.", True),
    ("Report sensitivity to pressure and temperature.", False),
    ("Report sensitivity to temperature and density.", False),
    ("How does flux change with pressure?", False),
    ("What is the sensitivity of flux to pressure?", False),
    ("How could we test sensitivity to pressure?", False),
])
def test_joint_measurement_effect_routing_does_not_invent_baselines(question, expected):
    assert requests_baseline_and_effect(question) is expected


@pytest.mark.parametrize("text, expected", [
    ("The snowballing algorithm identifies pairs.", ["snowballing"]),
    ("The Gate algorithm selects members; a separate routine finds pairs.", ["Gate"]),
    ("The Gate algorithm selects members and we propose comparing their populations.", ["Gate"]),
    ("We propose using the Gate algorithm to compare populations.", []),
    ("We could use the Gate algorithm, which selects members, to compare populations.", ["Gate"]),
    ("The measured method describes the cluster structure.", []),
    ("The mass is 8 solar masses.", []),
    ("An unnamed algorithm finds related pairs.", []),
])
def test_method_cues_preserve_reported_premises_and_ordinary_facts(text, expected):
    assert reported_method_names(text) == expected
