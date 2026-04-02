"""agentic-stacks init — scaffold an operator project."""

import pathlib

import click
import yaml


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
    click.echo(f"  Run 'agentic-stacks search' to discover stacks.")
    click.echo(f"  Run 'agentic-stacks pull <name>' to add one.")


@click.command()
@click.argument("path", required=False, default=None, type=click.Path())
def init(path: str | None):
    """Initialize a project.

    Works like git init — run in an existing directory or provide a path
    to create one. Add stacks later with 'agentic-stacks pull'.

    \b
    Examples:
      agentic-stacks init                  # init current directory
      agentic-stacks init my-deployment    # create and init my-deployment/
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
