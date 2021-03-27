# coding: utf8
"""葡萄 (putao, grape): Poor man's UTAU."""

import logging

from putao.__version__ import __version__  # noqa: W0611

logging.getLogger("sox").setLevel(logging.ERROR)

del logging
