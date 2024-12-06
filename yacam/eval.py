from typing import Callable

# Do not remove these imports, they are used when creating
# propositions from the config file.
from propositions import *
from post import Post


def create_post_eval(
    rules: list[Proposition],
    filters: list[Proposition] = None,
) -> Callable[[Post], bool]:
    return lambda p: any(f.valid(p) for f in filters or []) or all(r.valid(p) for r in rules)


def from_config(config: dict) -> tuple[list[Proposition], list[Proposition]]:
    """
    Create a ruleset and a set of filters from the config .yaml file.

    :param config: The configuration file.
    :return: A tuple with the rules and filters.
    """

    # Dynamically load the propositions from the config file.
    # TODO: Rethink this approach, it is weird and relies to much on the users to not mess up the config file.
    def as_proposition(entry: dict) -> Proposition:
        preposition = globals()[entry["name"]](**entry.get("params", {}))
        return Negate(preposition) if entry.get("negate", False) else preposition

    return [as_proposition(entry) for entry in config["rules"]], [as_proposition(entry) for entry in config["filters"]]
