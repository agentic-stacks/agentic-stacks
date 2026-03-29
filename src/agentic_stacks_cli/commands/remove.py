"""agentic-stacks remove — remove a stack from the current project."""

import pathlib
import shutil

import click

from agentic_stacks_cli.lock import read_lock, write_lock, remove_from_lock


@click.command()
@click.argument("reference")
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
def remove(reference: str, target_dir: str):
    """Remove a stack from the current project.

    REFERENCE is the stack name (e.g., openstack-kolla or agentic-stacks/openstack-kolla).
    """
    target = pathlib.Path(target_dir)
    lock_path = target / "stacks.lock"
    lock = read_lock(lock_path)

    # Match by full name or short name
    matched = None
    for entry in lock.get("stacks", []):
        if entry["name"] == reference or entry["name"].split("/")[-1] == reference:
            matched = entry["name"]
            break

    if not matched:
        raise click.ClickException(f"Stack '{reference}' not found in stacks.lock")

    short_name = matched.split("/")[-1]
    stack_path = target / ".stacks" / short_name

    # Remove from lock
    lock = remove_from_lock(lock, matched)
    write_lock(lock, lock_path)
    click.echo(f"Removed {matched} from stacks.lock")

    # Remove pulled directory if present
    if stack_path.is_dir():
        shutil.rmtree(stack_path)
        click.echo(f"Deleted .stacks/{short_name}/")
