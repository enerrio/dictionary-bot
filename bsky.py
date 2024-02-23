from atproto import Client
from atproto.exceptions import AtProtocolError
from atproto import models


class BskyClient:
    def __init__(self) -> None:
        self.client = Client(base_url="https://bsky.social")

    def login(
        self, username: str, password: str
    ) -> models.AppBskyActorDefs.ProfileViewDetailed:
        try:
            session = self.client.login(username, password)
        except AtProtocolError as err:
            print(f"Bluesky login error: {err}")
        return session

    def post(self, text: str) -> models.AppBskyFeedPost.CreateRecordResponse:
        try:
            post = self.client.send_post(text)
        except AtProtocolError as err:
            print(f"Bluesky post error: {err}")
        return post
