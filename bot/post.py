import logging

from bot.client import BlueskyClient
from bot.fetch_data import (
    WordDataError,
    get_word_details,
    get_word_of_the_day,
    parse_word_details,
)
from bot.message import build_word_of_the_day_message
from bot.schedule import already_posted_today, record_post
from config.settings import (
    API_KEY,
    BLUESKY_PASSWORD,
    BLUESKY_USERNAME,
    DEBUG,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def should_execute() -> bool:
    """Check whether the bot still needs to post for today."""
    return not already_posted_today()


def run() -> bool:
    """Main entrypoint for the script. Gathers the word of the day and posts to Bluesky.

    Returns:
        bool: Whether the post was successful or not.
    """
    logger.info("Debug mode is %s", "enabled" if DEBUG else "disabled")
    if not DEBUG and not should_execute():
        logger.info("Already posted today. Exiting without posting.")
        return True

    logger.info("Fetching word of the day")
    try:
        word, part_of_speech, gloss = get_word_of_the_day()
        logger.info("Word of the day: %s (%s)", word, part_of_speech or "unknown")
        api_response = get_word_details(word, API_KEY)
        word_content = parse_word_details(api_response, word, part_of_speech, gloss)
    except WordDataError as err:
        logger.error("Unable to fetch word of the day: %s", err)
        return False

    message = build_word_of_the_day_message(word, word_content)
    logger.info("Message to post:\n%s", message)

    if DEBUG:
        logger.info("Debug mode is enabled. No post will be made.")
        return True

    logger.info("Setting up Bluesky client")
    client = BlueskyClient()
    session = client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
    if not session:
        logger.error("Login failed. Exiting.")
        return False

    response = client.post(message)
    if not response:
        logger.error("Failed to post update.")
        return False
    record_post()
    logger.info("Post successful. Response: %s", response)
    return True
