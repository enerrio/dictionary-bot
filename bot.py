import requests
import random
import json
import re
import os
from rich import print as rprint
from typing import Any
from bs4 import BeautifulSoup
from utils import get_webcontent
from dotenv import load_dotenv
from bsky import BskyClient

WORD_OF_THE_DAY_URL = "https://www.merriam-webster.com/word-of-the-day"
MERRIAM_WEBSTER_API_URL = "https://dictionaryapi.com/api/v3/references/collegiate/json/"


def get_webster_page() -> requests.models.Response:
    """Get the word of the day webpage contents

    Returns:
        requests.models.Response: Webpage for word of the day
    """
    page = get_webcontent(WORD_OF_THE_DAY_URL)
    return page


def parse_webster_page(page: requests.models.Response) -> str:
    """Parse webpage using bs4 to get word of the day

    Args:
        page (requests.models.Response): Word of the day webpage

    Returns:
        str: Word of the day
    """
    soup = BeautifulSoup(page.content, "html.parser")
    header_text = soup.find(class_="word-header-txt")
    if header_text:
        word_of_the_day = header_text.get_text().lower()
    else:
        raise AttributeError("Error: The word of the day could not be located!")
    return word_of_the_day


def get_webster_api(word: str, api_key: str) -> dict[str, Any]:
    """Get the response from Webster API for a given word

    Args:
        word (str): Word of the day retrieved from website
        api_key (str): Secret Merriam Webster API key

    Returns:
        dict[str, str]: API response
    """
    webster_api_url = f"{MERRIAM_WEBSTER_API_URL}{word}?key={api_key}"
    page = get_webcontent(webster_api_url)
    return page.json()


def parse_webster_api(api_reponse: dict[str, Any]) -> dict[str, str]:
    """Parse API response for relevant word details to post

    Args:
        api_reponse (dict[str, str]): API response

    Returns:
        dict[str, str]: Word information to post
    """
    webster_api_content = api_reponse[0]
    post_content = {}

    # Get part of speech
    pos = webster_api_content["fl"]
    post_content["pos"] = pos

    # Get pronunciation if present
    pronunciations = webster_api_content["hwi"].get("prs")
    if pronunciations:
        # only extract sound pronunciation
        sound_pronunciation = [x["mw"] for x in pronunciations if "sound" in x]
        if sound_pronunciation:
            post_content["pronunciations"] = sound_pronunciation[0]

    # Get definition of word
    # definitions = webster_api_content["shortdef"]
    # definition_text = "\n".join([f"{i+1}) {x}" for i, x in enumerate(definitions)])
    definition_text_dt = webster_api_content["def"][0]["sseq"][0]
    definition_text_dt = [sseq for sseq in definition_text_dt if sseq[0] == "sense"][0]
    definition_text = definition_text_dt[1]["dt"][0][1]
    # for links, extract 2nd field
    definition_text = re.sub(
        r"{[a-z_]+\|([^\|}]+)(?:\|[^\|}]*)*}", r"\1", definition_text
    )
    definition_text = re.sub(r"{[^\}]*}", "", definition_text)
    post_content["definitions"] = definition_text

    # Choose random quote
    quotes = webster_api_content.get("quotes")
    if quotes:
        post_content["quote"] = re.sub(
            r"{[a-z\_\\/|]*}", "", random.choice(quotes)["t"]
        )
    return post_content


def create_post_text(post_content: dict[str, str]) -> str:
    """Create the text of the post

    Args:
        post_content (dict[str, str]): Contains word information parsed from API response

    Returns:
        str: Post text
    """
    text = (
        f"🌟 Word of the day: {post_content['word']}\n"
        f"📚 Part of Speech: {post_content['pos']}\n"
        f"🔊 Pronunciation: {post_content.get('pronunciations', '')}\n"
        f"📖 Definition: {post_content['definitions']}"
    )
    return text


def main():
    # Get secrets
    load_dotenv(override=True)
    api_key = os.getenv("API_KEY")
    bluesky_username = os.getenv("BLUESKY_USERNAME")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    debug = os.getenv("DEBUG").lower() == "true"

    # Get word of the day from merriam webster
    if debug:
        word_of_the_day = "rapport"
        print(f"Word of the day: {word_of_the_day}")
        with open(f"data/sample_api_response_{word_of_the_day}.json", "r") as f:
            api_response = json.load(f)
    else:
        web_page = get_webster_page()
        word_of_the_day = parse_webster_page(web_page)
        print(f"Word of the day: {word_of_the_day}")
        api_response = get_webster_api(word_of_the_day, api_key)

    # Parse the API response and get relevant info
    word_content = parse_webster_api(api_response)
    word_content.update({"word": word_of_the_day})
    post_text = create_post_text(word_content)
    rprint(api_response)
    rprint(word_content)
    rprint(post_text)

    # Post to Bluesky
    if not debug:
        print("Creating Bluesky session...")
        client = BskyClient()
        print("Logging in...")
        session = client.login(bluesky_username, bluesky_password)
        print("Posting text...")
        post = client.post(post_text)
        rprint(session)
        rprint(post)


def lambda_handler(event, context) -> dict[str, Any]:
    """Main entry point for AWS Lambda function

    Args:
        event: Contains info about service invoking function
        context: Contains methods + properties about invocation/runtime/function

    Returns:
        dict[str, Any]: Dictionary containing lambda invocation response info
    """
    main()
    return {"statusCode": 200, "body": json.dumps("Done!")}


if __name__ == "__main__":
    main()
