# coding: utf8
"""This modules contains the Abstract Base Class for a resampler to implement."""

import abc
from typing import Union

from pydub import AudioSegment

from ..note import Note, Rest


class Resampler(abc.ABC):
    def __init__(self):
        pass
