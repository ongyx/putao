# coding: utf8

import sys

from putao.core import Voicebank


if len(sys.argv) < 2:
    print("usage: create_voicebank.py <folder>")
    sys.exit(1)


voicebank_path = sys.argv[1]


voicebank = Voicebank(voicebank_path, create=True)
