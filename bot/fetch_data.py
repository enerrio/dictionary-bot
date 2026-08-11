import re
import unicodedata
from html import unescape
from typing import Any, NamedTuple
from urllib.parse import quote
from xml.etree import ElementTree

import requests

from config.settings import MERRIAM_WEBSTER_API_URL, WORD_OF_THE_DAY_FEED_URL


class WordDataError(RuntimeError):
    """Raised when the word of the day cannot be retrieved or parsed."""


class WordOfTheDay(NamedTuple):
    """Today's word, plus the two hints the feed gives about which sense it is.

    The API returns a separate entry per homograph and only one of them is the
    word of the day, so the part of speech and the feed's plain-English gloss
    are carried along to pick the right one.
    """

    word: str
    part_of_speech: str | None
    gloss: str | None


# Merriam-Webster's site returns 403 for the default python-requests user agent
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def get_webcontent(url: str, timeout: int = 15) -> requests.models.Response:
    """Get the web contents from a given URL.

    Args:
        url (str): URL to request.
        timeout (int): Seconds to wait for the response.

    Returns:
        requests.models.Response: Response to GET containing web contents.
    """
    try:
        page = requests.get(url, headers=HEADERS, timeout=timeout)
        page.raise_for_status()
    except requests.RequestException as err:
        raise WordDataError(f"Request to {url} failed: {err}") from err
    return page


def _part_of_speech_from_description(description: str, word: str) -> str | None:
    """Pull the part of speech out of a feed item's description.

    The description opens with a line shaped like
    ``<strong>word</strong> • \\pronunciation\\ • <em>adjective</em>``.

    Args:
        description (str): Inner HTML of the feed item's description.
        word (str): Headword the description belongs to.

    Returns:
        str | None: Part of speech, or None if it cannot be located.
    """
    if not description:
        return None
    # Prefer the emphasis that follows the headword, but the first one in the
    # description is the same field whenever the headword markup shifts around
    anchored = re.search(
        rf"<strong>\s*{re.escape(word)}\s*</strong>.*?<em>([^<]+)</em>",
        description,
        re.IGNORECASE | re.DOTALL,
    )
    match = anchored or re.search(r"<em>([^<]+)</em>", description)
    if not match:
        return None
    return match.group(1).strip().lower() or None


def _gloss_from_description(description: str) -> str | None:
    """Pull the feed's plain-English definition of the word out of an item.

    The description holds a short gloss written by the dictionary's editors,
    followed by an "Examples:" block and an etymology essay. Only the gloss
    describes the sense that is the word of the day.

    Args:
        description (str): Inner HTML of the feed item's description.

    Returns:
        str | None: Gloss text, or None if the description is empty.
    """
    if not description:
        return None
    gloss = re.split(r"<strong>\s*Examples:", description, maxsplit=1)[0]
    # Drop the "Word of the Day for <date> is:" preamble and all markup
    gloss = re.sub(r"^.*?is:\s*</font>", "", gloss, flags=re.DOTALL)
    gloss = unescape(re.sub(r"<[^>]+>", " ", gloss))
    return re.sub(r"\s+", " ", gloss).strip() or None


def get_word_of_the_day() -> WordOfTheDay:
    """Read today's word from Merriam-Webster's word of the day RSS feed.

    The most recent item in the feed is today's word.

    Returns:
        WordOfTheDay: Word of the day and its part of speech.
    """
    page = get_webcontent(WORD_OF_THE_DAY_FEED_URL)
    try:
        feed = ElementTree.fromstring(page.content)
    except ElementTree.ParseError as err:
        raise WordDataError(f"Word of the day feed is not valid XML: {err}") from err

    item = feed.find("./channel/item")
    title = item.findtext("title") if item is not None else None
    if not title or not title.strip():
        raise WordDataError("The word of the day could not be located in the feed")
    # Case is preserved so proper nouns such as "Gordian knot" post correctly
    word = title.strip()
    description = item.findtext("description") or ""
    return WordOfTheDay(
        word,
        _part_of_speech_from_description(description, word),
        _gloss_from_description(description),
    )


