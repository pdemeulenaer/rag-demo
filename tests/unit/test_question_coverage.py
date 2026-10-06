import pytest

from src.api.rag.question_coverage import original_question_parts, requests_parameter_effect


@pytest.mark.parametrize("labels", [("a", "b"), ("1", "2")])
def test_enumerated_requests_are_checked_independently(labels):
    first, second = labels
    parts = original_question_parts(f"Compare studies. ({first}) Report mass. ({second}) Report distance dependence.")
    assert [key for key, _ in parts] == [f"q_{first}", f"q_{second}"]
    assert "Report mass" in parts[0][1]
    assert "distance dependence" in parts[1][1]


@pytest.mark.parametrize("question", [
    "Compare equations (1) and (2).", "Compare references (4) and (8).",
    "Report (1) the mass and (1) its uncertainty.", "Report mass.",
    "(1) Report mass. (a) Report age.",
])
def test_non_request_numbering_falls_back_to_the_whole_question(question):
    assert original_question_parts(question) == [("q_original", question)]


@pytest.mark.parametrize("question", [
    "Report the mass sensitivity to distance.",
    "Describe the outcome dependence on the boundary condition.",
    "What is the effect of resolution on the measured size?",
    "How does the mass change when distance varies?",
    "How could the measured dependence on distance explain the findings?",
])
def test_parameter_effect_schema_is_selected_for_reported_relationships(question):
    assert requests_parameter_effect(question)


@pytest.mark.parametrize("question", [
    "Report the instrument sensitivity limit.",
    "What distances were tested?",
    "Propose a test of the effect of resolution on size.",
    "How could the rate change with distance?",
    "Report the mass in solar masses.",
])
def test_settings_limits_and_proposed_experiments_do_not_require_reported_effects(question):
    assert not requests_parameter_effect(question)
