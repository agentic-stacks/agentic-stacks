"""agentic-stacks init — scaffold an operator project."""

import pathlib
import subprocess

import click
import yaml

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.registry_repo import ensure_registry, load_formula
from agentic_stacks_cli.commands.pull import (
    _parse_ref,
    _clone_or_pull,
    _validate_repo_url,
    GITHUB_BASE,
)

COMMON_SKILLS_REF = "agentic-stacks/common-skills"


def _pull_common_skills(stack_dir: pathlib.Path) -> None:
    """Pull the common-skills stack into the project."""
    cfg = load_config()
    namespace, name = _parse_ref(COMMON_SKILLS_REF)

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

    dest = stack_dir / ".stacks" / name

    click.echo(f"Pulling {COMMON_SKILLS_REF}...")
    _validate_repo_url(repo_url)
    _clone_or_pull(repo_url, dest)
    click.echo(f"  → .stacks/{name}/")

    # Record version and commit SHA
    version = formula.get("version", "latest") if formula else "latest"
    commit_sha = ""
    if (dest / ".git").is_dir():
        result = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            commit_sha = result.stdout.strip()

    lock_path = stack_dir / "stacks.lock"
    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=COMMON_SKILLS_REF, version=version,
                       digest=commit_sha, registry=repo_url)
    for entry in lock["stacks"]:
        if entry["name"] == COMMON_SKILLS_REF:
            entry["repository"] = repo_url
    write_lock(lock, lock_path)
    click.echo(f"  Updated stacks.lock ({version} @ {commit_sha[:7]})")


def _init_operator_project(stack_dir: pathlib.Path):
    """Scaffold a project directory with stacks.lock, .gitignore, CLAUDE.md."""
    lock = {"stacks": []}
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    project_name = stack_dir.name
    claude_md = (
        f"# {project_name}\n\n"
        f"This project uses agentic stacks for domain expertise.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads all stacks to .stacks/\n"
        f"```\n\n"
        f"## Discover Stacks\n\n"
        f"```bash\n"
        f"agentic-stacks search \"keyword\"  # find stacks\n"
        f"agentic-stacks pull <name>        # add a stack to this project\n"
        f"```\n\n"
        f"## How This Works\n\n"
        f"Read each stack's CLAUDE.md for domain expertise:\n\n"
        f"```bash\n"
        f"ls .stacks/*/CLAUDE.md\n"
        f"```\n\n"
        f"Each stack knows how to deploy, configure, and operate its software. "
        f"Combine their expertise when stacks overlap (e.g., hardware + platform).\n\n"
        f"Work with the operator to build out their deployment. "
        f"Everything created here gets committed to this repo for reproducibility.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized project at {stack_dir}")


@click.command()
@click.argument("path", required=False, default=None, type=click.Path())
@click.option("--no-common", is_flag=True, default=False,
              help="Skip auto-pulling common-skills stack.")
def init(path: str | None, no_common: bool):
    """Initialize a project.

    Works like git init — run in an existing directory or provide a path
    to create one. Add stacks later with 'agentic-stacks pull'.

    By default, pulls agentic-stacks/common-skills. Use --no-common to skip.

    \b
    Examples:
      agentic-stacks init                  # init current directory
      agentic-stacks init my-deployment    # create and init my-deployment/
      agentic-stacks init --no-common      # init without common-skills
    """
    if path is None:
        stack_dir = pathlib.Path(".")
    else:
        stack_dir = pathlib.Path(path)
        stack_dir.mkdir(parents=True, exist_ok=True)

    # Don't re-init if already initialized
    if (stack_dir / "stacks.lock").exists():
        raise click.ClickException(
            f"Already initialized — {stack_dir / 'stacks.lock'} exists."
        )

    _init_operator_project(stack_dir)

    if not no_common:
        try:
            _pull_common_skills(stack_dir)
        except Exception as e:
            click.echo(f"  Warning: could not pull common-skills: {e}")

    click.echo(f"  Run 'agentic-stacks search' to discover stacks.")
    click.echo(f"  Run 'agentic-stacks pull <name>' to add one.")
