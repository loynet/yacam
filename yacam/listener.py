import configparser
import logging
import re
from abc import ABC
from threading import Thread, Event

import socketio
from urlextract import URLExtract

from post import Post
from session import ModSession

logger = logging.getLogger(__name__)


class StoppableThread(ABC, Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self._stop = Event()

    def stop(self):
        logger.debug(f'Killing thread, goodbye')
        self._stop.set()


class PostsListener(StoppableThread):
    def __init__(self, session: ModSession, config_parser: configparser.ConfigParser) -> None:
        super(PostsListener, self).__init__()

        tokens = "[" + "".join([re.escape(e) for e in config_parser['detection']['tokens'].split()]) + "]"
        mode = config_parser['detection']['mode']
        if mode == 'threshold':
            # Compiles the regex for the obfuscated tokens
            self.tokens_pattern = re.compile(tokens, re.IGNORECASE)
            # Sets the max threshold
            self.max_threshold = config_parser['detection'].getfloat('max_threshold')
            # Sets the eval function to the eval_threshold function
            self.eval = self.eval_threshold

        elif mode == 'entries':
            # Compiles the regex for the entry and group of entries
            e = r'\w' + tokens
            self.entry_pattern = re.compile(e, re.IGNORECASE)
            self.entries_pattern = re.compile(f'(?:{e})+', re.IGNORECASE)

            # Sets the max number of consecutive entries
            self.max_entries = config_parser['detection'].getint('max_consecutive_entries')

            # Sets the eval function to the eval_entries function
            self.eval = self.eval_entries

        self.countries_whitelist = config_parser.get('moderation', 'countries_whitelist', fallback='').split()

        self.session = session

        # TODO: add find a better way to handle this
        self.log_message = config_parser.get('moderation', 'log_message', fallback='')
        self.ban_author = config_parser['moderation']['action'] == "ban"
        if self.ban_author:
            self.ban_duration = config_parser.get('moderation', 'ban_duration', fallback='1y')
            self.ban_reason = config_parser.get('moderation', 'ban_reason', fallback='')

        self.extractor = URLExtract()
        client = socketio.Client(http_session=self.session)

        @client.event
        def connect():
            logger.info(f'Connected to {self.session.domain} websocket')
            client.emit('room', 'globalmanage-recent-hashed')

        @client.event
        def disconnect():
            logger.info(f'Disconnected from {self.session.domain} websocket')

        @client.on('newPost')
        def on_new_post(data):
            self.handle_new_post(Post.from_raw(data))

        self.client = client
        self.run()

    def eval_threshold(self, message: str) -> bool:
        return len(message) > 0 and len(re.findall(self.tokens_pattern, message)) / len(
            message) > self.max_threshold

    def eval_entries(self, message: str) -> bool:
        for found in re.finditer(self.entries_pattern, message):
            if len(re.findall(self.entry_pattern, found.string[found.start():found.end()])) > self.max_entries:
                return True
        return False

    def handle_bad_post(self, post: Post) -> None:

        logger.info(
            f'Found bad post:\n{post.get_url()}\n{" ,".join(file.content_hash for file in post.files)}\n{post.message}')

        # TODO find better way of handling this, looks bad af
        if self.ban_author:
            self.session.delete_ban(post.board, post.post_id, ban_reason=self.ban_reason,
                                    ban_duration=self.ban_duration, log_message=self.log_message)
        else:
            self.session.delete_post(post.board, post.post_id, log_message=self.log_message)

    def handle_new_post(self, post: Post) -> None:
        logger.debug(f'New post: {post.get_url()}, {post.message}')
        # Whitelist posts without files, posts from authenticated authors and posts from safe countries
        if not post.has_files() or post.has_capcode() or \
                (post.has_geo_flag() and post.author.flag.code in self.countries_whitelist):
            return

        msg = post.message
        # No message = no problem
        if msg is None:
            return

        # Check for urls
        urls = self.extractor.find_urls(msg, get_indices=True)
        # No urls = no problem
        if len(urls) == 0:
            return

        # Remove detected urls
        for url in urls:
            msg = msg[:url[1][0]] + msg[url[1][1]:]

        # Calculate the obfuscating ratio and compare it to the threshold
        if self.eval(msg):
            self.handle_bad_post(post)

    def run(self):
        self.client.connect(f'wss://{self.session.domain}/', transports=['websocket'])
        self.client.wait()  # Blocks the thread until the connection is closed

        if self._stop.wait():
            logger.info("Exiting recent watcher")
            self.client.disconnect()
