# coding: utf8

import collections.abc as c_abc
import logging
import pathlib
from typing import Dict, List, Union

from pydub import AudioSegment

from putao import internal, voicebank
from putao.exceptions import TrackError, ProjectError

_log = logging.getLogger("putao")


class Track:
    """A track (sequence of notes).

    Args:
        voicebank: The voicebank object to use to render notes.
    """

    def __init__(self, voicebank: voicebank.Voicebank):
        self._notes: List[internal.NoteBase] = []
        self.voicebank = voicebank

    def note(self, phoneme: str, pitch: int, duration: int):
        """Add a note.

        Args:
            phoneme: The syllable to sing.
            pitch: The absolute semitone value of the note.
            duration: How long to hold the note for (in miliseconds).
        """
        if phoneme not in self.voicebank:
            raise TrackError(f"'{phoneme}' does not exist in the voicebank")

        self._notes.append(internal.Note(self.voicebank[phoneme], pitch, duration))

    def rest(self, duration: int):
        """Add a rest (break in-between notes).

        Args:
            duration: How long to rest for.
        """
        self._notes.append(internal.Rest(duration))

    def render(self) -> AudioSegment:
        """Render all notes sequentially to an audio segment.

        Returns:
            The audio segment.
        """
        track_render = AudioSegment.empty()
        total = len(self._notes)

        for count, note in enumerate(self._notes, start=1):

            timestamp = len(track_render)
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

            _log.debug(
                "rendering note %s of %s (track duration: %ss)",
                count,
                total,
                timestamp / 1000,
            )

            render = note.render(preutter, overlap, self.voicebank.pitch)

            # extend final render (so overlay won't be truncated)
            track_render += AudioSegment.silent(len(render) - overlap)
            track_render = track_render.overlay(render, position=timestamp - overlap)

        return track_render

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
                self.note(*[dump[arg] for arg in ("phoneme", "pitch", "duration")])
            elif dump["type"] == "rest":
                self.rest(dump["duration"])


class Project(c_abc.MutableMapping):
    """A project (a.k.a song).

    First create a new track:

    proj = Project(".", 49)  # use the voicebank in curdir, pitched to C4
    track = proj.new_track("lead")

    If you want to access any existing tracks, use dict notation:

    existing_track = proj["lead"]

    You can also delete tracks:

    del proj["lead"]

    Args:
        vb_path: The path to the voicebank.
            The voicebank must be in UTAU format, and must have a oto.ini file.
        pitch: The pitch of the voicebank in semitones (as a int).
    """

    def __init__(self, vb_path: Union[str, pathlib.Path], pitch: int):
        self.voicebank = voicebank.Voicebank(vb_path, pitch)
        self.tracks: Dict[str, Track] = {}

    def __getitem__(self, name):
        return self.tracks[name]

    def __setitem__(self, name, value):
        raise ProjectError("can't directly set tracks: use .new_track() instead")

    def __delitem__(self, name):
        del self.tracks[name]

    def __iter__(self):
        return iter(self.tracks)

    def __len__(self):
        return len(self.tracks)

    def new_track(self, name: str) -> Track:
        """Create a new track.

        Args:
            name: The track name.

        Returns:
            The newly created track.

        Raises:
            ProjectError, if it already exists.
        """

        if name in self.tracks:
            raise ProjectError(f"track already exists: '{name}'")

        track = Track(self.voicebank)
        self.tracks[name] = track

        _log.debug("created new track %s", name)

        return track

    def render(self, path: Union[str, pathlib.Path]):
        """Render all tracks to a wavfile.

        Args:
            path: The file to render to.
        """

        project_render = AudioSegment.empty()
        for name, track in self.tracks.items():
            _log.debug("rendering track %s", name)
            render = track.render()

            project_len = len(project_render)
            render_len = len(render)

            if project_len < render_len:
                project_render += AudioSegment.silent(render_len - project_len)

            project_render = project_render.overlay(render)

        project_render.export(path, format="wav")

    def load(self, data: dict):
        """Load a project from a dict.

        Args:
            data: The project dict to load.
        """
        for name, notes in data["tracks"].items():
            track = self.new_track(name)
            track.load(notes)

    def dump(self) -> dict:
        """Dump a project to a dict.

        Returns:
            The project data as a dict.
        """
        data = {}
        for name, track in self.tracks.items():
            data[name] = track.dump()

        return data
