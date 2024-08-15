import configparser
import json
import logging
import os
import sys
import time
from datetime import datetime

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
        log_message = config.get("moderation", "log_message", fallback="")
        if action_type == "delete":
            self.action = lambda post: self.moderator.do(
                post.board, delete(post.post_id, log_message=log_message)
            )
        else:
            ban_reason = config.get("moderation", "ban_reason", fallback="")
            ban_duration = config.get("moderation", "ban_duration", fallback="1y")
            self.action = lambda post: self.moderator.do(
                post.board,
                delete_and_ban(
                    post.post_id,
                    log_message=log_message,
                    ban_reason=ban_reason,
                    ban_duration=ban_duration,
                ),
            )

        self.eval = PostEval(config)
        logger.info("Initialized")

    def on_new_post(self, data: list) -> None:
        post = Post.from_raw(data[0])
        if self.eval.is_spam(post):
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
