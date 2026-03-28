"""agentic-stacks search — find stacks in the registry."""

import pathlib
import click
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.argument("query")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def search(query: str, config_path: str | None):
    """Search for stacks in the registry."""
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    client = RegistryClient(api_url=api_url, token=cfg.get("token"))
    try:
        results = client.search(query)
    except Exception as e:
        raise click.ClickException(f"Search failed: {e}")
    if not results:
        click.echo(f"No stacks found for '{query}'.")
        return
    click.echo(f"Found {len(results)} stack(s):\n")
    for stack in results:
        ns = stack.get("namespace", "")
        name = stack.get("name", "")
        version = stack.get("version", "")
        desc = stack.get("description", "")
        click.echo(f"  {ns}/{name}@{version}")
        if desc:
            click.echo(f"    {desc}")
        click.echo()
