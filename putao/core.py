# coding: utf8

import collections.abc as c_abc
import json
import logging
import pathlib
from typing import Dict, List, Union

from pydub import AudioSegment

from . import model, utau
from .exceptions import TrackError, ProjectError

_log = logging.getLogger("putao")


class Track:
    """A track (sequence of notes).

    Args:
        resampler: The resampler to use to render notes.
    """

    def __init__(self, resampler: model.Resampler):
        self._notes: List[Union[model.Note, model.Rest]] = []
        self.resampler = resampler

    def note(self, phoneme: str, pitch: int, duration: int):
        """Add a note.

        Args:
            phoneme: The syllable to sing.
            pitch: The absolute semitone value of the note from A0, i.e 49 (A4).
            duration: How long to hold the note for (in miliseconds).
        """
        if phoneme not in self.resampler.voicebank:
            raise TrackError(f"'{phoneme}' does not exist in the voicebank")

        self._notes.append(
            model.Note(duration, pitch, self.resampler.voicebank[phoneme])
        )

    def rest(self, duration: int):
        """Add a rest (break in-between notes).

        Args:
            duration: How long to rest for.
        """
        self._notes.append(model.Rest(duration))

    def render(self) -> AudioSegment:
        """Render all notes sequentially to an audio segment.

        Returns:
            The audio segment.
        """
        track_render = AudioSegment.empty()
        total = len(self._notes)

        for count, note in enumerate(self._notes, start=1):

            timestamp = len(track_render)
            overlap = 0

            next_note = None

            try:
                next_note = self._notes[count + 1]
                if isinstance(next_note, model.Note):
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

            try:
                render = self.resampler.render(note, next_note)
            except Exception as e:
                _log.critical(f"SHIT: failed to render note {count} ({note})!!!")
                raise e

            # extend final render (so overlay won't be truncated)
            track_render += AudioSegment.silent(len(render) - overlap)

            # overlap this note into previous one
            track_render = track_render.overlay(render, position=timestamp - overlap)

        return track_render

    def dump(self) -> List[dict]:
        notes = []

        for note in self._notes:
            notes.append(note.dump())

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
        resampler: The name of the resampler to use.
            Available resamplers are in the dictionary model.RESAMPLERS.
            If not given, defaults to 'WorldResampler'.

    Raises:
        ProjectError, if the resampler given by name does not exist.
    """

    def __init__(
        self, vb_path: Union[str, pathlib.Path], resampler: str = "WorldResampler"
    ):
        self.voicebank = utau.Voicebank(vb_path)
        self.tracks: Dict[str, Track] = {}

        try:
            self.resampler = model.RESAMPLERS[resampler](self.voicebank)  # type:ignore
        except KeyError:
            raise ProjectError(f"resampler {resampler} does not exist")

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

        track = Track(self.resampler)
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
        """Load a project from a dict."""
        for name, notes in data["tracks"].items():
            track = self.new_track(name)
            track.load(notes)

    def fload(self, file: Union[str, pathlib.Path]):
        """Load a project from a file."""
        with open(file, "r") as f:
            self.load(json.load(f))

    def dump(self) -> dict:
        """Dump a project to a dict."""
        data = {}
        for name, track in self.tracks.items():
            data[name] = track.dump()

        return data

    def fdump(self, file: Union[str, pathlib.Path]):
        """Dump a project to a file."""
        with open(file, "w") as f:
            json.dump(self.dump(), f, indent=4)
