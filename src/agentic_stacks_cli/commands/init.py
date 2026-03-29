"""astack init — scaffold a new stack or operator project."""

import json
import pathlib

import click
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError


PROFILE_CATEGORIES = ["security", "networking", "storage", "scale", "features"]

DEFAULT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "profiles"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "profiles": {"type": "object"},
        "approval": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["auto", "auto-notify", "human-approve"],
                }
            },
        },
    },
}


@click.command()
@click.argument("path", type=click.Path())
@click.option("--name", required=True, help="Stack name")
@click.option("--namespace", required=True, help="Stack namespace (e.g., org name)")
@click.option("--from", "from_stack", default=None,
              help="Base stack to extend — path to local stack dir or namespace/name@version")
def init(path: str, name: str, namespace: str, from_stack: str | None):
    """Scaffold a new stack or operator project."""
    stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)

    if from_stack:
        _init_operator_project(stack_dir, name, namespace, from_stack)
    else:
        _init_stack(stack_dir, name, namespace)


def _init_stack(stack_dir: pathlib.Path, name: str, namespace: str):
    """Scaffold a new stack (original behavior)."""
    (stack_dir / "skills").mkdir()
    (stack_dir / "src").mkdir()
    (stack_dir / "overrides").mkdir()

    profiles_dir = stack_dir / "profiles"
    profiles_dir.mkdir()
    for category in PROFILE_CATEGORIES:
        (profiles_dir / category).mkdir()

    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()

    manifest = {
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"{name} stack",
        "target": {"software": name, "versions": []},
        "skills": [],
        "profiles": {
            "categories": PROFILE_CATEGORIES,
            "path": "profiles/",
            "merge_order": "security first (enforced), then declared order",
        },
        "environment_schema": "environments/_schema.json",
        "depends_on": [],
        "requires": {"tools": [], "python": ">=3.11"},
        "deprecations": [],
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    claude_md = f"# {name}\n\nStack: {namespace}/{name}\n\nRun `agentic-stacks doctor` to validate.\n"
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized stack '{namespace}/{name}' at {stack_dir}")


def _init_operator_project(stack_dir: pathlib.Path, name: str, namespace: str,
                           from_stack: str):
    """Scaffold a project that uses a stack."""
    from_path = pathlib.Path(from_stack)

    if from_path.is_dir():
        # Local path — read manifest directly
        try:
            parent = load_manifest(from_path / "stack.yaml")
        except ManifestError as e:
            raise click.ClickException(f"Invalid stack: {e}")
        parent_name = parent["name"]
        parent_namespace = parent["namespace"]
        repo_url = parent.get("repository", "")
    else:
        # Treat as GitHub reference — namespace/name or just name
        if "/" in from_stack:
            parent_namespace, parent_name = from_stack.split("/", 1)
        else:
            parent_namespace = "agentic-stacks"
            parent_name = from_stack
        repo_url = f"https://github.com/{parent_namespace}/{parent_name}"

    # stacks.lock
    lock = {
        "stacks": [{
            "name": f"{parent_namespace}/{parent_name}",
            "version": "latest",
            "repository": repo_url,
        }]
    }
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    # .gitignore
    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    # CLAUDE.md
    claude_md = (
        f"# {name}\n\n"
        f"This project uses the `{parent_name}` stack for domain expertise.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads the stack to .stacks/\n"
        f"```\n\n"
        f"## How This Works\n\n"
        f"Read `.stacks/{parent_name}/CLAUDE.md` for the stack's expertise — "
        f"it knows how to deploy, configure, and operate this software.\n\n"
        f"Work with the operator to build out their deployment. "
        f"Everything created here gets committed to this repo for reproducibility.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized project '{namespace}/{name}' at {stack_dir}")
    click.echo(f"  Uses: {parent_namespace}/{parent_name}")
    click.echo(f"  Run 'agentic-stacks pull' to download the stack.")
