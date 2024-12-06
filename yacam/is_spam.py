import sys
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import argparse
from post import Post
from eval import from_config, create_post_eval


def main():
    parser = argparse.ArgumentParser(description="Evaluate the content of a file containing a post.")
    parser.add_argument("file", type=str, help="Path to a file")
    args = parser.parse_args()

    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    post_eval = create_post_eval(*from_config(config["detection"]))

    with open(args.file, "r") as f:
        data = f.read()
    print(not post_eval(Post.from_raw(json.loads(data))))


if __name__ == "__main__":
    main()