def _fold_accents(text: str) -> str:
    """Strip accents from text.

    Args:
        text (str): Text to fold.

    Returns:
        str: Text with combining marks removed.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _lookup(word: str, api_key: str) -> Any:
    """Request one word from the Merriam-Webster API.

    Args:
        word (str): Word to look up.
        api_key (str): Secret Merriam-Webster API key.

    Returns:
        Any: Parsed API response.
    """
    # Multi-word entries such as "Gordian knot" contain spaces
    page = get_webcontent(f"{MERRIAM_WEBSTER_API_URL}{quote(word)}?key={api_key}")
    try:
        return page.json()
    except ValueError as err:
        raise WordDataError("Merriam-Webster API returned a non-JSON response") from err


def get_word_details(word: str, api_key: str) -> dict[str, Any]:
    """Get the response from the Merriam-Webster API for a given word.

    Args:
        word (str): Word of the day retrieved from the website.
        api_key (str): Secret Merriam-Webster API key.

    Returns:
        dict[str, Any]: API response.
    """
    if not api_key:
        raise WordDataError("Missing Merriam-Webster API key")
    response = _lookup(word, api_key)

    # An accented headword such as "élan" only returns spelling suggestions;
    # the entry itself is filed under the unaccented spelling
    folded = _fold_accents(word)
    if folded != word and not any(isinstance(entry, dict) for entry in response):
        return _lookup(folded, api_key)
    return response


def _link_text(match: re.Match[str]) -> str:
    """Return the display text of a link token, without its sense number.

    Cross references address a specific sense, as in ``{sx|burden:1||}``, but
    the sense number is an internal address and should not reach the post.

    Args:
        match (re.Match[str]): Match whose first group is the display text.

    Returns:
        str: Display text for the link.
    """
    return re.sub(r":\d+$", "", match.group(1))


def _strip_markup(text: str) -> str:
    """Render Merriam-Webster's inline formatting tokens as plain text.

    Args:
        text (str): Raw text from the API response.

    Returns:
        str: Text with formatting tokens rendered or removed.
    """
    # {bc} is a definitional break that the dictionary renders as a colon.
    # Dropping it runs consecutive senses together into one phrase.
    text = re.sub(r"{bc}", ": ", text)
    # For link tokens like {sx|word||}, keep only the display text
    text = re.sub(r"{[a-z_]+\|([^|}]+)(?:\|[^|}]*)*}", _link_text, text)
    # Drop any remaining formatting tokens such as {it} or {/it}
    text = re.sub(r"{[^}]*}", "", text)
    # A definition opens with {bc}, so the leading break is not a separator
    text = re.sub(r"\s+", " ", text).strip()
    return text.lstrip(":").strip()


def _clean_pronunciation(pronunciation: str, word: str) -> str:
    """Tidy a pronunciation for display.

    Multi-word entries only carry a pronunciation for the first word, which the
    dictionary marks with a trailing hyphen ("ˈgȯr-dē-ən-" for "Gordian knot").

    Args:
        pronunciation (str): Pronunciation from the API response.
        word (str): Word of the day.

    Returns:
        str: Pronunciation without a dangling hyphen.
    """
    if word.endswith("-"):
        # The word itself is a prefix or combining form, so the hyphen belongs
        return pronunciation
    return pronunciation.rstrip("-")


def _headword_matches(entry: dict[str, Any], word: str) -> bool:
    """Check whether an entry defines the given word.

    Entry ids carry a homograph number ("dudgeon:1") and a suffix for phrases
    ("crux criticorum:f"), neither of which is part of the headword.

    Args:
        entry (dict[str, Any]): A single entry from the API response.
        word (str): Word of the day.

    Returns:
        bool: True if the entry's headword is the word.
    """
    entry_id = entry.get("meta", {}).get("id", "")
    # Folded so the unaccented entry for a word like "élan" still matches
    return (
        _fold_accents(entry_id.split(":")[0]).casefold()
        == _fold_accents(word).casefold()
    )


def _content_words(text: str) -> set[str]:
    """Reduce text to the words worth comparing between two definitions.

    Args:
        text (str): Text to reduce.

    Returns:
        set[str]: Lowercase words of four characters or more.
    """
    return {word for word in re.findall(r"[a-z]+", text.casefold()) if len(word) >= 4}


def _nested_text(value: Any) -> str:
    """Collect every string inside a nested API structure.

    Sense sequences nest lists and dicts several levels deep and the useful
    text sits at the leaves, so the whole subtree is flattened rather than
    walked by key.

    Args:
        value (Any): A fragment of the API response.

    Returns:
        str: Every string in the fragment, space separated.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_nested_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_nested_text(item) for item in value)
    return ""


