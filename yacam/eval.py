from abc import ABC, abstractmethod
from configparser import ConfigParser
from urlextract import URLExtract

from post import Post

import re


# Ideally this would be an interface, but python isn't go so too bad :(
class StringEval(ABC):
    @abstractmethod
    def is_spam(self, s: str) -> bool:
        pass


class Threshold(StringEval):
    def __init__(self, config: ConfigParser):
        tokens = (
            "["
            + "".join([re.escape(e) for e in config["detection"]["tokens"].split()])
            + "]"
        )
        self.pattern = re.compile(tokens, re.IGNORECASE)
        self.max = config["detection"].getfloat("max_threshold")

    def is_spam(self, s: str) -> bool:
        return len(s) > 0 and (len(re.findall(self.pattern, s)) / len(s)) > self.max


class Counter(StringEval):
    def __init__(self, config: ConfigParser):
        tokens = (
            "["
            + "".join([re.escape(e) for e in config["detection"]["tokens"].split()])
            + "]"
        )
        # Compiles the regex for the entry and group of entries
        e = r"[^\W_]" + tokens
        self.entry_pattern = re.compile(e, re.IGNORECASE)
        self.pattern = re.compile(f"(?:{e})+", re.IGNORECASE)

        self.max = config["detection"].getint("max_consecutive_entries")

    def is_spam(self, s: str) -> bool:
        for found in re.finditer(self.pattern, s):
            if (
                len(
                    re.findall(
                        self.entry_pattern, found.string[found.start() : found.end()]
                    )
                )
                > self.max
            ):
                return True
        return False


class PostEval:
    def __init__(self, config: ConfigParser):
        mode = config["detection"]["mode"]
        if mode == "threshold":
            self.str_eval: StringEval = Threshold(config)
        elif mode == "entries":
            self.str_eval: StringEval = Counter(config)
        else:
            raise ValueError('detection mode must be "threshold" or "entries"')

        # Read the whitelist configs, it is optional
        self.whitelist: list[str] = config.get(
            "detection", "countries_whitelist", fallback=""
        ).split()

        self.url_extr: URLExtract = URLExtract()

    def is_spam(self, p: Post) -> bool:
        # Check if the poster used a capcode, basically if is an admin, mod or part of the global staff
        if p.has_capcode():
            return False

        # Check if a post has a messages and files
        if not p.message or not p.has_files():
            return False

        # Check if the post is from a whitelisted country
        if p.has_geo_flag() and p.author.flag.code in self.whitelist:
            return False

        # 99% of the posts are usually considered not spam at this point

        # Check for urls
        msg = p.message
        urls = self.url_extr.find_urls(msg, get_indices=True)
        # No urls = no problem
        if len(urls) == 0:
            return False

        # Remove found urls
        for url in urls:
            msg = msg[: url[1][0]] + msg[url[1][1] :]

        return self.str_eval.is_spam(msg)
