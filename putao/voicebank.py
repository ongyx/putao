# coding: utf8
"""UTAU voicebank interface.
NOTE: all time values are in miliseconds.
"""

from __future__ import annotations

import collections.abc as c_abc
import logging
import pathlib
import re
import zipfile
from dataclasses import dataclass
from typing import Union

import chardet

_log = logging.getLogger("putao")

RE_SYLLABLE = re.compile(r"(\w+\.wav)=(.+)" + (r",(-?\d+)" * 5))


@dataclass
class Entry:
    """An entry in the oto.ini config of an UTAU voicebank.
    (All time values are in miliseconds.)

    Args:
        wav: The absolute path to the wavfile.
        alias: The name of the phoneme to associate with the wavfile.
        offset: Unused length of time at the _start_ of the wavfile.
        consonant: Length of time of the consonant.
        cutoff: Unused length of time at the _end_ of the wavfile.
        preutterance: Length of time to extend the start of the note into the previous one.
            The previous note is shortened.
            This should be shorter than the overlap (below).
        overlap: Length of time to extend the previous note into the current note.
            This extension overlaps into the start of the current note.

    Attributes:
        See args.
    """

    wav: Union[str, pathlib.Path]
    alias: str
    offset: int
    consonant: int
    cutoff: int
    preutterance: int
    overlap: int

    @staticmethod
    def parse(entry: str) -> Entry:
        """Parse a line in an oto.ini file.

        Args:
            entry: The line to parse.

        Returns:
            The entry object.
        """
        wav, alias, *times = RE_SYLLABLE.findall(entry)[0]
        times = [int(t) for t in times]

        return Entry(wav, alias, *times)


class Voicebank(c_abc.Mapping):
    """An UTAU voicebank.

    Args:
        path: The path to the voicebank.
        pitch: The semitone value of the wavfiles in the voicebank.

    Attributes:
        path: See args.
        pitch: See args.
    """

    def __init__(self, path: Union[str, pathlib.Path], pitch: int):
        self.path = pathlib.Path(path)
        self.pitch = pitch

        self._wav_map = {}

        _log.debug("parsing oto.ini")

        # assuming the voicebank is already utf8...
        with (self.path / "oto.ini").open() as f:
            for _entry in f.readlines():
                entry = Entry.parse(_entry)

                # absolute path
                entry.wav = self.path / entry.wav
                self._wav_map[entry.alias] = entry

        _log.debug("parsed oto.ini")

    def __getitem__(self, key):
        return self._wav_map[key]

    def __iter__(self):
        return iter(self._wav_map)

    def __len__(self):
        return len(self._wav_map)


def unmojibake(text: Union[str, bytes]) -> str:
    """Re-encode text/bytes to UTF8 from Shift-JIS or other encodings.

    Args:
        text: The text to re-encode.

    Returns:
        The UTF8-ified text.
    """

    if isinstance(text, str):
        raw = text.encode("cp437")
    else:
        # already bytes
        raw = text

    try:
        return raw.decode("sjis")
    except UnicodeDecodeError:
        # use chardet to figure out encoding
        encoding = chardet.detect(raw)["encoding"]
        return raw.decode(encoding)


def is_utf8(zinfo: zipfile.ZipInfo) -> bool:
    """Check whether the filename of the zipinfo is utf8."""
    return bool(zinfo.flag_bits & 0x800)


def extract_voicebank(
    path: Union[str, pathlib.Path],
    to: Union[str, pathlib.Path],
    convert_newlines: bool = True,
):
    """Extract an UTAU voicebank zipfile, while decoding file(names) correctly.

    Args:
        path: The path to the zipfile.
        to: The folder to extract the zipfile to.
        convert_newlines: Whether or not to replace Windows-style newlines (CRLF) with *nix-style newlines (LF).
            Defaults to True.
    """
    path = pathlib.Path(path)
    to = pathlib.Path(to)

    with zipfile.ZipFile(path) as zf:
        for zinfo in zf.infolist():
            if not is_utf8(zinfo):
                # most voicebanks are either romanji (ASCII) or kanji/hirigana (SHIFT-JIS).
                zinfo.filename = unmojibake(zinfo.filename)

            full_path = to / zinfo.filename
            full_path.parent.mkdir(exist_ok=True)

            # decode any text files and extract manually
            if full_path.suffix[1:] in ("txt", "ini"):
                text = unmojibake(zf.read(zinfo))

                if convert_newlines:
                    text = text.replace("\r\n", "\n")

                full_path.write_text(text)

            else:
                zf.extract(zinfo, path=to)
