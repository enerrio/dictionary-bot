import pytest
import requests

from bot import fetch_data
from bot.fetch_data import WordDataError
from tests.conftest import make_entry

WORD_FEED_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss version="2.0"><channel>
  <title>Merriam-Webster's Word of the Day</title>
  <item>
    <title><![CDATA[Rapport]]></title>
    <link>https://www.merriam-webster.com/word-of-the-day/rapport-2026-08-10</link>
    <description><![CDATA[<p><strong>
      <font color="#000066">Merriam-Webster's Word of the Day for August 10, 2026 is:</font>
    </strong></p>
    <p><strong>Rapport</strong> &#149; \\ra-POR\\&nbsp; &#149; <em>noun</em><br />
    <p><em>Rapport</em> is a friendly relationship.</p></p>]]></description>
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
    word, part_of_speech, gloss = fetch_data.get_word_of_the_day()
    # Case is preserved so proper nouns such as "Gordian knot" read correctly
    assert word == "Rapport"
    assert part_of_speech == "noun"
    assert "friendly relationship" in gloss


def test_get_word_of_the_day_without_description(monkeypatch):
    feed = b"""<rss><channel><item><title>rapport</title></item></channel></rss>"""
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(content=feed)
    )
    assert fetch_data.get_word_of_the_day() == ("rapport", None, None)


def test_gloss_stops_before_the_examples_block():
    # The quotations below "Examples:" describe usage, not the sense itself,
    # and would otherwise outweigh the gloss when scoring homographs
    description = (
        "<p><strong>dudgeon</strong> &#149; <em>noun</em><br />"
        "<p>Dudgeon refers to a fit or state of indignation.</p></p>"
        "<p><strong>Examples:</strong><br /><p>a wood for dagger hilts</p></p>"
    )
    gloss = fetch_data._gloss_from_description(description)
    assert "indignation" in gloss
    assert "dagger" not in gloss


def test_part_of_speech_falls_back_to_first_emphasis():
    # The headword markup shifts around for some entries, so an unanchored
    # match still finds the same field
    description = "<p><b>rapport</b> &#149; <em>noun</em><br /></p>"
    assert fetch_data._part_of_speech_from_description(description, "rapport") == "noun"


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


def test_part_of_speech_missing_from_description():
    assert (
        fetch_data._part_of_speech_from_description("<p>no emphasis</p>", "x") is None
    )


def test_gloss_from_empty_description():
    assert fetch_data._gloss_from_description("") is None


def test_nested_text_ignores_non_text_leaves():
    # Sense sequences carry numbers and nulls alongside the text
    assert fetch_data._nested_text([1, None, {"a": "kept"}]).split() == ["kept"]


def test_get_webcontent_returns_response(monkeypatch):
    response = DummyResponse(content=b"ok")
    monkeypatch.setattr(fetch_data.requests, "get", lambda *a, **kw: response)
    assert fetch_data.get_webcontent("https://example.com") is response


def test_get_word_details_non_json_response(monkeypatch):
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(content=b"<html>")
    )
    with pytest.raises(WordDataError):
        fetch_data.get_word_details("rapport", "key")


def test_get_word_details_requires_api_key():
    with pytest.raises(WordDataError):
        fetch_data.get_word_details("rapport", "")


def test_get_word_details(monkeypatch, api_response):
    monkeypatch.setattr(
        fetch_data, "get_webcontent", lambda url: DummyResponse(json_data=api_response)
    )
    assert fetch_data.get_word_details("rapport", "key") == api_response


def test_get_word_details_encodes_multi_word_headwords(monkeypatch, api_response):
    requested = []

    def capture(url):
        requested.append(url)
        return DummyResponse(json_data=api_response)

    monkeypatch.setattr(fetch_data, "get_webcontent", capture)
    fetch_data.get_word_details("Gordian knot", "key")
    assert "Gordian%20knot" in requested[0]
    assert " " not in requested[0]


