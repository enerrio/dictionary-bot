import pytest
from atproto.exceptions import BadRequestError, InvokeTimeoutError

from bot import client as client_module
from bot.client import BlueskyClient


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip the retry backoff and record how long each wait would have been."""
    delays = []
    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    return delays


def test_retries_until_success(monkeypatch, no_sleep):
    monkeypatch.setattr(client_module, "BLUESKY_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(client_module, "BLUESKY_RETRY_BACKOFF", 2.0)
    attempts = []

    def flaky():
        attempts.append(True)
        if len(attempts) < 3:
            raise InvokeTimeoutError
        return "session"

    assert BlueskyClient()._call_with_retry("login", flaky) == "session"
    assert len(attempts) == 3
    assert no_sleep == [2.0, 4.0]


def test_gives_up_after_max_attempts(monkeypatch, no_sleep):
    monkeypatch.setattr(client_module, "BLUESKY_MAX_ATTEMPTS", 3)
    attempts = []

    def always_timeout():
        attempts.append(True)
        raise InvokeTimeoutError

    assert BlueskyClient()._call_with_retry("login", always_timeout) is None
    assert len(attempts) == 3


def test_does_not_retry_non_network_errors(no_sleep):
    attempts = []

    def rejected():
        attempts.append(True)
        raise BadRequestError("post too long")

    assert BlueskyClient()._call_with_retry("post", rejected) is None
    assert len(attempts) == 1
    assert no_sleep == []


def test_describe_names_message_less_exceptions():
    assert client_module._describe(InvokeTimeoutError()) == "InvokeTimeoutError"
    assert client_module._describe(BadRequestError("boom")) == "BadRequestError: boom"


def test_client_uses_configured_timeout():
    timeout = BlueskyClient().client.request._client.timeout
    assert timeout.connect == client_module.BLUESKY_REQUEST_TIMEOUT
