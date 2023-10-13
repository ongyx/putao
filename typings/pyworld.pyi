from numpy import float64
from numpy.typing import NDArray


def synthesize(
    f0: NDArray[float64],
    spectrogram: NDArray[float64],
    aperiodicity: NDArray[float64],
    fs: int,
    frame_period: float = ...,
):
    ...


def wav2world(
    x: NDArray[float64],
    fs: int,
    fft_size: int | None = ...,
    frame_period: float = ...,
) -> tuple[NDArray[float64], NDArray[float64], NDArray[float64]]:
    ...
