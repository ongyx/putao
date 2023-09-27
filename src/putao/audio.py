"""Classes for audio editing and processing.

The API aims to be similar to pydub.AudioSegement (https://github.com/jiaaro/pydub),
except that audio segments are backed by NumPy arrays for ease of use with soundfile/librosa.
"""

import contextlib
import dataclasses
import pathlib
from typing import IO, Any, BinaryIO, Iterator, Literal, Self

import numpy as np
import soundfile


@dataclasses.dataclass
class Segment:
    """An array of audio samples.
    The underlying array is guaranteed to be immutable.

    Attributes:
        array: A vector or matrix of audio samples in float64.
            They represent mono or stereo audio respectively.
        srate: The number of audio samples per second.
    """

    array: np.ndarray
    srate: int

    def __post_init__(self):
        # Only set the array to read-only if its not a view.
        # Otherwise, let the view inherit the writeable flag.
        if self.array.flags["OWNDATA"]:
            self.array.flags["WRITEABLE"] = False

    @property
    def channels(self) -> int:
        """Get the number of channels in the audio segment.

        Typically, audio segments only have 1 (mono) or 2 (stereo) channels.
        """

        return len(self.array.shape)

    def set_channels(self, channels: Literal[1, 2]) -> Self:
        """Spawn an audio segment with the specified number of channels.

        Args:
            channels: The number of channels to spawn the segment with.

        Returns:
            The spawned audio segment, or the existing audio segment if it already has the same number of channels.
        """

        match self.channels, channels:
            case 2, 1:
                # Stereo to mono.
                return self._spawn(self.array.mean(axis=1))
            case 1, 2:
                # Mono to stereo.
                return self._spawn(np.repeat(self.array, 2, axis=1))
            case _:
                # Return as-is.
                return self

    def fade(
        self,
        to_gain: float = 0,
        from_gain: float = 0,
        start: float | None = None,
        end: float | None = None,
    ):
        """Apply a fade effect to the audio segment.

        Args:
            to_gain: Final gain factor.
            from_gain: Initial gain factor.
            start: Where the fade should start.
            end: Where the fade should end.

        Returns:
            A copy of the audio segment with the fade applied.
        """

        if to_gain == 0 and from_gain == 0:
            return self

        start = start or 0
        end = end or len(self)

        if not start < end:
            raise ValueError("start must be earlier than end")

        with self.mutable() as segment:
            fade_arr = segment[start:end].array
            # Logarithmic fade curve.
            fade_arr *= np.logspace(from_gain, to_gain, num=len(fade_arr)) / 10

            return segment

    @contextlib.contextmanager
    def mutable(self) -> Iterator[Self]:
        """Create a temporarily mutable copy of the audio segment.
        After the context closes, the copy becomes immutable.
        """

        segment = self._spawn()
        segment.array.flags["WRITEABLE"] = True

        try:
            yield segment
        finally:
            segment.array.flags["WRITEABLE"] = False

    def _spawn(self, array: np.ndarray | None = None, srate: int | None = None) -> Self:
        if array is None:
            array = self.array.copy()

        if srate is None:
            srate = self.srate

        return Segment(array, srate)

    def export(self, file: str | pathlib.Path | BinaryIO, format: str = "WAV"):
        """Export an audio segment to a file.

        Args:
            file: The path-like or file-like object to export to.
            format: The format to export with.
                See soundfile.available_formats().
        """

        soundfile.write(file, self.array, self.srate, format=format)

    @classmethod
    def from_file(cls, file: str | pathlib.Path | IO[bytes]) -> Self:
        """Read an audio file into a segment.

        Args:
            file: The path-like or file-like object to read samples from.

        Returns:
            The audio segment.
        """
        return cls(*soundfile.read(file, dtype="float64"))

    @classmethod
    def silent(cls, duration: float = 1000, sample_rate: int = 44100) -> Self:
        """Create a slient audio segment.

        Args:
            duration: Length of the audio segment in milliseconds.
                Defaults to 1000ms (1 second).
            sample_rate: Sample rate of the audio segment.
                Defaults to 44.1kHz.

        Returns:
            The slient audio segment.
        """

        return cls(np.zeros(int(duration / 1000 * sample_rate)), sample_rate)

    def milliseconds(self, samples: int) -> float:
        """Convert a count of audio samples to milliseconds.

        Args:
            samples: The audio sample count.

        Returns:
            The audio sample count as a duration in milliseconds.
        """

        return samples / self.srate * 1000

    def __len__(self) -> int:
        return round(self.milliseconds(len(self.array)))

    def samples(self, ms: float) -> int:
        """Convert a duration in milliseconds to a count of audio samples.

        Args:
            ms: The duration in milliseconds.

        Returns:
            The duration as an audio sample count.
        """

        return int(ms / 1000 * self.srate)

    def __getitem__(self, ms: float | slice) -> Self | Any:
        if isinstance(ms, slice):
            if ms.step is not None:
                # Split the audio sample into chunks.
                return (
                    self._spawn(a) for a in np.hsplit(self.array, self.samples(ms.step))
                )

            start = self.samples(ms.start or 0)
            stop = self.samples(ms.stop or len(self.array))

            return self._spawn(self.array[start:stop])

        # Return 1 millisecond of audio.
        return self[ms : ms + 1]
