import dataclasses
import io
import struct
from typing import Any, BinaryIO, Self

import numpy as np

_MAGIC = b"FREQ0003"
_AVERAGE_WINDOW = 6


class Value(struct.Struct):
    """A struct consisting of a single value."""

    def read(self, file: BinaryIO) -> Any:
        """Unpack a value from a file.

        Args:
            file: The file to unpack from.

        Returns:
            The unpacked value.
        """

        return self.unpack(file.read(self.size))[0]

    def write(self, file: BinaryIO, value: Any):
        """Pack a value into a file.

        Args:
            file: The file to write the packed value to.
            value: The value to pack.
        """

        file.write(self.pack(value))


_Int32 = Value("<i")
_Float64 = Value("<d")

_Frame = np.dtype([("frequency", "<f8"), ("amplitude", "<f8")])


@dataclasses.dataclass
class Frq:
    """A frequency map of a voice sample.
    Frequency maps are binary files that store the fundamental frequency (F0) and amplitude of voice samples in order to pitch them to a note.

    Their format is as follows:

    # Frq

    | Section  | Offset |
    | -------- | ------ |
    | Header   | 0      |
    | Frame(s) | 40     |

    # Header (40 bytes)

    | Section           | Offset | Value    |
    | ----------------- | ------ | -------- |
    | Magic             | 0      | FREQ0003 |
    | Samples per frame | 8      | int32    |
    | Average F0        | 12     | float64  |
    | Padding           | 20     | (null)   |
    | Number of frames  | 36     | int32    |

    # Frame (16 bytes)

    | Section   | Offset | Value   |
    | --------- | ------ | ------- |
    | F0        | 0      | float64 |
    | Amplitude | 8      | float64 |
    ```

    All values in a frequency map are little-endian.

    Atrributes:
        samples: The number of WAV samples per F0 frame, usually 256 by default.
        average: The average F0 in hertz.
        frames: The F0 frames computed over the entire voice sample, consisting of a frequency and amplitude.
    """

    samples: int
    average: float
    frames: np.ndarray

    @property
    def frame_average(self) -> float:
        """The F0 average over the current frames."""

        kernel = np.ones(_AVERAGE_WINDOW) / _AVERAGE_WINDOW

        return np.convolve(self.frames["frequency"], kernel, mode="valid").mean()


def dump(frq: Frq, file: BinaryIO):
    """Dump the freqeuncy map to a binary file.

    Args:
        file: The binary file to dump to.
    """

    file.write(_MAGIC)

    _Int32.write(file, frq.samples)
    _Float64.write(file, frq.average)

    file.write(bytes([0] * 16))

    _Int32.write(file, len(frq.frames))

    # Numpy's tofile requires a *real* file with a descriptor, so we have to write the bytes directly.
    file.write(frq.frames.tobytes())


def dumps(frq: Frq) -> bytes:
    """Dump the frequency map to a byte string.

    Returns:
        The frequency map as a byte string.
    """

    with io.BytesIO() as b:
        dump(frq, b)
        return b.getvalue()


def load(file: BinaryIO) -> Frq:
    """Load a frequency map from a binary file.

    Args:
        file: The binary file to load from.
            Files must start with "FREQ0003" in ASCII.

    Returns:
        The frequency map.
    """

    # Match the magic numbar.
    if file.read(len(_MAGIC)) != _MAGIC:
        raise ValueError("invalid frq file")

    samples = _Int32.read(file)
    average = _Float64.read(file)

    # Empty padding.
    file.read(16)

    frames_len = _Int32.read(file)

    # Numpy's {to,from}file requires a *real* file with a descriptor, so we have to use a buffer.
    buffer = file.read(frames_len * _Frame.itemsize)

    frames = np.frombuffer(buffer, dtype=_Frame, count=frames_len)

    return Frq(samples, average, frames)


def loads(data: bytes) -> Frq:
    """Load a frequency map from a byte string.

    Args:
        data: The byte string to load from.

    Returns:
        The frequency map.
    """

    with io.BytesIO(data) as b:
        return load(b)