def test_get_word_details_retries_accented_word_unaccented(monkeypatch):
    # "élan" returns nothing but spelling suggestions; the entry is under "elan"
    entry = [make_entry("elan", "noun", "{bc}vigorous spirit or enthusiasm")]
    requested = []

    def lookup(url):
        requested.append(url)
        suggestions = ["clan", "flan", "eland"]
        return DummyResponse(json_data=suggestions if len(requested) == 1 else entry)

    monkeypatch.setattr(fetch_data, "get_webcontent", lookup)
    assert fetch_data.get_word_details("élan", "key") == entry
    assert len(requested) == 2


def test_get_word_details_does_not_retry_when_entries_are_returned(monkeypatch):
    entry = [make_entry("élan", "noun", "{bc}vigorous spirit")]
    requested = []

    def lookup(url):
        requested.append(url)
        return DummyResponse(json_data=entry)

    monkeypatch.setattr(fetch_data, "get_webcontent", lookup)
    assert fetch_data.get_word_details("élan", "key") == entry
    assert len(requested) == 1


def test_headword_matches_across_accents():
    # The feed spells it "élan" while the entry is filed under "elan"
    response = [make_entry("elan", "noun", "{bc}vigorous spirit or enthusiasm")]
    content = fetch_data.parse_word_details(response, "élan", "noun")
    assert content["definition"] == "vigorous spirit or enthusiasm"


def test_parse_word_details(api_response):
    content = fetch_data.parse_word_details(api_response, "rapport")
    assert content["pos"] == "noun"
    # Only the pronunciation with a sound file is used
    assert content["pronunciation"] == "ra-ˈpȯr"
    assert content["definition"] == "a friendly, harmonious relationship"


def test_parse_word_details_without_pronunciation(api_response):
    del api_response[0]["hwi"]["prs"]
    content = fetch_data.parse_word_details(api_response, "rapport")
    assert "pronunciation" not in content


def test_parse_word_details_omits_quotes(api_response):
    # Quotes are not part of the post and would risk the 300 character limit
    api_response[0]["quotes"] = [{"t": "They had an easy {it}rapport{/it}."}]
    assert "quote" not in fetch_data.parse_word_details(api_response, "rapport")


def test_parse_word_details_no_match():
    # A miss returns a list of suggested spellings instead of entry objects
    with pytest.raises(WordDataError):
        fetch_data.parse_word_details(["rapport", "report"], "rapport")


def test_parse_word_details_unexpected_shape(api_response):
    del api_response[0]["def"]
    with pytest.raises(WordDataError):
        fetch_data.parse_word_details(api_response, "rapport")


def test_parse_word_details_missing_sense_text(api_response):
    api_response[0]["def"][0]["sseq"][0] = [["bs", {}]]
    with pytest.raises(WordDataError):
        fetch_data.parse_word_details(api_response, "rapport")


def test_definitional_break_separates_senses():
    # {bc} renders as a colon; dropping it ran consecutive senses together
    assert (
        fetch_data._strip_markup("{bc}to set right {bc}{sx|remedy||}")
        == "to set right : remedy"
    )


def test_leading_definitional_break_is_not_a_separator():
    assert (
        fetch_data._strip_markup("{bc}an intricate problem") == "an intricate problem"
    )


def test_strip_markup_keeps_link_text():
    assert fetch_data._strip_markup("{bc}see {sx|halcyon||}") == "see halcyon"


def test_strip_markup_drops_cross_reference_sense_number():
    # "{sx|burden:1||}" once posted as the literal text "burden:1"
    assert fetch_data._strip_markup("{bc}{sx|burden:1||}") == "burden"


def test_strip_markup_removes_formatting_tokens_and_whitespace():
    assert (
        fetch_data._strip_markup("{bc}a {it}fun{/it}  gathering ") == "a fun gathering"
    )


