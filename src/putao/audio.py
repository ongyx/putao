"""Classes for audio editing and processing.

The API aims to be similar to pydub.AudioSegement (https://github.com/jiaaro/pydub),
except that audio segments are backed by NumPy arrays for ease of use with soundfile/librosa.
"""

import dataclasses
import pathlib
from typing import IO, Iterator, Self

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

    @classmethod
    def from_file(cls, file: str | pathlib.Path | IO[bytes]) -> Self:
        """Read an audio file into a segment.

        Args:
            file: The path-like or file-like object to read samples from.

        Returns:
            The audio segment.
        """
        return cls(*soundfile.read(file, dtype="float64"))

    def __len__(self) -> int:
        return round(self.milliseconds(len(self.array)))

    def __getitem__(self, ms: float | slice) -> Self | Iterator[Self]:
        if isinstance(ms, slice):
            if ms.step is not None:
                # Split the audio sample into chunks.
                return (
                    Segment(a, self.srate)
                    for a in np.hsplit(self.array, self.samples(ms.step))
                )

            start = self.samples(ms.start or 0)
            stop = self.samples(ms.stop or len(self.array))

            return Segment(self.array[start:stop], self.srate)

        # Return 1 millisecond of audio.
        return self[ms : ms + 1]
