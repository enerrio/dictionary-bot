import logging

from atproto import Client, models
from atproto.exceptions import AtProtocolError

logger = logging.getLogger(__name__)


class BlueskyClient:
    """Bluesky client to handle logging in and posting."""

    def __init__(self) -> None:
        self.client = Client(base_url="https://bsky.social")

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
        try:
            session = self.client.login(username, password)
            return session
        except AtProtocolError as err:
            logger.error("Bluesky login error: %s", err)
            return None

    def post(self, text: str) -> models.AppBskyFeedPost.CreateRecordResponse:
        """Post to Bluesky.

        Args:
            text (str): Content of the post.

        Returns:
            models.AppBskyFeedPost.CreateRecordResponse: Post response object.
            None: If the post fails.
        """
        try:
            post = self.client.send_post(text)
            return post
        except AtProtocolError as err:
            logger.error("Bluesky post error: %s", err)
            return None
