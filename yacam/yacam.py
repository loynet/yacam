import configparser
import logging
import os

from dotenv import load_dotenv

from session import ModSession
from listener import PostsListener

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Yacam:
    def __init__(self) -> None:
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

        # Load config file
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read('config.ini')

        self.session = ModSession(domain, username, password)
        logger.info('Yacam initialized')

    def run(self) -> None:
        logger.info('Yacam is running!')
        listener = PostsListener(self.session, self.config_parser)
        listener.join()


if __name__ == '__main__':
    yacam = Yacam()
    yacam.run()
