# coding: utf8

from __future__ import annotations

import collections.abc as c_abc
import json
import logging
import pathlib
from typing import Any, Dict, IO, List, Optional, Union

from pydub import AudioSegment

from . import model, utau
from .exceptions import TrackError, ProjectError, FrqNotFoundError

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
                "[track] rendering note %s of %s (track duration: %ss)",
                count,
                total,
                timestamp / 1000,
            )

            try:
                render = self.resampler.render(note, next_note)

            except FrqNotFoundError as e:
                _log.critical(
                    f"[track] resampler could not find frq files for {e}: generate them first!"
                )

            except Exception as e:
                _log.critical(f"[track] failed to render note {count} ({note})!!!")
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
        config: The project config (as a dict) to load.
            If not given, a new project will be created using defaults.

            Any config given should at least have these keys:

            'voicebank': The path to the voicebank.
                The voicebank must be in UTAU format, and must have a oto.ini file.
            'resampler': The name of the resampler to use.
                Available resamplers are in the dictionary model.RESAMPLERS.
                If not given, defaults to 'WorldResampler'.

    Raises:
        ProjectError, if the resampler given by name does not exist.
    """

    DEFAULTS: Dict[str, Any] = {"voicebank": ".", "resampler": "WorldResampler"}

    def __init__(self, config: Optional[dict] = None):

        if config is None:
            config = self.DEFAULTS.copy()

        self.config = config
        self.voicebank = utau.Voicebank(self.config["voicebank"])

        try:
            resampler_cls = model.RESAMPLERS[self.config["resampler"]]
        except KeyError:
            raise ProjectError(f"resampler {self.config['resampler']} does not exist")
        else:
            self.resampler = resampler_cls(self.voicebank)  # type:ignore

        # load tracks
        self.tracks: Dict[str, Track] = {}

        if "tracks" in self.config:
            for name, notes in self.config["tracks"].items():
                track = self.new_track(name)
                track.load(notes)

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

        _log.debug("[project] created new track %s", name)

        return track

    def render(self, path: Union[str, pathlib.Path]):
        """Render all tracks to a wavfile.

        Args:
            path: The file to render to.
        """

        project_render = AudioSegment.empty()
        for name, track in self.tracks.items():
            _log.info("[project] rendering track %s", name)
            render = track.render()

            project_len = len(project_render)
            render_len = len(render)

            if project_len < render_len:
                project_render += AudioSegment.silent(render_len - project_len)

            project_render = project_render.overlay(render)

        project_render.export(path, format="wav")

    @classmethod
    def loads(cls, config: str) -> Project:
        """Load a project from a JSON string."""

        return cls(json.loads(config))

    @classmethod
    def load(cls, fp: Union[str, pathlib.Path, IO]) -> Project:
        """Load a project from a file."""

        if isinstance(fp, (str, pathlib.Path)):
            fp = open(fp, "r")

        return cls.loads(fp.read())

    def dumps(self) -> str:
        """Dump this project to a JSON string."""

        config = {
            **self.config,
            "tracks": {name: track.dump() for name, track in self.tracks.items()},
        }
        return json.dumps(config, indent=4)

    def dump(self, fp: Union[str, pathlib.Path, IO]):
        """Dump this project to a file."""

        if isinstance(fp, (str, pathlib.Path)):
            fp = open(fp, "w")

        fp.write(self.dumps())
