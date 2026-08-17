import logging
import time
from collections.abc import Callable
from typing import TypeVar

from atproto import Client, Request, models
from atproto.exceptions import AtProtocolError, NetworkError

from config.settings import (
    BLUESKY_MAX_ATTEMPTS,
    BLUESKY_REQUEST_TIMEOUT,
    BLUESKY_RETRY_BACKOFF,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _describe(err: Exception) -> str:
    """Render an exception for logging, including its type.

    Timeouts raised by atproto carry no message at all, so the type name is the
    only clue about what failed.
    """
    return f"{type(err).__name__}: {err}" if str(err) else type(err).__name__


class BlueskyClient:
    """Bluesky client to handle logging in and posting."""

    def __init__(self) -> None:
        self.client = Client(
            base_url="https://bsky.social",
            request=Request(timeout=BLUESKY_REQUEST_TIMEOUT),
        )

    def _call_with_retry(self, action: str, operation: Callable[[], T]) -> T | None:
        """Run a Bluesky call, retrying transient network failures with backoff.

        Args:
            action (str): Name of the call, used in log messages.
            operation (Callable[[], T]): The call to run.

        Returns:
            T: Whatever the call returns.
            None: If every attempt failed.
        """
        for attempt in range(1, BLUESKY_MAX_ATTEMPTS + 1):
            try:
                return operation()
            except NetworkError as err:
                if attempt == BLUESKY_MAX_ATTEMPTS:
                    logger.error(
                        "Bluesky %s error after %d attempts: %s",
                        action,
                        attempt,
                        _describe(err),
                    )
                    return None
                delay = BLUESKY_RETRY_BACKOFF * 2 ** (attempt - 1)
                logger.warning(
                    "Bluesky %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    action,
                    attempt,
                    BLUESKY_MAX_ATTEMPTS,
                    _describe(err),
                    delay,
                )
                time.sleep(delay)
            except AtProtocolError as err:
                # Rejections such as a malformed post will fail the same way
                # every time, so there is nothing to gain from retrying
                logger.error("Bluesky %s error: %s", action, _describe(err))
                return None
        return None

    def login(
        self, username: str, password: str
    ) -> models.AppBskyActorDefs.ProfileViewDetailed:
        """Login to Bluesky using username and password.

        Args:
            username (str): Bluesky username.
            password (str): Bluesky password.

        Returns:
            models.AppBskyActorDefs.ProfileViewDetailed: Bluesky session object.
            None: If login fails.
        """
        return self._call_with_retry(
            "login", lambda: self.client.login(username, password)
        )

    def post(self, text: str) -> models.AppBskyFeedPost.CreateRecordResponse:
        """Post to Bluesky.

        Args:
            text (str): Content of the post.

        Returns:
            models.AppBskyFeedPost.CreateRecordResponse: Post response object.
            None: If the post fails.
        """
        return self._call_with_retry("post", lambda: self.client.send_post(text))
