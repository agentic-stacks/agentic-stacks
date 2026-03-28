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
    """Scaffold an operator project that extends a base stack."""
    from_path = pathlib.Path(from_stack)
    if from_path.is_dir():
        manifest_path = from_path / "stack.yaml"
    else:
        raise click.ClickException(
            f"Stack path not found: {from_stack}. "
            "Pass a local path to a stack directory."
        )

    try:
        parent = load_manifest(manifest_path)
    except ManifestError as e:
        raise click.ClickException(f"Invalid base stack: {e}")

    parent_name = parent["name"]
    parent_namespace = parent["namespace"]
    parent_version = parent["version"]
    project_spec = parent.get("project", {})
    per_env = project_spec.get("per_environment", [])

    # Create directories
    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()
    (stack_dir / "state").mkdir()

    # Scaffold example environment
    example_env = envs_dir / "example"
    example_env.mkdir()

    example_config = {
        "name": "example",
        "description": f"Example environment — edit this for your deployment",
    }
    with open(example_env / "config.yml", "w") as f:
        yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)

    # Create per-environment directories from parent's project spec
    for item in per_env:
        if item.endswith("/"):
            (example_env / item.rstrip("/")).mkdir(exist_ok=True)

    # Operator's stack.yaml with extends
    operator_manifest = {
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"{name} — extends {parent_namespace}/{parent_name}",
        "extends": {
            "name": parent_name,
            "namespace": parent_namespace,
            "version": parent_version,
        },
        "depends_on": [],
        "deprecations": [],
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(operator_manifest, f, default_flow_style=False, sort_keys=False)

    # stacks.lock
    lock = {
        "stacks": [{
            "name": f"{parent_namespace}/{parent_name}",
            "version": parent_version,
            "digest": "",
            "registry": f"ghcr.io/{parent_namespace}/{parent_name}:{parent_version}",
        }]
    }
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    # .gitignore
    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    # CLAUDE.md — wires the agent to the stack's skills
    skills_list = parent.get("skills", [])
    skills_md = ""
    if skills_list:
        skills_md = "\n## Available Skills\n\n"
        for skill in skills_list:
            skills_md += f"- **{skill['name']}** — {skill.get('description', '')}\n"

    per_env_md = ""
    if per_env:
        per_env_md = "\n## Environment Structure\n\nEach environment in `environments/` contains:\n\n"
        per_env_md += "- `config.yml` — your deployment choices\n"
        for item in per_env:
            if item != "config.yml":
                per_env_md += f"- `{item}` — edit as needed for your deployment\n"

    claude_md = (
        f"# {name}\n\n"
        f"Operator project extending "
        f"`{parent_namespace}/{parent_name}@{parent_version}`.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads the base stack to .stacks/\n"
        f"```\n\n"
        f"## How This Works\n\n"
        f"The base stack's skills are in "
        f"`.stacks/{parent_namespace}/{parent_name}/{parent_version}/skills/`. "
        f"Read them to understand how to deploy, configure, and operate "
        f"{parent.get('target', {}).get('software', 'this software')}.\n\n"
        f"The stack's CLAUDE.md at "
        f"`.stacks/{parent_namespace}/{parent_name}/{parent_version}/CLAUDE.md` "
        f"is the primary guide — it describes what config is needed, "
        f"where files go, and how the automation works.\n\n"
        f"Work with the operator to build out each environment.\n"
        f"{skills_md}"
        f"{per_env_md}"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized operator project '{namespace}/{name}' at {stack_dir}")
    click.echo(f"  Extends: {parent_namespace}/{parent_name}@{parent_version}")
    click.echo(f"  Run 'agentic-stacks pull' to download the base stack.")
