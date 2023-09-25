"""Classes for audio editing and processing.

The API aims to be similar to pydub.AudioSegement (https://github.com/jiaaro/pydub),
except that audio segments are backed by NumPy arrays for ease of use with soundfile/librosa.
"""

import dataclasses
import pathlib
from typing import IO, Iterator, Literal, Self

import numpy as np
import soundfile


@dataclasses.dataclass
class Segment:
    """An array of audio samples.

    Attributes:
        array: A vector or matrix of audio samples in float64.
            They represent mono or stereo audio respectively.
        srate: The number of audio samples per second.
    """

    array: np.ndarray
    srate: int

    @property
    def channels(self) -> int:
        return len(self.array.shape)

    def set_channels(self, channels: Literal[1, 2]) -> Self:
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

    def milliseconds(self, samples: int) -> float:
        """Convert a count of audio samples to milliseconds.

        Args:
            samples: The audio sample count.

        Returns:
            The audio sample count as a duration in milliseconds.
        """

        return samples / self.srate * 1000

    def samples(self, ms: float) -> int:
        """Convert a duration in milliseconds to a count of audio samples.

        Args:
            ms: The duration in milliseconds.

        Returns:
            The duration as an audio sample count.
        """

        return int(ms / 1000 * self.srate)

    def _spawn(self, array: np.ndarray | None = None, srate: int | None = None) -> Self:
        if array is None:
            array = self.array

        if srate is None:
            srate = self.srate

        return Segment(array, srate)

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

    def __len__(self) -> int:
        return round(self.milliseconds(len(self.array)))

    def __getitem__(self, ms: float | slice) -> Self | Iterator[Self]:
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
