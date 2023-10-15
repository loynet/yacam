import configparser
import json
import logging
import os
import sys

from dotenv import load_dotenv

from session import ModSession
from listener import PostListener
from eval import PostEval
from post import Post

# Logger configuration
logging.basicConfig(
    format='%(filename)s %(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def new_session() -> ModSession:
    # Load environment variables
    load_dotenv('.env')
    domain: str = os.environ.get('IMAGEBOARD_DOMAIN')
    if not domain:
        raise ValueError('"IMAGEBOARD_DOMAIN" environment variable must be set')

    username: str = os.environ.get('MOD_USERNAME')
    if not username:
        raise ValueError('"MOD_USERNAME" environment variable must be set')

    password: str = os.environ.get('MOD_PASSWORD')
    if not password:
        raise ValueError('"MOD_PASSWORD" environment variable must be set')

    return ModSession(domain, username, password)


class Yacam:
    def __init__(self) -> None:
        self.session = new_session()

        # Load config file
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # Sets what action is taken when spam is found
        if self.config['moderation']['action'] == 'delete':
            self.action: callable(Post) = lambda post: self.session.delete_post(
                post.board,
                post.post_id,
                log_message=self.config.get('moderation', 'log_message', fallback='')
            )
        elif self.config['moderation']['action'] == 'ban':
            self.action: callable(Post) = lambda post: self.session.delete_ban(
                post.board,
                post.post_id,
                ban_reason=self.config.get('moderation', 'ban_reason', fallback=''),
                ban_duration=self.config.get('moderation', 'ban_duration', fallback='1y'),
                log_message=self.config.get('moderation', 'log_message', fallback='')
            )
        else:
            raise ValueError('moderation action must be "ban" or "delete"')

        self.eval = PostEval(self.config)
        self.listener = PostListener(self.session, [self.on_new_post])
        logger.info('Initialized')

    def on_new_post(self, data: dict) -> None:
        p = Post.from_raw(data)
        if self.eval.is_spam(p):
            logger.info('Found spam')
            self.action(p)
            with open(f'{data["_id"]}.json', 'w') as f:
                f.write(json.dumps(data))

    def run(self) -> None:
        logger.info('Running')
        print('Press CTRL+C to exit')
        self.listener.run()


if __name__ == '__main__':
    try:
        yacam = Yacam()
        yacam.run()
    except KeyboardInterrupt:
        sys.exit()
