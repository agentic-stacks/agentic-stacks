"""agentic-stacks doctor — validate a stack or operator project."""

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
    lock_path = stack_dir / "stacks.lock"

    # Simple project (stacks.lock, no stack.yaml)
    if not manifest_path.exists() and lock_path.exists():
        _doctor_project(stack_dir, warnings)
        if warnings:
            click.echo(f"\n  Warnings ({len(warnings)}):")
            for warning in warnings:
                click.echo(f"    WARN: {warning}")
        click.echo(f"\n  Project is healthy.")
        return

    # Neither a stack nor a project
    if not manifest_path.exists() and not lock_path.exists():
        raise click.ClickException(
            f"Not a stack or project — no stack.yaml or stacks.lock found in {stack_dir.resolve()}.\n"
            f"  Run 'agentic-stacks init' to create a project, or "
            f"'agentic-stacks create owner/name' to scaffold a stack."
        )

    try:
        manifest = load_manifest(manifest_path)
        click.echo(f"  manifest: {manifest['full_name']}@{manifest.get('version', 'latest')}")
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


def _doctor_project(stack_dir, warnings):
    """Validate a project and its pulled stacks."""
    import yaml

    lock_path = stack_dir / "stacks.lock"
    lock = yaml.safe_load(lock_path.read_text()) or {}
    stacks = lock.get("stacks", [])
    click.echo(f"  project: {stack_dir.resolve().name}")
    click.echo(f"  stacks.lock: {len(stacks)} stack(s)")

    for entry in stacks:
        name = entry["name"].split("/")[-1]
        dest = stack_dir / ".stacks" / name
        manifest_path = dest / "stack.yaml"
        if manifest_path.exists():
            click.echo(f"\n  .stacks/{name}: pulled")
            try:
                manifest = load_manifest(manifest_path)
                skill_count = len(manifest.get("skills", []))
                click.echo(f"    manifest: {manifest['full_name']}@{manifest.get('version', 'latest')}")
                click.echo(f"    skills: {skill_count}")
                # Check skill entries resolve
                for skill in manifest.get("skills", []):
                    entry_path = dest / skill["entry"]
                    if not entry_path.exists():
                        warnings.append(
                            f"{name}: skill entry not found: {skill['name']} -> {skill['entry']}")
            except ManifestError as e:
                warnings.append(f"{name}: invalid manifest: {e}")
        elif (dest / "CLAUDE.md").exists():
            click.echo(f"\n  .stacks/{name}: pulled (no manifest)")
        else:
            click.echo(f"\n  .stacks/{name}: NOT FOUND")
            warnings.append(f"Stack '{entry['name']}' not pulled. Run 'agentic-stacks pull'.")

    if not (stack_dir / "CLAUDE.md").exists():
        warnings.append("Missing CLAUDE.md")

    if not (stack_dir / ".gitignore").exists():
        warnings.append("Missing .gitignore")


def _doctor_operator_project(stack_dir, manifest, extends, warnings):
    """Validate an operator project that extends a base stack."""
    ext_name = extends.get("name", "")
    ext_namespace = extends.get("owner", extends.get("namespace", ""))
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

    # Optional directories — report if present, don't warn if absent
    envs_dir = stack_dir / "environments"
    if envs_dir.is_dir():
        envs = sorted([
            d.name for d in envs_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ])
        if envs:
            click.echo(f"  environments: {', '.join(envs)}")


def _doctor_stack(stack_dir, manifest, warnings):
    """Validate a regular stack (original behavior)."""
    skills_dir = stack_dir / "skills"
    if not skills_dir.is_dir():
        warnings.append("Missing directory: skills/")
    else:
        click.echo(f"  skills/: found")

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
