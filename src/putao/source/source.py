# coding: utf8
"""This module provides utils to register a source."""

import abc
from typing import Callable, Dict, IO, List

from ..core import Project

_REG = {}


class Source(abc.ABC):
    """A source handles loading arbitrary data into a Project."""

    @property
    @abc.abstractclassmethod
    def format(self) -> str:
        """The name of this source (used when selecting which source to use)."""
        pass

    @abc.abstractmethod
    def loads(self, data: bytes, project: Project):
        """Load data into the project.

        Args:
            data: The data to load.
            project: The project to load into.
        """
        pass

    def load(self, file: IO, project: Project):
        """Load data from a file into the project.

        Args:
            file: The file to load the data from.
            project: The project to load into.
        """
        self.loads(file.read(), project)

    @classmethod
    def reg(cls):
        """Register this source to the global registry."""
        _REG[cls.format] = cls


def formats() -> List[str]:
    return list(_REG.keys())
