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
from typing import Dict, Set, Union

import chardet

_log = logging.getLogger(__name__)

RE_SYLLABLE = re.compile(r"(\w+\.wav)=(.+)" + (r",(-?\d+)" * 5))

CONFIG_FILE = "oto.ini"
JSON_CONFIG_FILE = "oto.json"


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
        path: The absolute path to the wavfile, as a pathlib.Path object.

    Attributes:
        See args.
    """

    wav: str
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
        try:
            wav, alias, *times = RE_SYLLABLE.findall(entry)[0]
            times = [int(t) for t in times]
        except IndexError:
            # oto has blank entries (only the filename is in the line)
            wav = entry.split("=")[0]
            alias = wav.split(".")[0]
            times = [0, 0, 0, 0, 0]

        return cls(wav, alias, *times)

    @classmethod
    def load(cls, entry: dict) -> Entry:
        """Load an entry from its dict representation."""
        new_entry = {
            field: value if field in ("wav", "alias") else int(value)
            for field, value in entry.items()
        }

        return cls(**new_entry)

    def path(self) -> pathlib.Path:
        return pathlib.Path(self.wav)

    def dump(self) -> dict:
        """Dump this entry to a dict representation."""
        return self.__dict__.copy()


def parse_oto(oto: Union[str, pathlib.Path], enc: str = "utf8") -> Dict[str, Entry]:
    """Parse an oto.ini file.

    Args:
        path: The path to the oto.ini file.
        enc: The encoding of the file.
            Most voicebanks are encoded in Shift-JIS, or very rarely UTF-8.

    Returns:
        A dict map of alias to an Entry object.
    """

    oto = pathlib.Path(oto)
    oto_map = {}

    # assuming the voicebank is already utf8...
    with open(oto, encoding=enc) as f:
        for _entry in f.readlines():
            entry = Entry.parse(_entry)
            oto_map[entry.alias] = entry

            if not entry.consonant:
                _log.warning(f"{entry.alias}: consonant length is zero")

            if not entry.overlap < entry.preutterance:
                _log.warning(f"{entry.alias}: overlap ({entry.overlap}) should be before preutterance ({entry.preutterance})")

    return oto_map


class Voicebank(c_abc.Mapping):
    """An UTAU voicebank.

    Args:
        path: The path to the voicebank.

    Attributes:
        path: See args.
        entries: The entries loaded from the oto.ini file.
        wavfiles: A set of all the wav file paths in oto.ini.
    """

    def __init__(self, path: Union[str, pathlib.Path]):
        self.path = pathlib.Path(path).resolve(strict=True)

        self.entries: Dict[str, Entry]
        self.wavfiles: Set[str] = set()

        _log.debug("parsing oto.ini")

        self.entries = parse_oto(self.path / CONFIG_FILE)

        _log.debug("parsed oto.ini")

        # wavfiles should be in the same directory as the oto.ini file.
        # make the paths absolute
        for _, entry in self.entries.items():
            entry.wav = str(self.path / entry.wav)
            self.wavfiles.add(entry.wav)

    def __getitem__(self, key):
        return self.entries[key]

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)


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

                full_path.write_text(text, encoding="UTF8")

            else:
                _log.debug("extracting %s", zinfo.filename)
                zf.extract(zinfo, path=to)
