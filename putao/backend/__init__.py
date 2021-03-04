# coding: utf8
"""Backends provide an abstraction between a source of music notes and putao's song architecture.

Each backend must have a loads() function that accepts a single argument 'data' with type 'bytes'.
This function must return a dict of lists:

{  # tracks
    "track_name": [  # notes
        {
            'type': ...  # either 'note' or 'rest'
            'duration': ...  # how long to hold the note for
            'pitch': ...  # the absolute semitone value of the note, only needed if type is 'note'.
            'overlap': ...  # how much the note overlaps with the previous one. Optional (default:0.0)
        },
        ...
    ]
}
"""

import importlib
import pathlib
import sys
from typing import IO

BACKENDS = [
    p.stem for p in pathlib.Path(__file__).parent.glob("*.py") if p.stem != "__init__"
]


def loads(data: bytes, fmt: str) -> dict:
    """Load data according to fmt.

    Args:
        data: The music data to load.
        fmt: Which backend to use to load the music data.
            Available backends are in BACKENDS.

    Returns:
        The data as a project dict.
    """

    module = f"putao.backend.{fmt}"
    if module in sys.modules:
        backend = sys.modules[module]
    else:
        backend = importlib.import_module(module)

    return backend.loads(data)  # type: ignore


def load(fp: IO, *args) -> dict:
    """Load data from fp according to fmt.

    Args:
        fp: The file to read data from.
            It must be opened in bytes mode ('rb').
        *args: Passed to loads().

    Returns:
        The data as a project dict.
    """

    return loads(fp.read(), *args)
