import pathlib
import pytest
from putao.oto.sample import Sample

from putao.oto.voicebank import Voicebank, CONFIG_FILE

VOWELS = ["あ", "え", "い", "お", "う"]
ENCODINGS = ["shift_jis", "utf_8"]


@pytest.fixture(scope="session", params=ENCODINGS)
def voicebank(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> pathlib.Path:
    encoding = request.param

    dir = tmp_path_factory.mktemp(f"vb_{encoding}")

    # Output oto.ini in the encoding.
    with (dir / CONFIG_FILE).open("w", encoding=encoding) as f:
        for vowel in VOWELS:
            print(f"{vowel}.wav={vowel},1,2,3,4,5", file=f)

            # Mojibake vowel on purpose.
            if encoding != "utf_8":
                vowel = vowel.encode(encoding).decode("cp437")

            # Create an empty sample file for each vowel.
            (dir / vowel).with_suffix(".wav").touch()

    return dir


def test_voicebank(voicebank: pathlib.Path):
    vb = Voicebank(voicebank)

    assert vb.samples == {v: Sample(f"{v}.wav", v, 1, 2, 3, 4, 5) for v in VOWELS}

    for sample in vb.samples.values():
        assert vb.path_to(sample).exists()
