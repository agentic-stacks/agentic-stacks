"""astack doctor — validate a stack or operator project."""

import json
import pathlib

import click

from agentic_stacks.manifest import load_manifest, ManifestError


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".",
              help="Path to stack directory")
def doctor(path: str):
    """Validate a stack or operator project for correctness."""
    stack_dir = pathlib.Path(path)
    warnings = []

    manifest_path = stack_dir / "stack.yaml"
    try:
        manifest = load_manifest(manifest_path)
        click.echo(f"  manifest: {manifest['full_name']}@{manifest['version']}")
    except ManifestError as e:
        raise click.ClickException(f"Invalid manifest: {e}")

    extends = manifest.get("extends")
    if extends:
        _doctor_operator_project(stack_dir, manifest, extends, warnings)
    else:
        _doctor_stack(stack_dir, manifest, warnings)

    if warnings:
        click.echo(f"\n  Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"    WARN: {warning}")

    click.echo(f"\n  Stack is healthy.")


def _doctor_operator_project(stack_dir, manifest, extends, warnings):
    """Validate an operator project that extends a base stack."""
    ext_name = extends.get("name", "")
    ext_namespace = extends.get("namespace", "")
    ext_version = extends.get("version", "")
    click.echo(f"  extends: {ext_namespace}/{ext_name}@{ext_version}")

    # Check parent stack is pulled
    parent_candidates = list(
        (stack_dir / ".stacks" / ext_namespace / ext_name).glob("*/stack.yaml")
    ) if (stack_dir / ".stacks" / ext_namespace / ext_name).is_dir() else []
    if parent_candidates:
        click.echo(f"  parent: found in .stacks/")
    else:
        click.echo(f"  parent: NOT FOUND — run 'agentic-stacks pull'")
        warnings.append(
            f"Parent stack '{ext_namespace}/{ext_name}' not in .stacks/. "
            f"Run 'agentic-stacks pull' to download it."
        )

    # Check environments
    envs_dir = stack_dir / "environments"
    if envs_dir.is_dir():
        envs = sorted([
            d.name for d in envs_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ])
        if envs:
            click.echo(f"  environments: {', '.join(envs)}")
        else:
            warnings.append("No environments found in environments/")
    else:
        warnings.append("Missing directory: environments/")

    # Check state dir
    if (stack_dir / "state").is_dir():
        click.echo(f"  state/: found")
    else:
        warnings.append("Missing directory: state/")


def _doctor_stack(stack_dir, manifest, warnings):
    """Validate a regular stack (original behavior)."""
    for dirname in ["skills", "profiles", "environments"]:
        d = stack_dir / dirname
        if not d.is_dir():
            warnings.append(f"Missing directory: {dirname}/")
        else:
            click.echo(f"  {dirname}/: found")

    profiles_path = manifest.get("profiles", {}).get("path", "profiles/")
    profiles_dir = stack_dir / profiles_path
    if profiles_dir.is_dir():
        categories = manifest.get("profiles", {}).get("categories", [])
        for cat in categories:
            if not (profiles_dir / cat).is_dir():
                warnings.append(
                    f"Profile category directory missing: {profiles_path}{cat}/")

    schema_path_str = manifest.get("environment_schema", "")
    if schema_path_str:
        schema_file = stack_dir / schema_path_str
        if schema_file.exists():
            try:
                json.loads(schema_file.read_text())
                click.echo(f"  schema: valid")
            except json.JSONDecodeError as e:
                raise click.ClickException(
                    f"Invalid environment schema JSON: {e}")
        else:
            warnings.append(
                f"Environment schema not found: {schema_path_str}")

    for skill in manifest.get("skills", []):
        entry = stack_dir / skill["entry"]
        if not entry.exists():
            warnings.append(
                f"Skill entry not found: {skill['name']} -> {skill['entry']}")

    deprecations = manifest.get("deprecations", [])
    if deprecations:
        click.echo(f"\n  Deprecations ({len(deprecations)}):")
        for dep in deprecations:
            click.echo(
                f"    - {dep['skill']}: deprecated since {dep['since']}, "
                f"removal in {dep['removal']}, "
                f"use '{dep['replacement']}' instead")
