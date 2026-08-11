import logging
from datetime import date
from pathlib import Path

from whenever import Instant

from config.settings import POST_TIMEZONE, STATE_FILE

logger = logging.getLogger(__name__)


def today_in_timezone(timezone: str = POST_TIMEZONE) -> date:
    """Return the current calendar date in the given timezone.

    Args:
        timezone (str): IANA timezone name.

    Returns:
        date: Today's date in that timezone.
    """
    return Instant.now().to_tz(timezone).py_datetime().date()


def already_posted_today(state_file: Path = STATE_FILE) -> bool:
    """Check whether a post has already been made for today.

    launchd replays a missed calendar job when the machine wakes, so this guards
    against posting the same word twice in one day.

    Args:
        state_file (Path): File holding the ISO date of the last successful post.

    Returns:
        bool: True if a post was already recorded for today.
    """
    try:
        last_posted = state_file.read_text().strip()
    except FileNotFoundError:
        return False
    return last_posted == today_in_timezone().isoformat()


def record_post(state_file: Path = STATE_FILE) -> None:
    """Record today's date as the last successful post.

    Args:
        state_file (Path): File holding the ISO date of the last successful post.
    """
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(f"{today_in_timezone().isoformat()}\n")
