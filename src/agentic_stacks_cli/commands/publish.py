"""agentic-stacks publish — generate a registry formula from a stack."""

import pathlib

import click
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.registry_repo import ensure_registry, write_formula


def _manifest_to_formula(manifest: dict) -> dict:
    """Convert a stack manifest to a registry formula."""
    owner = manifest.get("owner") or manifest.get("namespace", "")
    skills = []
    for skill in manifest.get("skills", []):
        skills.append({"name": skill["name"], "description": skill.get("description", "")})
    requires = dict(manifest.get("requires", {}))
    if "tools" in requires:
        tools = requires["tools"]
        if tools and isinstance(tools[0], dict):
            requires["tools"] = [t["name"] for t in tools]
    return {
        "name": manifest["name"],
        "owner": owner,
        "version": manifest.get("version", "0.0.1"),
        "repository": manifest.get("repository", ""),
        "tag": f"v{manifest.get('version', '0.0.1')}",

        "description": manifest.get("description", "").strip(),
        "target": manifest.get("target", {}),
        "skills": skills,
        "depends_on": manifest.get("depends_on", []),
        "requires": requires,
    }


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def publish(path: str, config_path: str | None):
    """Generate a registry formula from a stack."""
    stack_dir = pathlib.Path(path)
    cfg_path = pathlib.Path(config_path) if config_path else None

    if not (stack_dir / "stack.yaml").exists() and (stack_dir / "stacks.lock").exists():
        raise click.ClickException(
            "This is a project, not a stack. Publish is for stack authors."
        )

    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Invalid stack: {e}")

    name = manifest["name"]
    owner = manifest.get("owner") or manifest.get("namespace", "")
    version = manifest.get("version", "0.0.1")
    repository = manifest.get("repository", "")

    if not repository:
        raise click.ClickException(
            "stack.yaml must include a 'repository' field "
            "(e.g., https://github.com/your-org/your-stack)"
        )

    formula = _manifest_to_formula(manifest)

    click.echo(f"Publishing {owner}/{name}@{version}...")
    click.echo(f"  Repository: {repository}")

    # Write formula to local registry cache
    from agentic_stacks_cli.config import load_config
    cfg = load_config(cfg_path)
    registry_path = ensure_registry(
        repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
    )
    write_formula(registry_path, formula)
    click.echo(f"  Wrote formula to local registry cache.")

    # Also write to current directory for PR submission
    formula_path = stack_dir / "formula.yaml"
    with open(formula_path, "w") as f:
        yaml.dump(formula, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    click.echo(f"  Wrote {formula_path}")

    click.echo(f"\nPublished {owner}/{name}@{version}")
    click.echo(f"\nTo add to the registry, submit a PR to:")
    click.echo(f"  https://github.com/agentic-stacks/registry")
    click.echo(f"  Add: stacks/{owner}/{name}.yaml")
