# coding: utf8
"""葡萄 (putao, grape): Poor man's UTAU."""

__version__ = "0.0.3a0"

import logging

# from putao.core import Project  # noqa: W0611

logging.getLogger("sox").setLevel(logging.ERROR)
logging.basicConfig(level=logging.DEBUG)
