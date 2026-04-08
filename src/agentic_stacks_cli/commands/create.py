"""agentic-stacks create — scaffold a new stack."""

import pathlib

import click
import yaml


def _parse_identity(identity: str) -> tuple[str, str]:
    """Parse 'owner/name' into (owner, name)."""
    if "/" not in identity:
        raise click.BadParameter(
            f"Expected owner/name format (e.g., my-org/my-stack), got: {identity}",
            param_hint="'IDENTITY'",
        )
    owner, name = identity.split("/", 1)
    if not owner or not name:
        raise click.BadParameter(
            f"Both owner and name are required (e.g., my-org/my-stack), got: {identity}",
            param_hint="'IDENTITY'",
        )
    return owner, name


@click.command()
@click.argument("identity")
@click.argument("path", required=False, default=None, type=click.Path())
def create(identity: str, path: str | None):
    """Create a new stack.

    IDENTITY is owner/name (e.g., my-org/my-stack).
    PATH is where to create it (default: ./name).
    """
    owner, name = _parse_identity(identity)

    if path is None:
        stack_dir = pathlib.Path(f"./{name}")
    else:
        stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(
            f"Directory already exists and is not empty: {stack_dir}"
        )

    stack_dir.mkdir(parents=True, exist_ok=True)

    (stack_dir / "skills").mkdir()

    manifest = {
        "name": name,
        "owner": owner,
        "description": f"{name} stack",
        "target": {"software": name, "versions": []},
        "skills": [],
        "depends_on": [],
        "requires": {"tools": [], "python": ">=3.11"},
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    claude_md = (
        f"# {name}\n\n"
        f"Stack: {owner}/{name}\n\n"
        f"## Routing Table\n\n"
        f"| Need | Skill | Entry |\n"
        f"|---|---|---|\n\n"
        f"## Authoring Guide\n\n"
        f"Follow the stack authoring guide to build this stack:\n"
        f"https://agentic-stacks.com/docs/authoring\n\n"
        f"Run `agentic-stacks doctor` to validate.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    readme = (
        f"# {name}\n\n"
        f"An [agentic stack](https://github.com/agentic-stacks/agentic-stacks) "
        f"that teaches AI agents how to operate {name}.\n\n"
        f"## Usage\n\n"
        f"```bash\n"
        f"# Create a project and pull this stack\n"
        f"agentic-stacks init my-project\n"
        f"cd my-project\n"
        f"agentic-stacks pull {owner}/{name}\n"
        f"```\n\n"
        f"Then start Claude Code — it reads `.stacks/{name}/CLAUDE.md` "
        f"and becomes an expert operator.\n\n"
        f"## Authoring\n\n"
        f"See the [authoring guide](https://agentic-stacks.com/docs/authoring) "
        f"for how to build and extend this stack.\n"
    )
    (stack_dir / "README.md").write_text(readme)

    click.echo(f"Created stack '{owner}/{name}' at {stack_dir}")
