import configparser
import json
import logging
import os
import sys

from basedflare_session import BasedSession
from dotenv import load_dotenv

from moderator import Moderator, delete, delete_and_ban
from requests import Session
from eval import PostEval
from post import Post

# Configure logger
logging.basicConfig(
    format="%(filename)s %(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def new_moderator(session: Session) -> Moderator:
    load_dotenv(".env")
    domain: str = os.environ.get("IMAGEBOARD_DOMAIN")
    if not domain:
        raise ValueError('"IMAGEBOARD_DOMAIN" environment variable must be set')

    username: str = os.environ.get("MOD_USERNAME")
    if not username:
        raise ValueError('"MOD_USERNAME" environment variable must be set')

    password: str = os.environ.get("MOD_PASSWORD")
    if not password:
        raise ValueError('"MOD_PASSWORD" environment variable must be set')

    return Moderator(session, f"https://{domain}", username, password)


class Yacam:
    def __init__(self) -> None:
        # Load configuration file
        config = configparser.ConfigParser()
        config.read("config.ini")

        session = (
            BasedSession()
            if config.getboolean("yacam", "use_basedflare")
            else Session()
        )
        session.headers.update({"User-Agent": config.get("yacam", "user_agent")})
        self.moderator = new_moderator(session)

        action_type = config.get("moderation", "action")
        if action_type == "delete":
            self.action = lambda post: self.moderator.do(
                post.board, delete(post.post_id)
            )
        else:
            self.action = lambda post: self.moderator.do(
                post.board, delete_and_ban(post.post_id)
            )

        self.eval = PostEval(config)
        logger.info("Initialized")

    def on_new_post(self, event: list) -> None:
        if event[0] != "newPost":
            return
        post = Post.from_raw(event[1])
        if self.eval.is_spam(post):
            logger.info("Found spam")
            self.action(post)
            with open(f'{event[1]["_id"]}.json', "w") as f:
                f.write(json.dumps(event[1]))

    def run(self) -> None:
        logger.info("Running")
        print("Press CTRL+C to exit")
        self.moderator.listen([self.on_new_post])


if __name__ == "__main__":
    try:
        yacam = Yacam()
        yacam.run()
    except KeyboardInterrupt:
        sys.exit()
