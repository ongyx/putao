# coding: utf8

import functools
import json
import logging
import pathlib
import shutil
import tempfile

import click

from . import core, backend, model, utau
from .__version__ import __version__

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


@cli.group()
def resampler():
    """List/configure resamplers."""


@resampler.command("frq")
@click.argument("name")
@click.option("-p", "--path", default=".", help="path to the voicebank")
@click.option("-f", "--force", default=False, is_flag=True, help="ignore existing frqs")
def r_frq(name, path, force):
    """Generate frequency files for a UTAU voicebank using resampler by name."""

    voicebank = utau.Voicebank(path)
    resampler = model.RESAMPLERS[name](voicebank)
    resampler.gen_frq(force=force)


@cli.group()
def project():
    """Project (song) management."""


@project.command("import")
@click.argument("file")
@click.option(
    "-f",
    "--fmt",
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


@project.command("render")
@click.argument("proj_file")
@click.option("-o", "--output", default="render.wav", help="file to render to")
@click.option("-v", "--voicebank", default=".", help="path to the voicebank")
def p_render(proj_file, output, voicebank):
    """Render a project file."""

    proj = core.Project(voicebank)

    proj.fload(proj_file)

    proj.render(output)
