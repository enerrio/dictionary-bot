from bot import post
from bot.fetch_data import WordDataError, WordOfTheDay


def _fail(message):
    raise AssertionError(message)


def _stub_fetch(monkeypatch, api_response):
    monkeypatch.setattr(
        post,
        "get_word_of_the_day",
        lambda: WordOfTheDay("rapport", "noun", "a friendly relationship"),
    )
    monkeypatch.setattr(post, "get_word_details", lambda word, key: api_response)


def test_run_debug_does_not_post(monkeypatch, api_response):
    monkeypatch.setattr(post, "DEBUG", True)
    _stub_fetch(monkeypatch, api_response)
    monkeypatch.setattr(
        post.BlueskyClient,
        "login",
        lambda self, username, password: _fail("login should not be called"),
    )

    assert post.run() is True


def test_run_skips_when_already_posted(monkeypatch):
    monkeypatch.setattr(post, "DEBUG", False)
    monkeypatch.setattr(post, "already_posted_today", lambda: True)
    monkeypatch.setattr(post, "get_word_of_the_day", lambda: _fail("should not fetch"))

    assert post.run() is True


def test_run_returns_false_when_word_data_unavailable(monkeypatch):
    monkeypatch.setattr(post, "DEBUG", False)
    monkeypatch.setattr(post, "already_posted_today", lambda: False)
    monkeypatch.setattr(
        post,
        "get_word_of_the_day",
        lambda: (_ for _ in ()).throw(WordDataError("boom")),
    )

    assert post.run() is False


def test_run_login_failure(monkeypatch, api_response):
    monkeypatch.setattr(post, "DEBUG", False)
    monkeypatch.setattr(post, "already_posted_today", lambda: False)
    _stub_fetch(monkeypatch, api_response)
    monkeypatch.setattr(
        post.BlueskyClient, "login", lambda self, username, password: None
    )

    assert post.run() is False


def test_run_production_success(monkeypatch, api_response):
    recorded = []
    monkeypatch.setattr(post, "DEBUG", False)
    monkeypatch.setattr(post, "already_posted_today", lambda: False)
    monkeypatch.setattr(post, "record_post", lambda: recorded.append(True))
    _stub_fetch(monkeypatch, api_response)
    monkeypatch.setattr(
        post.BlueskyClient, "login", lambda self, username, password: "fake_session"
    )
    monkeypatch.setattr(post.BlueskyClient, "post", lambda self, text: "fake_response")

    assert post.run() is True
    assert recorded == [True]


def test_run_production_failure_does_not_record(monkeypatch, api_response):
    recorded = []
    monkeypatch.setattr(post, "DEBUG", False)
    monkeypatch.setattr(post, "already_posted_today", lambda: False)
    monkeypatch.setattr(post, "record_post", lambda: recorded.append(True))
    _stub_fetch(monkeypatch, api_response)
    monkeypatch.setattr(
        post.BlueskyClient, "login", lambda self, username, password: "fake_session"
    )
    monkeypatch.setattr(post.BlueskyClient, "post", lambda self, text: None)

    assert post.run() is False
    assert recorded == []
