"""agentic-stacks login — authenticate with the registry."""

import click
from agentic_stacks_cli.config import load_config, save_config


@click.command()
@click.option("--token", default=None, help="GitHub personal access token")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def login(token: str | None, config_path: str | None):
    """Authenticate with the Agentic Stacks registry."""
    from pathlib import Path
    cfg_path = Path(config_path) if config_path else None
    if not token:
        token = click.prompt("GitHub personal access token", hide_input=True)
    cfg = load_config(cfg_path)
    cfg["token"] = token
    save_config(cfg, cfg_path)
    click.echo("Logged in. Token saved.")
