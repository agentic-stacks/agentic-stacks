"""agentic-stacks init — scaffold an operator project that uses a stack."""

import pathlib

import click
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError


DEFAULT_ORG = "agentic-stacks"
GITHUB_BASE = "https://github.com"

PROFILE_CATEGORIES = ["security", "networking", "storage", "scale", "features"]


def _resolve_stack_ref(ref: str) -> tuple[str, str, str]:
    """Resolve a stack reference to (owner, name, repo_url)."""
    ref_path = pathlib.Path(ref)
    if ref_path.is_dir():
        try:
            parent = load_manifest(ref_path / "stack.yaml")
        except ManifestError as e:
            raise click.ClickException(f"Invalid stack: {e}")
        owner = parent["owner"]
        name = parent["name"]
        repo_url = parent.get("repository", "")
        return owner, name, repo_url

    if "/" in ref:
        owner, name = ref.split("/", 1)
    else:
        owner = DEFAULT_ORG
        name = ref
    repo_url = f"{GITHUB_BASE}/{owner}/{name}"
    return owner, name, repo_url


def _init_operator_project(stack_dir: pathlib.Path, owner: str, name: str, repo_url: str):
    """Scaffold a project that uses a stack."""
    lock = {
        "stacks": [{
            "name": f"{owner}/{name}",
            "version": "latest",
            "repository": repo_url,
        }]
    }
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    claude_md = (
        f"# {name}\n\n"
        f"This project uses agentic stacks for domain expertise.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads all stacks to .stacks/\n"
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
    click.echo(f"  Uses: {owner}/{name}")
    click.echo(f"  Run 'agentic-stacks pull' to download the stack.")


def _legacy_init_stack(stack_dir: pathlib.Path, name: str, owner: str):
    """Backwards-compat: scaffold a stack (old init without --from)."""
    import json
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
        "owner": owner,
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

    default_schema = {
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
    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(default_schema, f, indent=2)
        f.write("\n")

    claude_md = (
        f"# {name}\n\n"
        f"Stack: {owner}/{name}\n\n"
        f"## Authoring Guide\n\n"
        f"Follow the stack authoring guide to build this stack:\n"
        f"https://github.com/agentic-stacks/agentic-stacks/blob/main/docs/guides/authoring-a-stack.md\n\n"
        f"Run `agentic-stacks doctor` to validate.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized stack '{owner}/{name}' at {stack_dir}")


@click.command()
@click.argument("identity_or_path", required=False, default=None)
@click.argument("path", required=False, default=None, type=click.Path())
@click.option("--name", default=None, hidden=True, help="[Deprecated] Stack name")
@click.option("--namespace", default=None, hidden=True, help="[Deprecated] Stack owner")
@click.option("--from", "from_stack", default=None, hidden=True,
              help="[Deprecated] Stack to use")
def init(identity_or_path: str | None, path: str | None,
         name: str | None, namespace: str | None, from_stack: str | None):
    """Initialize a project using a stack.

    IDENTITY is owner/name of the stack (e.g., agentic-stacks/kubernetes-talos).
    PATH is where to create the project (default: ./name).
    """
    # Detect legacy flag-based invocation
    if name is not None or namespace is not None:
        click.echo(
            "WARNING: --name and --namespace are deprecated. "
            "Use: agentic-stacks create owner/name [path] (for new stacks) "
            "or: agentic-stacks init owner/name [path] (for projects)",
        )
        legacy_name = name or "unnamed"
        legacy_owner = namespace or "unknown"
        legacy_path = pathlib.Path(identity_or_path) if identity_or_path else pathlib.Path(f"./{legacy_name}")

        if legacy_path.exists() and any(legacy_path.iterdir()):
            raise click.ClickException(f"Directory already exists and is not empty: {legacy_path}")
        legacy_path.mkdir(parents=True, exist_ok=True)

        if from_stack:
            owner, stack_name, repo_url = _resolve_stack_ref(from_stack)
            _init_operator_project(legacy_path, owner, stack_name, repo_url)
        else:
            _legacy_init_stack(legacy_path, legacy_name, legacy_owner)
        return

    # New positional syntax
    if identity_or_path is None:
        raise click.UsageError("Missing argument: IDENTITY (owner/name of stack to use)")

    identity = identity_or_path
    if "/" not in identity:
        raise click.BadParameter(
            f"Expected owner/name format (e.g., agentic-stacks/kubernetes-talos), got: {identity}",
            param_hint="'IDENTITY'",
        )

    owner, stack_name = identity.split("/", 1)
    repo_url = f"{GITHUB_BASE}/{owner}/{stack_name}"

    if path is None:
        stack_dir = pathlib.Path(f"./{stack_name}")
    else:
        stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)
    _init_operator_project(stack_dir, owner, stack_name, repo_url)
