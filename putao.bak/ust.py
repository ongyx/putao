# coding: utf8
"""Load/dump UTAU ust projects."""

import collections
from typing import Any, Dict

from putao import core


def _parse(ust: str) -> dict:
    proj: Dict[str, Any] = collections.defaultdict(dict)

    section = None
    for count, entry in enumerate(ust.splitlines(), start=1):
        if entry.startswith("[") and entry.endswith("]"):
            section = entry[2:-1]

        elif entry.count("=") == 1:
            field, _, value = entry.partition("=")
            proj[section][field] = value  # type: ignore

        elif entry.startswith("UST Version"):
            # version format is 'UST Version(version)'
            proj["version"] = entry[11:]

        else:
            raise RuntimeError("Invalid UST syntax on line {count}: {entry}")

    return proj


class Project(core.Project):
    pass
