"""agentic-stacks list — show stacks in the current project."""

import pathlib

import click

from agentic_stacks_cli.lock import read_lock


@click.command("list")
@click.option("--path", "target_dir", default=".", type=click.Path(), help="Project directory")
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
        version = entry.get("version", "")
        short_name = name.split("/")[-1]
        pulled = (stacks_dir / short_name / ".git").is_dir()
        status = "pulled" if pulled else "not pulled"
        version_str = f"@{version}" if version else ""
        click.echo(f"  {name}{version_str}  ({status})")
