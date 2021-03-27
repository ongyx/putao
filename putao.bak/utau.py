# coding: utf8
"""UTAU voicebank interface.
NOTE: all time values are in miliseconds.
"""

from __future__ import annotations

import collections.abc as c_abc
import json
import logging
import pathlib
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

import chardet
import numpy as np
import pyworld
import soundfile

_log = logging.getLogger("putao")

RE_SYLLABLE = re.compile(r"(\w+\.wav)=(.+)" + (r",(-?\d+)" * 5))

CFG_FILE = "oto.ini"
JSON_CFG_FILE = "oto.json"


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

    wav: pathlib.Path
    alias: str
    offset: int
    consonant: int
    cutoff: int
    preutterance: int
    overlap: int

    @classmethod
    def parse(cls, entry: str) -> Entry:
        """Parse a line in an oto.ini file.

        Args:
            entry: The line to parse.

        Returns:
            The entry object.
        """
        wav, alias, *times = RE_SYLLABLE.findall(entry)[0]
        times = [int(t) for t in times]

        return cls(wav, alias, *times)

    @classmethod
    def _from_dict(cls, entry: dict) -> Entry:
        new_entry = {
            field: value if field in ("wav", "alias") else int(value)
            for field, value in entry.items()
        }

        return cls(**new_entry)

    def _to_dict(self) -> dict:
        return self.__dict__.copy()


def parse_oto(oto: Union[str, pathlib.Path]) -> Dict[str, Entry]:
    """Parse a oto.ini file.

    Args:
        path: The path to the oto.ini file.

    Returns:
        A dict map of alias to an Entry object.
    """

    oto = pathlib.Path(oto)
    oto_map = {}

    # assuming the voicebank is already utf8...
    with open(oto) as f:
        for _entry in f.readlines():
            entry = Entry.parse(_entry)

            # parent path should be where the voicebank is
            entry.wav = oto.parent / entry.wav

            oto_map[entry.alias] = entry

    return oto_map


class Voicebank(c_abc.Mapping):
    """An UTAU voicebank.

    Args:
        path: The path to the voicebank.
        config: The inital configuration of the voicebank.
            If not specified, config will be loaded from the file instead.

    Attributes:
        path: See args.
        config: The voicebank config.
        cfg_path: The path to the voicebank config file.
            This file is in putao format (JSON).
    """

    def __init__(self, path: Union[str, pathlib.Path], config: Optional[dict] = None):
        self.path = pathlib.Path(path)
        self.cfg_path = self.path / JSON_CFG_FILE

        if config is None:
            with self.cfg_path.open() as f:
                config = json.load(f)

        self.config = config

        entries = self.config.get("entries")

        if entries is None:
            _log.debug("parsing oto.ini")

            entries = parse_oto(self.path / CFG_FILE)
            entries_dict = {alias: entry._to_dict() for alias, entry in entries.items()}

            _log.debug("parsed oto.ini")

            # write back to config file
            with self.cfg_path.open("w") as f:
                json.dump({**self.config, "entries": entries_dict}, f, indent=4)

            self.config["entries"] = entries

        else:
            # load entries from config
            self.config["entries"] = {
                alias: Entry._from_dict(entry) for alias, entry in entries.items()
            }

    def __getitem__(self, key):
        return self.config["entries"][key]

    def __iter__(self):
        return iter(self.config["entries"])

    def __len__(self):
        return len(self.config["entries"])


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


def extract(
    path: Union[str, pathlib.Path],
    to: Union[str, pathlib.Path],
    convert_newlines: bool = True,
):
    """Extract an UTAU voicebank zipfile, while decoding file(name)s correctly.

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
                _log.debug("re-encoding %s to UTF8", zinfo.filename)
                text = unmojibake(zf.read(zinfo))

                if convert_newlines:
                    text = text.replace("\r\n", "\n")

                full_path.write_text(text)

            else:
                _log.debug("extracting %s", zinfo.filename)
                zf.extract(zinfo, path=to)
