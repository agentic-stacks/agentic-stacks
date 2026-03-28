"""astack doctor — validate a stack project."""

import json
import pathlib

import click

from agentic_stacks.manifest import load_manifest, ManifestError


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
def doctor(path: str):
    """Validate a stack project for correctness."""
    stack_dir = pathlib.Path(path)
    warnings = []

    manifest_path = stack_dir / "stack.yaml"
    try:
        manifest = load_manifest(manifest_path)
        click.echo(f"  manifest: {manifest['full_name']}@{manifest['version']}")
    except ManifestError as e:
        raise click.ClickException(f"Invalid manifest: {e}")

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
                warnings.append(f"Profile category directory missing: {profiles_path}{cat}/")

    schema_path_str = manifest.get("environment_schema", "")
    if schema_path_str:
        schema_file = stack_dir / schema_path_str
        if schema_file.exists():
            try:
                json.loads(schema_file.read_text())
                click.echo(f"  schema: valid")
            except json.JSONDecodeError as e:
                raise click.ClickException(f"Invalid environment schema JSON: {e}")
        else:
            warnings.append(f"Environment schema not found: {schema_path_str}")

    for skill in manifest.get("skills", []):
        entry = stack_dir / skill["entry"]
        if not entry.exists():
            warnings.append(f"Skill entry not found: {skill['name']} -> {skill['entry']}")

    deprecations = manifest.get("deprecations", [])
    if deprecations:
        click.echo(f"\n  Deprecations ({len(deprecations)}):")
        for dep in deprecations:
            click.echo(f"    - {dep['skill']}: deprecated since {dep['since']}, removal in {dep['removal']}, use '{dep['replacement']}' instead")

    if warnings:
        click.echo(f"\n  Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"    WARN: {warning}")

    click.echo(f"\n  Stack is healthy.")
