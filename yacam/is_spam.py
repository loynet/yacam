import argparse
import configparser
import json

from urlextract import URLExtract
from eval import Threshold, Counter, PostEval
from post import Post


def main():
    parser = argparse.ArgumentParser(description="Evaluate the content file.")
    parser.add_argument(
        "type", choices=["post", "string"], help="Type of data to evaluate."
    )
    parser.add_argument(
        "file", type=str, help="Path to a file containing data to evaluate."
    )
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read("config.ini")

    with open(args.file, "r") as f:
        data = f.read()

    if args.type == "string":
        mode_classes = {"threshold": Threshold, "entries": Counter}
        urls = URLExtract().find_urls(data, only_unique=True)
        data = "".join(data.replace(url, "") for url in urls)
        print(mode_classes[config["detection"]["mode"]](config).is_spam(data))

    elif args.type == "post":
        print(PostEval(config).is_spam(Post.from_raw(json.loads(data))))


if __name__ == "__main__":
    main()
