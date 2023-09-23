from . import main, voicebank

main.app.add_typer(voicebank.app, name="voicebank")
