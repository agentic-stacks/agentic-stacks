"""agentic-stacks list — show stacks in the current project."""

import pathlib

import click

from agentic_stacks_cli.lock import read_lock


@click.command("list")
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
def list_stacks(target_dir: str):
    """List stacks in the current project."""
    target = pathlib.Path(target_dir)
    lock = read_lock(target / "stacks.lock")
    stacks = lock.get("stacks", [])

    if not stacks:
        click.echo("No stacks in this project. Use 'agentic-stacks pull <stack>' to add one.")
        return

    click.echo(f"Stacks ({len(stacks)}):\n")
    stacks_dir = target / ".stacks"
    for entry in stacks:
        name = entry["name"]
        short_name = name.split("/")[-1]
        pulled = (stacks_dir / short_name / ".git").is_dir()
        status = "pulled" if pulled else "not pulled"
        click.echo(f"  {name}  ({status})")
