import json
import logging
import os
import sys
import time
from datetime import datetime

import yaml
from basedflare_session import BasedSession
from dotenv import load_dotenv

from moderator import Moderator, delete, delete_and_ban
from requests import Session
from eval import create_post_eval, from_config, Post

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
        # Load configuration
        # TODO: Add proper config validation
        with open("./config.yaml", "r") as f:
            config = yaml.safe_load(f)

        # Create a session
        session = BasedSession() if config["general"].get("basedflare_session", False) else Session()
        # TODO: Add proper versioning
        session.headers.update({"User-Agent": config["general"].get("user_agent", "YACAM/1.1")})

        self.moderator = new_moderator(session)

        mod_config = config["moderation"]
        log_message = mod_config.get("log_message", "")
        if mod_config.get("action", "delete") == "delete":
            self.action = lambda post: self.moderator.do(post.board, delete(post.post_id, log_message=log_message))
        else:
            self.action = lambda post: self.moderator.do(
                post.board,
                delete_and_ban(
                    post.post_id,
                    log_message=log_message,
                    ban_reason=mod_config.get("ban_reason", ""),
                    ban_duration=mod_config.get("ban_duration", "1y"),
                ),
            )

        self.is_valid = create_post_eval(*from_config(config["detection"]))
        logger.info("Initialized")

    def on_new_post(self, data: list) -> None:
        post = Post.from_raw(data[0])
        if not self.is_valid(post):
            logger.info("Found spam")
            self.action(post)
            with open(f'{data[0]["_id"]}.json', "w") as f:
                f.write(json.dumps(data[0]))

    def run(self) -> None:
        logger.info("Running")
        print("Press CTRL+C to exit")

        delay, max_delay = 5, 60 * 30  # seconds
        last_exception = datetime.now()
        while True:
            try:
                time.sleep(delay)
                self.moderator.login()  # Login every time to avoid session expiration issues (not ideal)
                self.moderator.listen(self.on_new_post)
            except Exception as e:
                logger.exception(e)
                # Regenerate the delay if the last exception was more than max_delay and a threshold of 5 minutes has passed
                curr_time = datetime.now()
                if (curr_time - last_exception).total_seconds() > max_delay + (60 * 5):
                    delay = 5
                last_exception = curr_time
                delay = min(delay * 2, max_delay)
                logger.error(f"Error {e}, trying again in {delay} seconds")


if __name__ == "__main__":
    try:
        yacam = Yacam()
        yacam.run()
    except KeyboardInterrupt:
        sys.exit()
