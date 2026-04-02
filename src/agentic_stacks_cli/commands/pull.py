"""agentic-stacks pull — download a stack into .stacks/."""

import pathlib
import re
import subprocess

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.registry_repo import ensure_registry, load_formula


DEFAULT_ORG = "agentic-stacks"
GITHUB_BASE = "https://github.com"


def _parse_ref(ref: str) -> tuple[str, str]:
    """Parse 'name' or 'namespace/name' into (namespace, name)."""
    if "/" in ref:
        parts = ref.split("/", 1)
        return parts[0], parts[1]
    return DEFAULT_ORG, ref


def _clone_or_pull(repo_url: str, dest: pathlib.Path) -> None:
    """Clone a repo, or pull if already cloned."""
    if (dest / ".git").is_dir():
        click.echo(f"  Updating {dest}...")
        result = subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise click.ClickException(f"git pull failed: {result.stderr.strip()}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        click.echo(f"  Cloning {repo_url}...")
        result = subprocess.run(
            ["git", "clone", repo_url, str(dest)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise click.ClickException(f"git clone failed: {result.stderr.strip()}")


@click.command()
@click.argument("reference", required=False)
@click.option("--path", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def pull(reference: str | None, target_dir: str, config_path: str | None):
    """Pull a stack into .stacks/."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    lock_path = target / "stacks.lock"

    if not reference:
        # Pull all stacks from lock file
        lock = read_lock(lock_path)
        if not lock["stacks"]:
            raise click.ClickException("No stacks.lock found or it's empty.")
        for entry in lock["stacks"]:
            repo_url = entry.get("repository", "")
            name = entry["name"].split("/")[-1]
            dest = target / ".stacks" / name
            click.echo(f"Pulling {entry['name']}...")
            _clone_or_pull(repo_url, dest)
        click.echo("All stacks pulled.")
        return

    namespace, name = _parse_ref(reference)

    # Try to resolve from registry formula
    repo_url = None
    formula = None
    try:
        registry_path = ensure_registry(
            repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
        )
        formula = load_formula(registry_path, namespace, name)
        repo_url = formula["repository"]
    except (FileNotFoundError, Exception):
        pass

    # Fall back to GitHub URL convention
    if not repo_url:
        repo_url = f"{GITHUB_BASE}/{namespace}/{name}"

    dest = target / ".stacks" / name

    click.echo(f"Pulling {namespace}/{name}...")
    _clone_or_pull(repo_url, dest)
    click.echo(f"  → .stacks/{name}/")

    # Record version from formula and commit SHA from cloned repo
    version = formula.get("version", "latest") if formula else "latest"
    commit_sha = ""
    if (dest / ".git").is_dir():
        result = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            commit_sha = result.stdout.strip()

    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=f"{namespace}/{name}", version=version,
                       digest=commit_sha, registry=repo_url)
    for entry in lock["stacks"]:
        if entry["name"] == f"{namespace}/{name}":
            entry["repository"] = repo_url
    write_lock(lock, lock_path)
    click.echo(f"  Updated stacks.lock ({version} @ {commit_sha[:7]})")
