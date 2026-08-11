import pytest
import requests

from bot import fetch_data
from bot.fetch_data import WordDataError

WORD_FEED_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss version="2.0"><channel>
  <title>Merriam-Webster's Word of the Day</title>
  <item>
    <title><![CDATA[Rapport]]></title>
    <link>https://www.merriam-webster.com/word-of-the-day/rapport-2026-08-10</link>
  </item>
  <item>
    <title><![CDATA[yesterday]]></title>
  </item>
</channel></rss>
"""


class DummyResponse:
    def __init__(self, content=b"", json_data=None):
        self.content = content
        self._json_data = json_data

    def raise_for_status(self):
        return None

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


def test_get_word_of_the_day(monkeypatch):
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(content=WORD_FEED_XML)
    )
    # The most recent item wins over older entries in the feed
    assert fetch_data.get_word_of_the_day() == "rapport"


def test_get_word_of_the_day_empty_feed(monkeypatch):
    monkeypatch.setattr(
        fetch_data,
        "get_webcontent",
        lambda url: DummyResponse(content=b"<rss><channel></channel></rss>"),
    )
    with pytest.raises(WordDataError):
        fetch_data.get_word_of_the_day()


def test_get_word_of_the_day_invalid_xml(monkeypatch):
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(content=b"not xml <<<")
    )
    with pytest.raises(WordDataError):
        fetch_data.get_word_of_the_day()


def test_get_webcontent_raises_on_request_error(monkeypatch):
    def boom(url, headers, timeout):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(fetch_data.requests, "get", boom)
    with pytest.raises(WordDataError):
        fetch_data.get_webcontent("https://example.com")


def test_get_word_details_requires_api_key():
    with pytest.raises(WordDataError):
        fetch_data.get_word_details("rapport", "")


def test_get_word_details(monkeypatch, api_response):
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(json_data=api_response)
    )
    assert fetch_data.get_word_details("rapport", "key") == api_response


def test_parse_word_details(api_response):
    content = fetch_data.parse_word_details(api_response)
    assert content["pos"] == "noun"
    # Only the pronunciation with a sound file is used
    assert content["pronunciation"] == "ra-ˈpȯr"
    assert content["definition"] == "a friendly, harmonious relationship"
    assert content["quote"] == "They had an easy rapport."


def test_parse_word_details_without_pronunciation(api_response):
    del api_response[0]["hwi"]["prs"]
    content = fetch_data.parse_word_details(api_response)
    assert "pronunciation" not in content


def test_parse_word_details_no_match():
    # A miss returns a list of suggested spellings instead of entry objects
    with pytest.raises(WordDataError):
        fetch_data.parse_word_details(["rapport", "report"])


def test_parse_word_details_unexpected_shape(api_response):
    del api_response[0]["def"]
    with pytest.raises(WordDataError):
        fetch_data.parse_word_details(api_response)


def test_strip_markup_keeps_link_text():
    assert fetch_data._strip_markup("{bc}see {sx|halcyon||}") == "see halcyon"
