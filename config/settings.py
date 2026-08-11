import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(REPO_ROOT / ".env")

API_KEY = os.getenv("API_KEY")
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# The word-of-the-day HTML page blocks non-browser clients with a 403, so the
# bot reads the word from Merriam-Webster's RSS feed instead
WORD_OF_THE_DAY_FEED_URL = "https://www.merriam-webster.com/wotd/feed/rss2"
MERRIAM_WEBSTER_API_URL = "https://dictionaryapi.com/api/v3/references/collegiate/json/"

# Timezone used to decide which calendar day a run belongs to
POST_TIMEZONE = "America/Los_Angeles"

# Records the last day the bot posted so a replayed launchd job cannot double post
STATE_FILE = REPO_ROOT / "state" / "last_posted_date"
