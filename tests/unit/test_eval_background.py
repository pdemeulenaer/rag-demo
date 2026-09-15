"""Background lifecycle tests: all remote responses and clocks are offline doubles."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from openai import NotFoundError
import pytest

from evals import background as bg


def response(status="completed", response_id="resp_1"):
    return SimpleNamespace(id=response_id, status=status, model="gpt-5", output=[],
                           output_text='{"answer": "draft"}', usage=None)


@pytest.fixture
def lifecycle(monkeypatch):
    monkeypatch.setattr(bg, "sleep", lambda seconds: None)
    state = {"results": []}
    saved = []
    def save():
        saved.append(deepcopy(state))
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response("queued")),
                                                      retrieve=Mock(return_value=response())))
    return state, saved, save, client


def test_submission_and_response_id_are_durable_before_polling(lifecycle):
    state, saved, save, client = lifecycle
    def create(**kwargs):
        assert saved[-1]["background_jobs"]["q1"]["status"] == "submitting"
        assert kwargs["background"] is True and kwargs["store"] is False
        assert kwargs["timeout"] == 20
        return response("queued")
    def retrieve(response_id, **kwargs):
        assert saved[-1]["background_jobs"]["q1"]["response_id"] == response_id
        assert 0 < kwargs["timeout"] <= 20
        return response()
    client.responses.create.side_effect = create
    client.responses.retrieve.side_effect = retrieve
    assert bg.obtain_response(client, "q1", {"model": "gpt-5"}, state, save)["status"] == "completed"
    assert saved[-1]["background_jobs"]["q1"]["terminal"]["output_text"]
    client.responses.create.assert_called_once()


def test_poll_failure_resumes_get_without_another_submission(lifecycle):
    state, saved, save, client = lifecycle
    client.responses.retrieve.side_effect = httpx.RemoteProtocolError("private detail")
    with pytest.raises(httpx.RemoteProtocolError):
        bg.obtain_response(client, "q1", {}, state, save)
    assert saved[-1]["background_jobs"]["q1"]["response_id"] == "resp_1"
    client.responses.retrieve.side_effect = None
    assert bg.obtain_response(client, "q1", {}, state, save)["status"] == "completed"
    assert client.responses.create.call_count == 1
    assert client.responses.retrieve.call_count == 2


def test_disconnect_during_create_does_not_implicitly_repeat_paid_work(lifecycle):
    state, saved, save, client = lifecycle
    client.responses.create.side_effect = httpx.RemoteProtocolError("lost submission response")
    with pytest.raises(httpx.RemoteProtocolError):
        bg.obtain_response(client, "q1", {}, state, save)
    with pytest.raises(bg.BackgroundError, match="submission outcome unknown"):
        bg.obtain_response(client, "q1", {}, state, save)
    assert client.responses.create.call_count == 1
    client.responses.create.side_effect = None
    bg.obtain_response(client, "q1", {}, state, save, retry_job="q1")
    assert client.responses.create.call_count == 2
    assert state["background_history"][0]["status"] == "submitting"


def test_local_save_failure_prevents_submission(lifecycle):
    state, saved, save, client = lifecycle
    with pytest.raises(OSError):
        bg.obtain_response(client, "q1", {}, state, Mock(side_effect=OSError("disk full")))
    client.responses.create.assert_not_called()


def test_terminal_response_reused_without_api_access(lifecycle):
    state, saved, save, client = lifecycle
    first = bg.obtain_response(client, "q1", {}, state, save)
    client.responses.create.side_effect = AssertionError("No additional POST")
    client.responses.retrieve.side_effect = AssertionError("Use saved terminal output")
    assert bg.obtain_response(client, "q1", {}, state, save) == first


@pytest.mark.parametrize("status", ["failed", "incomplete", "cancelled"])
def test_terminal_failure_is_not_accepted_or_automatically_regenerated(lifecycle, status):
    state, saved, save, client = lifecycle
    client.responses.retrieve.return_value = response(status)
    for _ in range(2):
        with pytest.raises(bg.BackgroundError, match=f"background response {status}"):
            bg.obtain_response(client, "q1", {}, state, save)
    assert client.responses.create.call_count == 1
    assert client.responses.retrieve.call_count == 1
    assert state["background_jobs"]["q1"]["terminal"]["status"] == status
    client.responses.retrieve.return_value = response()
    bg.obtain_response(client, "q1", {}, state, save, retry_job="q1")
    assert client.responses.create.call_count == 2


def test_expired_response_requires_explicit_regeneration(lifecycle):
    state, saved, save, client = lifecycle
    client.responses.retrieve.side_effect = NotFoundError("private detail", body=None,
        response=httpx.Response(404, request=httpx.Request("GET", "https://example.com")))
    for _ in range(2):
        with pytest.raises(bg.BackgroundError, match="unavailable or expired"):
            bg.obtain_response(client, "q1", {}, state, save)
    assert client.responses.create.call_count == 1
    assert client.responses.retrieve.call_count == 1
    assert state["background_jobs"]["q1"]["unavailable"] is True


def test_polling_deadline_preserves_remote_job_for_resume(lifecycle, monkeypatch):
    state, saved, save, client = lifecycle
    clock = [0.0]
    monkeypatch.setattr(bg, "monotonic", lambda: clock[0])
    monkeypatch.setattr(bg, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    client.responses.retrieve.return_value = response("in_progress")
    with pytest.raises(bg.BackgroundError, match="polling wait limit reached"):
        bg.obtain_response(client, "q1", {}, state, save, wait_seconds=6)
    assert clock[0] == 6
    assert state["background_jobs"]["q1"]["response_id"] == "resp_1"
    with pytest.raises(bg.BackgroundError, match="still retrievable"):
        bg.validate_retry(state, "q1")
    client.responses.retrieve.return_value = response()
    bg.obtain_response(client, "q1", {}, state, save, wait_seconds=6)
    assert client.responses.create.call_count == 1


def test_retry_must_name_an_unresolved_job(lifecycle):
    state, saved, save, client = lifecycle
    with pytest.raises(bg.BackgroundError, match="unresolved background job"):
        bg.validate_retry(state, "typo")
    bg.obtain_response(client, "q1", {}, state, save)
    state["results"].append({"id": "q1"})
    with pytest.raises(bg.BackgroundError, match="unresolved background job"):
        bg.validate_retry(state, "q1")


def test_mismatched_poll_response_is_not_accepted(lifecycle):
    state, saved, save, client = lifecycle
    client.responses.retrieve.return_value = response(response_id="resp_wrong")
    with pytest.raises(bg.BackgroundError, match="identity mismatch"):
        bg.obtain_response(client, "q1", {}, state, save)
    assert "terminal" not in state["background_jobs"]["q1"]
