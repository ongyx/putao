# coding: utf8
"""Compatibility layer between putao and UTAU (so UTAU voicebanks can be used)."""

import collections
import pathlib
import re
import zipfile
from typing import Union

import chardet

RE_SYLLABLE = re.compile(r"(\w+\.wav)=(.+)" + (r",(-?\d+)" * 5))

Syllable = collections.namedtuple(
    "Syllable", "wav consonant offset cutoff preutterance overlap"
)


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


class Voicebank:
    def __init__(self, path: Union[str, pathlib.Path]):
        self.path = pathlib.Path(path)
        self.wav_map = {}

        # assuming the voicebank is already utf8...
        with (self.path / "oto.ini").open() as f:
            for entry in f.readlines():
                try:
                    parsed_entry = list(RE_SYLLABLE.findall(entry)[0])
                except IndexError:
                    print(entry)
                    raise

                wav, alias, *positions = parsed_entry
                self.wav_map[alias] = Syllable(wav, *[int(p) for p in positions])


if __name__ == "__main__":
    import pprint

    pprint.pp(Voicebank(".").wav_map)