def _gloss_overlap(entry: dict[str, Any], gloss_words: set[str]) -> int:
    """Score how well an entry's definitions match the feed's gloss.

    Homographs share a part of speech often enough that it cannot separate
    them ("dudgeon" is a noun either way), but the wording of the feed's gloss
    follows the sense that is the word of the day.

    Args:
        entry (dict[str, Any]): A single entry from the API response.
        gloss_words (set[str]): Content words from the feed's gloss.

    Returns:
        int: Number of content words the entry shares with the gloss.
    """
    definitions = _strip_markup(_nested_text(entry.get("def", [])))
    return len(_content_words(definitions) & gloss_words)


def _select_entry(
    api_response: list[Any],
    word: str,
    part_of_speech: str | None = None,
    gloss: str | None = None,
) -> dict[str, Any]:
    """Pick the entry that the word of the day refers to.

    The response also holds homographs, inflections, and phrases that merely
    contain the word, so the first entry is not reliably the right one.

    Args:
        api_response (list[Any]): API response.
        word (str): Word of the day.
        part_of_speech (str | None): Part of speech listed by the feed.
        gloss (str | None): Plain-English definition from the feed.

    Returns:
        dict[str, Any]: The entry to build the post from.
    """
    # Entries without a "def" are variants such as "cruces" that only point at
    # another entry, and cannot produce a definition
    defined = [
        entry
        for entry in api_response
        if isinstance(entry, dict) and entry.get("def") and entry.get("fl")
    ]
    if not defined:
        # A miss returns a list of suggested spellings rather than entry objects
        raise WordDataError("Merriam-Webster API returned no entry for the word")

    candidates = [
        entry for entry in defined if _headword_matches(entry, word)
    ] or defined
    if part_of_speech:
        matching_pos = [
            entry for entry in candidates if entry["fl"].casefold() == part_of_speech
        ]
        candidates = matching_pos or candidates
    if len(candidates) > 1 and gloss:
        gloss_words = _content_words(gloss) - _content_words(word)
        # max() keeps the earliest entry when nothing matches the gloss, which
        # falls back to the dictionary's own ordering
        return max(candidates, key=lambda entry: _gloss_overlap(entry, gloss_words))
    return candidates[0]


def parse_word_details(
    api_response: list[Any],
    word: str,
    part_of_speech: str | None = None,
    gloss: str | None = None,
) -> dict[str, str]:
    """Parse the API response for the details used in the post.

    Args:
        api_response (list[Any]): API response.
        word (str): Word of the day, used to find the matching entry.
        part_of_speech (str | None): Part of speech listed by the feed.
        gloss (str | None): Plain-English definition from the feed.

    Returns:
        dict[str, str]: Word information to post.
    """
    entry = _select_entry(api_response, word, part_of_speech, gloss)
    post_content = {}

    try:
        post_content["pos"] = entry["fl"]

        # Only extract a pronunciation that has an associated sound file
        pronunciations = entry["hwi"].get("prs", [])
        sound_pronunciation = [x["mw"] for x in pronunciations if "sound" in x]
        if sound_pronunciation:
            post_content["pronunciation"] = _clean_pronunciation(
                sound_pronunciation[0], word
            )

        sense_sequence = entry["def"][0]["sseq"][0]
        sense = next(sseq for sseq in sense_sequence if sseq[0] == "sense")
        post_content["definition"] = _strip_markup(sense[1]["dt"][0][1])
    except (KeyError, IndexError, StopIteration) as err:
        raise WordDataError(f"Unexpected API response shape: {err}") from err

    return post_content
