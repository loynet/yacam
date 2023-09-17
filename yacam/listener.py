import configparser
import json
import logging
import re
from abc import ABC
from threading import Thread, Event

import socketio
from urlextract import URLExtract

from post import Post
from session import ModSession

logger = logging.getLogger(__name__)


# TODO this stopple thread thing is even doing something? Check it later
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

        # Read the detection configs
        tokens = "[" + "".join([re.escape(e) for e in config_parser['detection']['tokens'].split()]) + "]"
        mode = config_parser['detection']['mode']

        if mode == 'threshold':
            self.tokens_pattern = re.compile(tokens, re.IGNORECASE)
            self.max_threshold = config_parser['detection'].getfloat('max_threshold')
            self.eval_post = self.eval_threshold

        elif mode == 'entries':
            # Compiles the regex for the entry and group of entries
            e = r'[^\W_]' + tokens
            self.entry_pattern = re.compile(e, re.IGNORECASE)
            self.entries_pattern = re.compile(f'(?:{e})+', re.IGNORECASE)

            self.max_entries = config_parser['detection'].getint('max_consecutive_entries')
            self.eval_post = self.eval_entries

        # Read the whitelist configs
        self.countries_whitelist = config_parser.get('detection', 'countries_whitelist', fallback='').split()

        # Read the moderation action configs
        log_message = config_parser.get('moderation', 'log_message', fallback='')
        self.ban_author = config_parser['moderation']['action'] == "ban"
        if not self.ban_author:
            self.mod_action = lambda post: self.session.delete_post(post.board, post.post_id, log_message=log_message)
        else:
            duration = config_parser.get('moderation', 'ban_duration', fallback='1y')
            reason = config_parser.get('moderation', 'ban_reason', fallback='')
            self.mod_action = lambda post: self.session.delete_ban(post.board, post.post_id, ban_reason=reason,
                                                                   ban_duration=duration, log_message=log_message)

        self.session = session
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
            if self.handle_new_post(Post.from_raw(data)):
                # TODO: this is a very "hackish" way to do this, but it works for now, fix it later
                # Redact urls from the message
                urls = self.extractor.find_urls(data['nomarkup'])
                for url in urls:
                    u = url.split('/')
                    # If the url has no path, we must delete the whole domain (in every entry)
                    safe_url = f'{u[0]}/REDACTED' if len(u) > 1 else f'REDACTED.TLD'
                    data['nomarkup'] = data['nomarkup'].replace(url, safe_url)
                    data['message'] = data['message'].replace(url, safe_url)

                # Dump the data to a json file
                with open(f'{data["_id"]}.json', 'w') as f:
                    f.write(json.dumps(data))

        self.client = client
        self.run()

    def eval_threshold(self, message: str) -> bool:
        return len(message) > 0 and len(re.findall(self.tokens_pattern, message)) / len(message) > self.max_threshold

    def eval_entries(self, message: str) -> bool:
        for found in re.finditer(self.entries_pattern, message):
            if len(re.findall(self.entry_pattern, found.string[found.start():found.end()])) > self.max_entries:
                return True
        return False

    def handle_bad_post(self, post: Post) -> None:
        logger.info(
            f'Found bad post:\n{post.get_url()}\n{" ,".join(file.content_hash for file in post.files)}\n{post.message}')
        self.mod_action(post)

    def handle_new_post(self, post: Post) -> bool:
        logger.debug(f'New post: {post.get_url()}, {post.message}')
        # Whitelist posts without files, posts from authenticated authors and posts from safe countries
        if not post.has_files() or post.has_capcode() or \
                (post.has_geo_flag() and post.author.flag.code in self.countries_whitelist):
            return False

        msg = post.message
        # No message = no problem
        if msg is None:
            return False

        # Check for urls
        urls = self.extractor.find_urls(msg, get_indices=True)
        # No urls = no problem
        if len(urls) == 0:
            return False

        # Remove detected urls
        for url in urls:
            msg = msg[:url[1][0]] + msg[url[1][1]:]

        # Calculate the obfuscating ratio and compare it to the threshold
        if self.eval_post(msg):
            self.handle_bad_post(post)
            return True

    def run(self):
        self.client.connect(f'wss://{self.session.domain}/', transports=['websocket'])
        self.client.wait()  # Blocks the thread until the connection is closed

        if self._stop.wait():
            logger.info("Exiting recent watcher")
            self.client.disconnect()
