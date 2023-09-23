import logging
from typing import Annotated

import rich.progress
import typer

from .. import oto

LOG_LEVELS = [
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
]

app = typer.Typer(no_args_is_help=True)


@app.callback()
def common(
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose", "-v", count=True, min=0, max=5, help="set logging level"
        ),
    ] = 0
):
    """Concatenative synthesizer inspired by and compatible with UTAU."""

    if verbose == 0:
        logging.disable()
    else:
        logging.basicConfig(level=LOG_LEVELS[verbose - 1])
