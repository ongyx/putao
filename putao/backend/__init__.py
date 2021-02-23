# coding: utf8
"""Backends provide an abstraction between a source of music notes and putao's song architecture.

Each backend must have a load() function that accepts a single argument 'data' with type 'bytes'.
For each note, this function must yield a dict:

{
    'type': ...  # either 'note' or 'rest'
    'duration': ...  # how long to hold the note for
    'pitch': ...  # the absolute semitone value of the note, only needed if type is 'note'.
}
"""

import importlib
import pathlib
import sys

BACKENDS = [
    p.stem for p in pathlib.Path(__file__).parent.glob("*.py") if p.stem != "__init__"
]


def load(data: bytes, fmt: str) -> dict:
    """Load data according to fmt.

    Args:
        data: The music data to load.
        fmt: Which backend to use to load the music data.
            Available backends are in BACKENDS.
    """

    module = f"putao.backend.{fmt}"
    if module in sys.modules:
        backend = sys.modules[module]
    else:
        backend = importlib.import_module(module)

    return {"notes": [n for n in backend.load(data)]}  # type: ignore
