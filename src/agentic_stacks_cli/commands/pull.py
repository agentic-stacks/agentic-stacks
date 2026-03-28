"""agentic-stacks pull — download a stack from the registry."""

import pathlib
import re

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.oci import pull_stack
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.api_client import RegistryClient


def _parse_ref(ref: str) -> tuple[str, str, str | None]:
    match = re.match(r"^([^/]+)/([^@]+)(?:@(.+))?$", ref)
    if not match:
        raise ValueError(f"Invalid reference: '{ref}'. Expected format: namespace/name or namespace/name@version")
    return match.group(1), match.group(2), match.group(3)


@click.command()
@click.argument("reference", required=False)
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def pull(reference: str | None, target_dir: str, config_path: str | None):
    """Pull a stack from the registry."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    registry = cfg.get("registry", "ghcr.io")
    lock_path = target / "stacks.lock"

    if not reference:
        lock = read_lock(lock_path)
        if not lock["stacks"]:
            raise click.ClickException("No stacks.lock found or it's empty.")
        for entry in lock["stacks"]:
            ns, name = entry["name"].split("/", 1)
            version = entry["version"]
            stacks_dir = target / ".stacks" / ns / name / version
            click.echo(f"Pulling {entry['name']}@{version}...")
            pull_stack(registry=registry, namespace=ns, name=name, version=version, output_dir=stacks_dir)
        click.echo("All stacks restored from lock file.")
        return

    try:
        namespace, name, version = _parse_ref(reference)
    except ValueError as e:
        raise click.ClickException(str(e))

    client = RegistryClient(api_url=api_url, token=cfg.get("token"))
    try:
        stack_info = client.get_stack(namespace, name, version=version)
        version = stack_info.get("version", version)
        registry_ref = stack_info.get("registry_ref", f"{registry}/{namespace}/{name}:{version}")
    except Exception:
        if not version:
            raise click.ClickException("Version required when registry API is unavailable.")
        registry_ref = f"{registry}/{namespace}/{name}:{version}"

    stacks_dir = target / ".stacks" / namespace / name / version
    click.echo(f"Pulling {namespace}/{name}@{version}...")
    digest = pull_stack(registry=registry, namespace=namespace, name=name,
                        version=version, output_dir=stacks_dir)
    click.echo(f"  Extracted to {stacks_dir}")

    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=f"{namespace}/{name}", version=version,
                       digest=digest, registry=registry_ref)
    write_lock(lock, lock_path)
    click.echo(f"  Updated stacks.lock")
    click.echo(f"\nPulled {namespace}/{name}@{version}")
