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
from numpy.typing import NDArray


def db_to_amp(db: float) -> float:
    """Calculate the amplitude factor from a decibel value.

    Args:
        db: The decibel value.

    Returns:
        The amplitude factor.
    """

    return 10 ** (db / 20)


@dataclasses.dataclass(slots=True)
class Segment:
    """An array of audio samples.

    Attributes:
        array: A vector or matrix of audio samples in float64.
            They represent mono or stereo audio respectively.
        srate: The number of audio samples per second.
    """

    array: NDArray[np.float64]
    srate: int

    def __post_init__(self):
        # Check if the array is a view or copy.
        # Copies are always made immutable, whereas views inherit their mutability from their base copy or view.
        if self.array.base is None:
            # Make the array a view of itself so the original is left untouched.
            self.array = self.array[:]
            self.mut = False

    @property
    def mut(self) -> bool:
        """Whether or not the audio segment's array is mutable.

        Regardless of this, all segment operations return a copy of the array.
        """

        return self.array.flags.writeable

    @mut.setter
    def mut(self, value: bool):
        self.array.flags.writeable = value

    @property
    def channels(self) -> int:
        """The number of channels in the audio segment.

        Typically, audio segments only have 1 (mono) or 2 (stereo) channels.
        """

        return len(self.array.shape)

    def overlay(self, segment: Self, position: float = 0, times: int = -1) -> Self:
        """Overlay an audio segment.

        Args:
            position: Where to start overlaying from.
            times: How many times to loop the segment.
                If less than 0, the segment is looped over the entire base segment.

        Returns:
            The overlaid base segment.
        """

        with self.spawn().mutable() as base:
            size = len(segment)

            # Begin overlap from position onwards.
            chunk: Self
            for chunk in base[position::size]:
                if times == 0:
                    break

                seg = segment.array

                # Slice the segment down to the chunk's size if it is larger.
                if len(chunk) < size:
                    seg = seg[: len(chunk.array)]

                chunk.array[:] = np.mean(np.array([chunk.array, seg]), axis=0)

                times -= 1

            return base

    def append(self, segment: Self, crossfade: float = 100) -> Self:
        """Append an audio segment.

        Args:
            segment: The segment to append.
            crossfade: Length in milliseconds to crossfade the original and appended segment.
                Defaults to 0.1ms.

        Returns:
            The new segment.

        Raises:
            ValueError: crossfade is longer than the original or appended segment.
        """

        if not crossfade:
            # One segment after the other.
            return self.spawn(np.concatenate([self.array, segment.array], axis=0))

        self_len = len(self)
        seg_len = len(segment)
        if crossfade > self_len or crossfade > seg_len:
            raise ValueError(
                f"crossfade is longer than self or segment (crossfade={crossfade}ms, self={self_len}ms, segment={seg_len}ms)"
            )

        # Fade the crossfade region and take the mean to overlay them.
        faded = np.mean(
            np.array(
                [
                    self[-crossfade:].fade(to_gain=-120),
                    segment[:crossfade].fade(from_gain=-120),
                ]
            )
        )

        # Concatenate the other regions with the crossfade.
        return self.spawn(
            np.concatenate([self[:-crossfade].array, faded, segment[crossfade:].array])
        )

    def apply_gain(self, db: float) -> Self:
        """Apply a uniform gain.

        Args:
            db: The gain in decibels.

        Returns:
            A copy of the audio segment with the gain applied.
        """

        return self.spawn(self.array * db_to_amp(db))

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
                return self.spawn(self.array.mean(axis=0))
            case 1, 2:
                # Mono to stereo.
                return self.spawn(np.tile(self.array, (2, 1)))
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
            to_gain: Final gain in dbFS.
            from_gain: Initial gain in dbFS.
            start: Where the fade should start.
            end: Where the fade should end.

        Returns:
            A copy of the audio segment with the fade applied.

        Raises:
            ValueError: to_gain or from_gain are above 0.
        """

        if to_gain == 0 and from_gain == 0:
            return self

        if to_gain > 0 or from_gain > 0:
            raise ValueError(
                f"dbFS cannot be above 0 (to_gain={to_gain}, from_gain={from_gain})"
            )

        to_amp = db_to_amp(to_gain)
        from_amp = db_to_amp(from_gain)

        start = start or 0
        end = end or len(self)

        if not start < end:
            raise ValueError(
                f"start must be earlier than end (start={start}, end={end})"
            )

        with self.spawn().mutable() as segment:
            fade_arr = segment[start:end].array
            # Logarithmic fade curve.
            fade_arr *= np.logspace(from_amp, to_amp, num=len(fade_arr)) / 10

            return segment

    def export(self, file: str | pathlib.Path | BinaryIO, format: str = "WAV"):
        """Export an audio segment to a file.

        Args:
            file: The path-like or file-like object to export to.
            format: The format to export with.
                See soundfile.available_formats().
        """

        soundfile.write(file, self.array, self.srate, format=format)

    @contextlib.contextmanager
    def mutable(self) -> Iterator[Self]:
        """Create a context where the audio segment is temporarily mutable."""

        self.mut = True

        try:
            yield self
        finally:
            self.mut = False

    def spawn(
        self,
        array: NDArray[np.float64] | None = None,
        srate: int | None = None,
    ) -> Self:
        """Create a copy of the audio segment and its attributes.

        Args:
            array: The sample array.
                If None, a copy of the existing array is made.
            srate: The sample rate of the array.
                If None, the existing sample rate is used.

        Returns:
            The copied audio segment.
        """

        if array is None:
            # Create a copy of the underlying array.
            array = self.array.copy()

        if srate is None:
            srate = self.srate

        return Segment(array, srate)

    def samples(self, ms: float) -> int:
        """Convert a duration in milliseconds to a count of audio samples.

        Args:
            ms: The duration in milliseconds.

        Returns:
            The duration as an audio sample count.
        """

        return int(ms / 1000 * self.srate)

    def milliseconds(self, samples: int) -> float:
        """Convert a count of audio samples to milliseconds.

        Args:
            samples: The audio sample count.

        Returns:
            The audio sample count as a duration in milliseconds.
        """

        return samples / self.srate * 1000

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

    def __add__(self, segment_or_gain: Self | float) -> Self:
        if isinstance(segment_or_gain, Segment):
            return self.append(segment_or_gain, crossfade=0)

        return self.apply_gain(segment_or_gain)

    def __mul__(self, segment_or_repeat: Self | int) -> Self:
        if isinstance(segment_or_repeat, Segment):
            return self.overlay(segment_or_repeat)

        return self.spawn(np.repeat(self.array, segment_or_repeat, axis=0))

    def __getitem__(self, ms: float | slice) -> Any:
        if isinstance(ms, slice):
            if ms.step is not None:
                # Split the audio sample into chunks.
                chunk = self.samples(ms.step)
                chunks = range(chunk, self.array.shape[0], chunk)

                return (self.spawn(a) for a in np.array_split(self.array, chunks))

            start = self.samples(ms.start or 0)
            stop = self.samples(ms.stop or len(self.array))

            return self.spawn(self.array[start:stop])

        # Return 1 millisecond of audio.
        return self[ms : ms + 1]

    def __len__(self) -> int:
        return round(self.milliseconds(len(self.array)))
