# coding: utf8
"""This module provides utils to register a source."""

from typing import Callable, Dict, List

from ..core import Project

source_func = Callable[[bytes, Project], None]

_REG: Dict[str, source_func] = {}


def formats() -> List[str]:
    return list(_REG.keys())


def loads(fmt: str, data: bytes, project: Project):
    """Load source data into a project.

    Args:
        fmt: The source data format.
        data: The data to load.
        project: The project to load the data into.

    Raises:
        KeyError, if the format was not found.
    """

    if fmt not in _REG:
        raise KeyError(f"format not recognised: {fmt}")

    fn = _REG[fmt]
    fn(data, project)


def register(fmt: str, fn: source_func):
    """Register a new source.

    Args:
        fmt: The file extension of the source data (mid, mml, etc.)
        fn: The function to parse the source data.
    """

    _REG[fmt] = fn
