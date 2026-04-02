"""agentic-stacks search — find stacks in the registry."""

import pathlib

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import ensure_registry, search_formulas


@click.command()
@click.argument("query")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def search(query: str, config_path: str | None):
    """Search for stacks in the registry."""
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    repo_url = cfg.get("registry_repo", "https://github.com/agentic-stacks/registry")

    try:
        registry_path = ensure_registry(repo_url=repo_url)
    except Exception as e:
        raise click.ClickException(f"Could not update registry: {e}")

    results = search_formulas(registry_path, query)

    if not results:
        click.echo(f"No stacks found for '{query}'.")
        return

    click.echo(f"Found {len(results)} stack(s):\n")
    for formula in results:
        owner = formula.get("owner", "")
        name = formula.get("name", "")
        version = formula.get("version", "")
        desc = formula.get("description", "").strip()
        click.echo(f"  {owner}/{name}@{version}")
        if desc:
            click.echo(f"    {desc}")
        click.echo()
