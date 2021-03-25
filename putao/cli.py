# coding: utf8

import functools
import json
import logging
import pathlib
import shutil
import tempfile

import click

from putao import core, backend, utau
from putao.__version__ import __version__

click.option = functools.partial(click.option, show_default=True)  # type: ignore


@click.group()
@click.version_option(__version__)
def cli():
    logging.basicConfig(level=logging.DEBUG)


@cli.group()
def voicebank():
    """Voicebank-related utils."""


@voicebank.command("extract")
@click.argument("zfile")
@click.option("-t", "--target", default=".", help="where to extract the voicebank to")
def v_extract(zfile, target):
    """Extract the voicebank(s) in zfile."""

    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = pathlib.Path(_tempdir)

        # extract to tempdir first
        utau.extract(zfile, tempdir)

        # find all folders with an oto.ini file
        voicebanks = [p.parent for p in tempdir.rglob(utau.CONFIG_FILE)]
        for count, voicebank in enumerate(voicebanks):
            print(f"{count}: {voicebank.name}")

        choice = click.prompt("Voicebank to use", 0)
        voicebank_to_move = voicebanks[choice]

        for path in voicebank_to_move.iterdir():
            shutil.move(path, target)

    print("done")


@voicebank.command("frq")
@click.argument("path")
@click.option("-f", "--force", default=False, is_flag=True, help="ignore existing frqs")
def v_frq(path, force):
    """Generate frequency files for a UTAU voicebank at path."""

    # pitch will not be used anyway.
    voicebank = utau.Voicebank(path, 0)
    voicebank.generate_frq(force=force)


# @voicebank.command("init")
# @click.argument("path")
# @click.option("-k", "--key", type=int, help="voicebank key (i.e C4, D#4, etc.)")
# def v_init(path):
#    """Initalise an existing UTAU voicebank at path for use in putao."""


@cli.group()
def project():
    """Project (song) management."""


@project.command("import")
@click.argument("file")
@click.option(
    "-f",
    "--fmt",
    default="",
    type=click.Choice(backend.BACKENDS),
    help="external file format",
)
@click.option("-o", "--output", default="", help="where to save the project")
def p_import(file, fmt, output):
    """Import an external file into a project."""

    file = pathlib.Path(file)

    if not fmt:
        # guess format using file extension
        fmt = file.suffix[1:]

    with file.open("rb") as f:
        proj_data = backend.load(f, fmt)

    if not output:
        output = file.with_suffix(".json")

    with open(output, "w") as f:
        json.dump(proj_data, f, indent=4)


# @project.command("render")
# @click.argument("proj_file")
# @click.option("-o", "--output", default="render.wav", help="file to render to")
# def p_render(proj_file, output):
#    """Render a project file."""
