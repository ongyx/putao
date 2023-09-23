import dataclasses
import pathlib
import textwrap
import zipfile
from typing import Annotated, Optional

import typer
from rich.progress import Progress
from rich.table import Table

from .. import oto

from .console import console

app = typer.Typer(no_args_is_help=True, help="View and manage voicebanks")


@app.command()
def extract(
    file: Annotated[
        pathlib.Path, typer.Argument(exists=True, dir_okay=False, resolve_path=True)
    ],
    dir: Annotated[
        pathlib.Path, typer.Argument(exists=True, file_okay=False, resolve_path=True)
    ] = pathlib.Path(),
):
    """Extract a ZIP file to a directory as UTF-8."""

    if not zipfile.is_zipfile(file):
        raise ValueError("File is not a ZIP file!")

    with Progress() as p:
        oto.extract_zip(file, dir, progress=p)


@app.command()
def info(
    dir: Annotated[
        pathlib.Path, typer.Argument(exists=True, file_okay=False, resolve_path=True)
    ] = pathlib.Path(),
    alias: Annotated[Optional[str], typer.Argument()] = None,
    frq: Annotated[bool, typer.Option(help="Display frequency maps")] = False,
):
    """Show information on a voicebank directory.
    If alias is given, only the corresponding sample is shown.
    """

    vb = oto.Voicebank(dir)

    console.print(
        textwrap.dedent(
            f"""
            {dir}          
            encoding: {vb.encoding}
            samples: {len(vb)}
            files: {len(set(s.file for s in vb))}
            """
        )
    )

    table = Table()
    for field in dataclasses.fields(oto.Sample):
        table.add_column(field.name.capitalize())

    if frq:
        table.add_column("F0 average")
        table.add_column("Note")

    samples = vb if alias is None else [vb[alias]]

    for sample in samples:
        values = [str(v) for v in dataclasses.astuple(sample)]

        if frq:
            # Attempt to read F0 value.
            try:
                with vb.path_to_frq(sample).open("rb") as f:
                    fmap = oto.Frq.load(f)
            except FileNotFoundError:
                values.extend(["-", "-"])
            else:
                f0 = fmap.average
                values.extend([f"{f0:.2f}Hz", str(oto.Pitch(f0).midi)])

        table.add_row(*values)

    console.print(table)
