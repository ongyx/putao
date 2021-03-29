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
def project():
    """Project (song) management."""


def _p_new(name):
    click.echo(f"Creating new project '{name}'.")

    author = click.prompt("Author of project (your name)")

    voicebank = click.prompt("Path to UTAU voicebank")

    resampler = click.prompt(
        "Choose a resampler to use",
        type=click.Choice(list(model.RESAMPLERS)),
        default="WorldResampler",
    )

    click.echo(f"Sucessfully created project '{name}'.")

    return {
        "name": name,
        "author": author,
        "voicebank": voicebank,
        "resampler": resampler,
        "putao_version": __version__,
    }


@project.command("new")
@click.argument("name")
@click.option(
    "-o", "--output", help="where to save new project (defaults to curdir/(name).json)"
)
def p_new(name, output):
    """Create a new project through an interactive wizard."""

    config = _p_new(name)
    config_path = output or pathlib.Path(".") / f"{name}.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


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
    """Import an external file into a new project."""

    file = pathlib.Path(file)

    if not fmt:
        # guess format using file extension
        fmt = file.suffix[1:]

    if not output:
        output = file.with_suffix(".json")

    config = _p_new(file.stem)

    with file.open("rb") as f:
        config["tracks"] = backend.load(f, fmt)

    with output.open("w") as f:
        json.dump(config, f, indent=4)


@project.command("render")
@click.argument("proj_file")
@click.option("-o", "--output", default="render.wav", help="file to render to")
@click.option(
    "-f", "--frq", is_flag=True, help="regenerate frq files for the voicebank"
)
def p_render(proj_file, output, frq):
    """Render a project file."""

    proj = core.Project.load(proj_file)

    if "frq" not in proj.config or frq:
        click.echo(
            f"generating frq files using {proj.resampler.__class__.__name__}, this might take a while..."
        )
        proj.resampler.gen_frq_all(force=True)
        proj.config["frq"] = True

    proj.render(output)
    proj.dump(proj_file)
