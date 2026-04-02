"""agentic-stacks update — update stacks to latest versions."""

import pathlib
import subprocess

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.registry_repo import ensure_registry, load_formula


def _get_local_sha(dest: pathlib.Path) -> str:
    """Get the current HEAD SHA of a cloned stack."""
    if not (dest / ".git").is_dir():
        return ""
    result = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _get_remote_sha(dest: pathlib.Path) -> str:
    """Fetch and return the remote HEAD SHA without pulling."""
    if not (dest / ".git").is_dir():
        return ""
    subprocess.run(
        ["git", "-C", str(dest), "fetch", "--quiet"],
        capture_output=True, text=True,
    )
    result = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "origin/main"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


@click.command()
@click.argument("name", required=False)
@click.option("--path", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
@click.option("--check", is_flag=True, help="Check for updates without applying them")
def update(name: str | None, target_dir: str, config_path: str | None, check: bool):
    """Update stacks to latest versions."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    lock_path = target / "stacks.lock"
    lock = read_lock(lock_path)

    if not lock["stacks"]:
        raise click.ClickException("No stacks in stacks.lock.")

    # Get registry for version info
    try:
        registry_path = ensure_registry(
            repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
        )
    except Exception:
        registry_path = None

    entries = lock["stacks"]
    if name:
        entries = [e for e in entries if e["name"].endswith(f"/{name}") or e["name"] == name]
        if not entries:
            raise click.ClickException(f"Stack '{name}' not found in stacks.lock.")

    updated = 0
    for entry in entries:
        stack_name = entry["name"].split("/")[-1]
        namespace = entry["name"].split("/")[0] if "/" in entry["name"] else "agentic-stacks"
        dest = target / ".stacks" / stack_name
        current_sha = entry.get("digest", "")
        current_version = entry.get("version", "?")

        if not (dest / ".git").is_dir():
            click.echo(f"  {entry['name']}: not cloned, run 'pull' first")
            continue

        remote_sha = _get_remote_sha(dest)
        if not remote_sha:
            click.echo(f"  {entry['name']}: could not check remote")
            continue

        # Get formula version for display
        formula_version = current_version
        if registry_path:
            try:
                formula = load_formula(registry_path, namespace, stack_name)
                if formula:
                    formula_version = formula.get("version", current_version)
            except Exception:
                pass

        if current_sha and remote_sha == current_sha:
            click.echo(f"  {entry['name']}: up to date ({current_version})")
            continue

        if check:
            click.echo(f"  {entry['name']}: update available ({current_version} → {formula_version})")
            continue

        # Pull the update
        click.echo(f"  {entry['name']}: updating...")
        result = subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            click.echo(f"    git pull failed: {result.stderr.strip()}")
            continue

        new_sha = _get_local_sha(dest)
        lock = add_to_lock(lock, name=entry["name"], version=formula_version,
                           digest=new_sha, registry=entry.get("registry", ""))
        for e in lock["stacks"]:
            if e["name"] == entry["name"]:
                e["repository"] = entry.get("repository", "")
        updated += 1
        click.echo(f"    updated to {formula_version} ({new_sha[:7]})")

    if not check and updated > 0:
        write_lock(lock, lock_path)
        click.echo(f"\nUpdated {updated} stack(s).")
    elif not check:
        click.echo("\nAll stacks up to date.")
