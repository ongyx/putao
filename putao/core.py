# coding: utf8

from __future__ import annotations

import collections.abc as c_abc
import gzip
import json
import logging
import pathlib
from typing import Dict, IO, List, Optional, Union

from pydub import AudioSegment

from . import model, utau, utils
from .jsonclasses import dataclass
from .resamplers import RESAMPLERS

from .__version__ import __version__
from .exceptions import TrackError, ProjectError

_log = logging.getLogger(__name__)


@dataclass
class Config:
    """A project's configuration.

    voicebank: The path to the voicebank.
        The voicebank must be in UTAU format, and must have a oto.ini file.
    resampler: The name of the resampler to use.
        Available resamplers are in the dictionary model.RESAMPLERS.
        If not given, defaults to 'WorldResampler'.
    """

    name: str = ""
    author: str = ""
    voicebank: str = "."
    resampler: str = "world"
    version: str = __version__


class Track:
    """A track (sequence of notes).

    Args:
        resampler: The resampler to use to render notes.
    """

    def __init__(self, resampler: model.Resampler):
        self.notes: List[model.Note] = []
        self.resampler = resampler

    def note(self, syllable: str, pitch: int, duration: int):
        """Add a note.

        Args:
            syllable: The syllable to sing.
            pitch: The absolute semitone value of the note from A0, i.e 49 (A4).
            duration: How long to hold the note for (in miliseconds).
        """
        if syllable not in self.resampler.voicebank:
            raise TrackError(f"'{syllable}' does not exist in the voicebank")

        self.notes.append(model.Note(duration, pitch, syllable))  # type: ignore

    def rest(self, duration: int):
        """Add a rest (break in-between notes).

        Args:
            duration: How long to rest for.
        """
        self.notes.append(model.Rest(duration))

    def render(self) -> AudioSegment:
        """Render all notes sequentially to an audio segment.

        Returns:
            The audio segment.
        """
        track_render = AudioSegment.empty()
        total = len(self.notes)

        for count, note in enumerate(self.notes, start=1):

            timestamp = len(track_render)
            overlap = 0

            next_note = None

            try:
                next_note = self.notes[count + 1]
                if next_note.syllable:
                    overlap = self.resampler.voicebank[next_note.syllable].overlap
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

            except Exception as e:
                _log.critical(f"[track] failed to render note {count} ({note})!!!")
                raise e

            # set mono channels and CD-quality sample rate
            render = render.set_frame_rate(utils.SAMPLE_RATE)

            # extend final render (so overlay won't be truncated)
            track_render += AudioSegment.silent(len(render) - overlap)

            # overlap this note into previous one
            track_render = track_render.overlay(render, position=timestamp - overlap)

        return track_render


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
        config: The project config as a Config object.
            If not given, a new project config will be created.

    Raises:
        ProjectError, if the resampler given by name does not exist.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        tracks: Optional[Dict[str, List[model.Note]]] = None,
    ):

        self.config = config or Config()
        self.tracks: Dict[str, Track] = {}

        self.voicebank = utau.Voicebank(self.config.voicebank)

        try:
            cls = RESAMPLERS[self.config.resampler]
        except KeyError:
            raise ProjectError(f"resampler {self.config.resampler} does not exist")

        self.resampler = cls(self.voicebank)

        for name, notes in (tracks or {}).items():
            track = self.new_track(name)
            track.notes = notes

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

        return cls(**json.loads(config))

    @classmethod
    def load(cls, fp: Union[str, pathlib.Path, IO]) -> Project:
        """Load a project from a path or file object."""

        if isinstance(fp, (str, pathlib.Path)):
            fp = gzip.open(fp, "rt")

        return cls.loads(fp.read())

    def dumps(self) -> str:
        """Dump this project to a JSON string."""

        data = {
            "config": self.config,
            "tracks": {name: track.notes for name, track in self.tracks.items()},
        }

        return json.dumps(data, indent=4)

    def dump(self, fp: Union[str, pathlib.Path, IO]):
        """Dump this project to a path or file object."""

        if isinstance(fp, (str, pathlib.Path)):
            fp = gzip.open(fp, "wt")

        fp.write(self.dumps())
