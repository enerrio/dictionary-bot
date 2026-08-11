import random
import re
from typing import Any
from xml.etree import ElementTree

import requests

from config.settings import MERRIAM_WEBSTER_API_URL, WORD_OF_THE_DAY_FEED_URL


class WordDataError(RuntimeError):
    """Raised when the word of the day cannot be retrieved or parsed."""


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


def get_word_of_the_day() -> str:
    """Read today's word from Merriam-Webster's word of the day RSS feed.

    The most recent item in the feed is today's word.

    Returns:
        str: Word of the day.
    """
    page = get_webcontent(WORD_OF_THE_DAY_FEED_URL)
    try:
        feed = ElementTree.fromstring(page.content)
    except ElementTree.ParseError as err:
        raise WordDataError(f"Word of the day feed is not valid XML: {err}") from err

    title = feed.findtext("./channel/item/title")
    if not title or not title.strip():
        raise WordDataError("The word of the day could not be located in the feed")
    return title.strip().lower()


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
    page = get_webcontent(f"{MERRIAM_WEBSTER_API_URL}{word}?key={api_key}")
    try:
        return page.json()
    except ValueError as err:
        raise WordDataError("Merriam-Webster API returned a non-JSON response") from err


def _strip_markup(text: str) -> str:
    """Remove Merriam-Webster's inline formatting tokens from text.

    Args:
        text (str): Raw text from the API response.

    Returns:
        str: Text with formatting tokens removed.
    """
    # For link tokens like {sx|word||}, keep only the display text
    text = re.sub(r"{[a-z_]+\|([^|}]+)(?:\|[^|}]*)*}", r"\1", text)
    # Drop any remaining formatting tokens such as {bc} or {it}
    return re.sub(r"{[^}]*}", "", text).strip()


def parse_word_details(api_response: list[Any]) -> dict[str, str]:
    """Parse the API response for the details used in the post.

    Args:
        api_response (list[Any]): API response.

    Returns:
        dict[str, str]: Word information to post.
    """
    if not api_response or not isinstance(api_response[0], dict):
        # A miss returns a list of suggested spellings rather than entry objects
        raise WordDataError("Merriam-Webster API returned no entry for the word")

    entry = api_response[0]
    post_content = {}

    try:
        post_content["pos"] = entry["fl"]

        # Only extract a pronunciation that has an associated sound file
        pronunciations = entry["hwi"].get("prs", [])
        sound_pronunciation = [x["mw"] for x in pronunciations if "sound" in x]
        if sound_pronunciation:
            post_content["pronunciation"] = sound_pronunciation[0]

        sense_sequence = entry["def"][0]["sseq"][0]
        sense = next(sseq for sseq in sense_sequence if sseq[0] == "sense")
        post_content["definition"] = _strip_markup(sense[1]["dt"][0][1])
    except (KeyError, IndexError, StopIteration) as err:
        raise WordDataError(f"Unexpected API response shape: {err}") from err

    quotes = entry.get("quotes")
    if quotes:
        post_content["quote"] = _strip_markup(random.choice(quotes)["t"])
    return post_content
