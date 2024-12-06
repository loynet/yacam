from abc import ABC, abstractmethod
import re

import utils as utils
from defaults import DEFAULT_TOKENS
from post import Post
from urllib.parse import urlparse


class Proposition(ABC):
    """
    A proposition that can be evaluated on a post.
    Each proposition should implement the valid method, which returns a boolean. This method should be used to check if
    the proposition is valid for a given post.
    """

    @abstractmethod
    def valid(self, p: "Post") -> bool:
        pass


class Negate(Proposition):
    """
    Negates a proposition.
    This is useful because it allows propositions to be simpler and more reusable,
    but should be used with caution as it can be confusing.
    """

    def __init__(self, proposition: Proposition):
        self.proposition = proposition

    def valid(self, p: "Post") -> bool:
        return not self.proposition.valid(p)


class MessageHasLessThanThreshold(Proposition):
    """
    Checks if the ratio of tokens and characters in the post message is below a certain threshold.
    Whitespaces and urls are removed before the check.
    """

    def __init__(
        self,
        tokens: list[str] = None,
        max_threshold: float = 0.3,
    ):
        self.pattern = re.compile(f'[{"".join(re.escape(t) for t in (tokens or DEFAULT_TOKENS))}]', re.IGNORECASE)
        self.max_threshold = max_threshold
        self.url_finder = utils.URLFinder()

    def valid(self, p: "Post") -> bool:
        if not p.message:
            return True

        # Removes URLs, whitespaces and special characters
        msg = "".join(self.url_finder.remove(p.message).split())
        return len(msg) != 0 and (len(re.findall(self.pattern, msg)) / len(msg)) < self.max_threshold


class MessageHasLessThanConsecutiveEntries(Proposition):
    """
    Checks if the amount of consecutive entries in the post message is below a certain count.
    An entry is defined as a word character (as defined by Python regular expressions) followed by a token (e.g., a*).
    """

    def __init__(
        self,
        tokens: list[str] = None,
        max_count: int = 3,
    ):
        # Compiles the regex for the entry and group of entries
        e = r"[^\W_]" + f'[{"".join(re.escape(t) for t in (tokens or DEFAULT_TOKENS))}]'
        self.entry_pattern = re.compile(e, re.IGNORECASE)
        self.pattern = re.compile(f"(?:{e})+", re.IGNORECASE)

        self.max_count = max_count

    def valid(self, p: "Post") -> bool:
        if not p.message or len(p.message) == 0:
            return True

        for found in re.finditer(self.pattern, p.message):
            found_entries = re.findall(
                self.entry_pattern,
                found.string[found.start() : found.end()],
            )
            if len(found_entries) > self.max_count:
                return False

        return True


class MessageHasNOrMoreURLs(Proposition):
    """
    Checks if the amount of URLs in the post message is below a certain count.
    """

    def __init__(self, n: int = 1):
        self.url_finder = utils.URLFinder()
        self.n = n

    def valid(self, p: "Post") -> bool:
        if not p.message or len(p.message) == 0:
            return True
        return len(self.url_finder.find(p.message)) >= self.n


class AllUrlsAreShorteners(Proposition):
    """
    Checks if the amount of URLs in the post message is below a certain count.
    """

    def __init__(self, max_length: int = 8):
        self.url_finder = utils.URLFinder()
        self.max_length = max_length

    def valid(self, p: "Post") -> bool:
        if not p.message or len(p.message) == 0:
            return False

        urls = self.url_finder.find(p.message)
        if len(urls) == 0:
            return False

        for url in self.url_finder.find(p.message):
            path = utils.parse_path(url)
            # The idea is that shorteners have a path with a single element that is short,
            # this is not a perfect heuristic but will do
            if len(path) > 1 or len(path[0]) > self.max_length:
                return False

        return True


class AuthorHasWhitelistedGeoFlag(Proposition):
    """
    Checks if the author of the post has a geo flag that is not in the whitelist.
    """

    def __init__(self, whitelist: list[str]):
        self.whitelist = whitelist

    def valid(self, p: "Post") -> bool:
        return p.has_geo_flag() and p.author.flag.code in self.whitelist


class AuthorHasCapcode(Proposition):
    """
    Checks if the author of the post has a capcode.
    """

    def valid(self, p: "Post") -> bool:
        return p.has_capcode()


class PostHasFiles(Proposition):
    """
    Checks if the post has N or more files.
    """

    def valid(self, p: "Post") -> bool:
        return p.has_files()


class PostHasMessage(Proposition):
    """
    Checks if the post has a message.
    """

    def valid(self, p: "Post") -> bool:
        return p.message is not None and len(p.message) > 0


class PostIsThread(Proposition):
    """
    Checks if the post is a thread.
    """

    def valid(self, p: "Post") -> bool:
        return p.is_thread
