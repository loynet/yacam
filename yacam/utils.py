from urllib.parse import urlparse

from urlextract import URLExtract


class URLFinder(object):
    """
    Singleton wrapper for URLExtract with extra functionality.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(URLFinder, cls).__new__(cls)
            cls._instance.extractor = URLExtract()
        return cls._instance

    def find(self, s: str, unique: bool = False) -> list:
        return self.extractor.find_urls(s, only_unique=unique)

    def remove(self, s: str) -> str:
        for url in self.find(s):
            # Count is 1 because find returns multiple instances of the same URL
            s = s.replace(url, "", 1)
        return s


def parse_path(url: str) -> list[str]:
    remove_empty_strings = lambda s: list(filter(None, s))
    parsed = urlparse(url)
    return remove_empty_strings(url.split("/")[1:] if not parsed.scheme else parsed.path.split("/")[1:])
