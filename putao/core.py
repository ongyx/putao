# coding: utf8

import abc
import pathlib
from typing import List, Optional, Union

from pydub import AudioSegment

from putao import internal, utils, voicebank
from putao.exceptions import TrackError


class Track:
    def __init__(self, voicebank: voicebank.Voicebank):
        self._notes: List[internal.NoteBase] = []
        self.voicebank = voicebank

    def note(self, phoneme: str, pitch: int, duration: int):
        if phoneme not in self.voicebank:
            raise TrackError(f"'{phoneme}' does not exist in the voicebank")

        self._notes.append(internal.Note(self.voicebank[phoneme], pitch, duration))

    def rest(self, duration: int):
        self._notes.append(internal.Rest(duration))

    def render(self, path: Union[str, pathlib.Path]):
        final_render = AudioSegment.empty()

        for count, note in enumerate(self._notes):
            timestamp = len(final_render)
            preutter = 0
            overlap = 0

            try:
                next_note = self._notes[count + 1]
                if isinstance(next_note, internal.Note):
                    preutter = next_note.entry.preutterance
                    overlap = next_note.entry.overlap
            except IndexError:
                # no more notes
                pass

            render = note.render(preutter, overlap)

            # extend final render (so overlay won't be truncated)
            final_render += AudioSegment.silent(len(render) - overlap)
            final_render = final_render.overlay(render, position=timestamp - overlap)

        final_render.export(path, format="wav")

    def dump(self) -> List[dict]:
        notes = []

        for note in self._notes:
            dump = note.dump()
            if isinstance(note, internal.Note):
                dump.update(
                    {
                        "pitch": note.pitch,
                        "phoneme": note.entry.alias,
                    }
                )

            notes.append(dump)

        return notes

    def load(self, note_dumps: List[dict]):
        self._notes.clear()

        for dump in note_dumps:
            if dump["type"] == "note":
                self.note(*[dump[arg] for arg in ("phenome", "pitch", "duration")])
            elif dump["type"] == "rest":
                self.rest(dump["duration"])


class Project:
    def __init__(self, voicebank_path: Union[str, pathlib.Path], pitch: int):
        self.voicebank = voicebank.Voicebank(voicebank_path, pitch)