def test_select_entry_prefers_homograph_matching_feed_pos():
    # "nurture" leads with the noun, but the word of the day was the verb
    response = [
        make_entry("nurture:1", "noun", "{bc}training, upbringing"),
        make_entry("nurture:2", "verb", "{bc}to supply with nourishment"),
    ]
    content = fetch_data.parse_word_details(response, "nurture", "verb")
    assert content["pos"] == "verb"
    assert content["definition"] == "to supply with nourishment"


def test_select_entry_uses_gloss_when_homographs_share_a_pos(homograph_response):
    # Both "dudgeon" homographs are nouns, so only the feed's gloss separates
    # them; the archaic sense sorts first and was once posted by mistake
    gloss = "Dudgeon is a literary word referring to a fit or state of indignation."
    content = fetch_data.parse_word_details(
        homograph_response, "dudgeon", "noun", gloss
    )
    assert content["definition"] == "a fit or state of indignation"


def test_select_entry_keeps_dictionary_order_when_gloss_matches_nothing(
    homograph_response,
):
    content = fetch_data.parse_word_details(
        homograph_response, "dudgeon", "noun", "unrelated wording entirely"
    )
    assert content["definition"] == "a wood used especially for dagger hilts"


def test_select_entry_ignores_phrases_containing_the_word():
    # "in high dudgeon" is a different headword and must never be chosen, even
    # though its wording matches the gloss closely
    response = [
        make_entry("in high dudgeon", "phrase", "{bc}feeling angry or offended"),
        make_entry("dudgeon:2", "noun", "{bc}a fit or state of indignation"),
    ]
    content = fetch_data.parse_word_details(
        response, "dudgeon", "noun", "feeling angry or offended in high dudgeon"
    )
    assert content["definition"] == "a fit or state of indignation"


def test_select_entry_skips_entries_without_definitions():
    # Variant entries such as "cruces" point at another entry and define nothing
    response = [
        {"meta": {"id": "cruces"}, "hwi": {"hw": "cruces"}},
        make_entry("crux", "noun", "{bc}a puzzling or difficult problem"),
    ]
    content = fetch_data.parse_word_details(response, "crux", "noun")
    assert content["definition"] == "a puzzling or difficult problem"


def test_select_entry_matches_headword_case_insensitively():
    # The feed says "gordian knot" while the entry id is "Gordian knot"
    response = [
        make_entry("cut the Gordian knot", "phrase", "{bc}to solve a problem boldly"),
        make_entry("Gordian knot", "noun", "{bc}an intricate problem"),
    ]
    content = fetch_data.parse_word_details(response, "gordian knot", "noun")
    assert content["definition"] == "an intricate problem"


def test_select_entry_falls_back_when_no_headword_matches():
    response = [make_entry("elan vital", "noun", "{bc}the vital force")]
    content = fetch_data.parse_word_details(response, "élan", "noun")
    assert content["definition"] == "the vital force"


def test_select_entry_falls_back_when_no_pos_matches(homograph_response):
    content = fetch_data.parse_word_details(homograph_response, "dudgeon", "verb")
    assert content["pos"] == "noun"


def test_pronunciation_drops_dangling_hyphen():
    # Multi-word entries only carry the first word's pronunciation
    response = [
        make_entry(
            "Gordian knot",
            "noun",
            "{bc}an intricate problem",
            [{"mw": "ˈgȯr-dē-ən-", "sound": {"audio": "gordi01"}}],
        )
    ]
    content = fetch_data.parse_word_details(response, "Gordian knot", "noun")
    assert content["pronunciation"] == "ˈgȯr-dē-ən"


def test_pronunciation_keeps_hyphen_for_combining_forms():
    response = [
        make_entry(
            "pan-", "combining form", "{bc}all", [{"mw": "ˈpan-", "sound": {"a": "p"}}]
        )
    ]
    content = fetch_data.parse_word_details(response, "pan-", "combining form")
    assert content["pronunciation"] == "ˈpan-"
