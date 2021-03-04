# coding: utf8

import json
import pathlib
import sys

voicebank = {"syllables": {}}

if len(sys.argv) < 3:
    print("usage: create_voicebank.py <folder> <pitch in scientific music notation>")
    sys.exit(1)


voicebank_path = pathlib.Path(sys.argv[1])
voicebank_tone = sys.argv[2]

for wavfile in voicebank_path.glob("*.wav"):
    voicebank["syllables"][wavfile.stem] = voicebank_tone

with (voicebank_path / "voicebank.json").open("w") as f:
    json.dump(voicebank, f, indent=4)
