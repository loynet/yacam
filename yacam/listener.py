import logging
import re
from abc import ABC
from threading import Thread, Event

import socketio
from urlextract import URLExtract

from post import Post
from session import ModSession

# TODO make these configurable
BAD_SYMBOLS = ['*', '&', '%', '$', '#', '@', '!', '?', '(', ')', '[', ']', '{', '}', '<', '>', '/', '\\', '|', '+', '=']
THRESHOLD = 0.25
WHITELISTED_COUNTRIES = []

logger = logging.getLogger(__name__)


class Listener(ABC, Thread):
    def __init__(self, session):
        Thread.__init__(self)
        self.daemon = True
        self._stop = Event()
        self.session = session

    def stop(self):
        logger.debug(f'Killing listener, goodbye')
        self._stop.set()


class PostsListener(Listener):
    def __init__(self, session: ModSession) -> None:
        super(PostsListener, self).__init__(session)

        self.good_countries = WHITELISTED_COUNTRIES
        self.bad_symbols = re.compile("[" + "".join([re.escape(e) for e in BAD_SYMBOLS]) + "]", re.IGNORECASE)

        self.extractor = URLExtract()

        client = socketio.Client(http_session=self.session)

        @client.event
        def connect():
            logger.info(f'Connected to {self.session.domain} websocket')
            # TODO remove the hardcoded room
            client.emit('room', 'cc99-manage-recent-hashed')

        @client.event
        def disconnect():
            logger.info(f'Disconnected from {self.session.domain} websocket')

        @client.on('newPost')
        def on_new_post(data):
            self.handle_new_post(Post.from_raw(data))

        self.client = client
        self.run()

    def handle_bad_post(self, post: Post) -> None:
        logger.info(f'Found bad post: {post.get_url()}, {post.message}, deleting...')
        # Tom updates every action and he knows better
        self.session.update_csrf()
        self.session.delete_post(post.board, post.post_id, reason='bad post')

    def handle_new_post(self, post: Post) -> None:
        logger.debug(f'New post: {post.get_url()}, {post.message}')
        # Whitelist posts without files, posts from authenticated authors and posts from safe countries
        if not post.has_files() or post.has_capcode() or \
                (post.has_geo_flag() and post.author.flag.code in self.good_countries):
            return

        # TODO implement new algorithm for detecting bad posts

        # Check for urls
        msg = post.message
        urls = self.extractor.find_urls(msg, get_indices=True)
        # No urls = no problem
        if len(urls) == 0:
            return

        # Remove detected urls
        for url in urls:
            msg = msg[:url[1][0]] + msg[url[1][1]:]

        # Calculate the obfuscating ratio and compare it to the threshold
        if len(msg) > 0 and len(re.findall(self.bad_symbols, msg)) / len(msg) > THRESHOLD:
            self.handle_bad_post(post)

    def run(self):
        self.client.connect(f'wss://{self.session.domain}/', transports=['websocket'])
        self.client.wait()  # Blocks the thread until the connection is closed

        if self._stop.wait():
            logger.info("Exiting recent watcher")
            self.client.disconnect()
