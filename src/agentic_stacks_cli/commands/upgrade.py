"""agentic-stacks upgrade — upgrade a stack to the latest version."""

import pathlib
import click
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.oci import pull_stack
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.argument("name")
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def upgrade(name: str, target_dir: str, config_path: str | None):
    """Upgrade a stack to the latest version."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    registry = cfg.get("registry", "ghcr.io")

    lock_path = target / "stacks.lock"
    lock = read_lock(lock_path)

    current = None
    for entry in lock["stacks"]:
        entry_name = entry["name"].split("/")[-1]
        if entry_name == name or entry["name"] == name:
            current = entry
            break

    if not current:
        raise click.ClickException(f"Stack '{name}' not found in stacks.lock. Pull it first.")

    full_name = current["name"]
    namespace, stack_name = full_name.split("/", 1)
    current_version = current["version"]

    click.echo(f"Checking for updates to {full_name} (current: {current_version})...")

    client = RegistryClient(api_url=api_url, token=cfg.get("token"))
    try:
        latest = client.get_stack(namespace, stack_name)
    except Exception as e:
        raise click.ClickException(f"Could not check for updates: {e}")

    latest_version = latest.get("version", current_version)
    if latest_version == current_version:
        click.echo(f"Already up to date ({current_version}).")
        return

    click.echo(f"  New version available: {current_version} -> {latest_version}")

    deprecations = latest.get("deprecations", [])
    if deprecations:
        click.echo(f"\n  Deprecations in {latest_version}:")
        for dep in deprecations:
            click.echo(f"    - {dep['skill']}: use '{dep['replacement']}' instead ({dep['reason']})")

    stacks_dir = target / ".stacks" / namespace / stack_name / latest_version
    click.echo(f"\n  Pulling {full_name}@{latest_version}...")
    digest = pull_stack(registry=registry, namespace=namespace, name=stack_name,
                        version=latest_version, output_dir=stacks_dir)

    registry_ref = latest.get("registry_ref", f"{registry}/{namespace}/{stack_name}:{latest_version}")
    lock = add_to_lock(lock, name=full_name, version=latest_version, digest=digest, registry=registry_ref)
    write_lock(lock, lock_path)

    click.echo(f"\nUpgraded {full_name}: {current_version} -> {latest_version}")
