"""agentic-stacks lint — validate skill content against authoring standards."""

import pathlib

import click

from agentic_stacks.lint_rules import (
    LintRules,
    lint_stack,
    load_project_rules,
    merge_stack_rules,
)


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".",
              help="Path to a stack directory or project")
@click.option("--rules", "rules_path", type=click.Path(exists=True), default=None,
              help="Path to a .lint-rules.yaml file")
def lint(path: str, rules_path: str | None):
    """Lint a stack's skills against authoring standards.

    Validates skill content quality: README presence, file length, placeholder
    text, heading style, CLAUDE.md structure, routing table completeness, and
    critical rules count.

    Rules are loaded in order:
      1. Common-skills .lint-rules.yaml (centralized control)
      2. Stack-level .lint-rules.yaml (per-stack override)
      3. --rules flag (explicit override)
      4. Built-in defaults (if nothing else found)

    \b
    Examples:
      agentic-stacks lint                    # lint stack in current directory
      agentic-stacks lint --path ./my-stack  # lint a specific stack
      agentic-stacks lint --rules rules.yaml # use custom rules file
    """
    stack_dir = pathlib.Path(path)
    manifest_path = stack_dir / "stack.yaml"
    lock_path = stack_dir / "stacks.lock"

    # If this is a project (has stacks.lock), lint all pulled stacks
    if not manifest_path.exists() and lock_path.exists():
        _lint_project(stack_dir, rules_path)
        return

    # Single stack
    if not manifest_path.exists():
        raise click.ClickException(
            f"No stack.yaml found in {stack_dir.resolve()}.\n"
            f"  Run from a stack directory or use --path."
        )

    rules = _resolve_rules(stack_dir, rules_path)
    _print_rules_source(stack_dir, rules_path)
    messages = lint_stack(stack_dir, rules)
    _print_results(stack_dir, messages)


def _lint_project(project_dir: pathlib.Path, rules_path: str | None):
    """Lint all pulled stacks in a project."""
    import yaml

    lock_path = project_dir / "stacks.lock"
    lock = yaml.safe_load(lock_path.read_text()) or {}
    stacks = lock.get("stacks", [])

    if not stacks:
        click.echo("No stacks in this project.")
        return

    # Report rules source
    common_rules = project_dir / ".stacks" / "common-skills" / ".lint-rules.yaml"
    if rules_path:
        click.echo(f"  Rules: {rules_path}")
    elif common_rules.exists():
        click.echo(f"  Rules: common-skills/.lint-rules.yaml")
    else:
        click.echo(f"  Rules: built-in defaults")

    total_errors = 0
    total_warnings = 0

    for entry in stacks:
        name = entry["name"].split("/")[-1]
        stack_dir = project_dir / ".stacks" / name
        manifest_path = stack_dir / "stack.yaml"

        if not manifest_path.exists():
            click.echo(f"\n  {entry['name']}: skipped (not pulled or no manifest)")
            continue

        rules = _resolve_rules(stack_dir, rules_path, project_dir)
        messages = lint_stack(stack_dir, rules)

        errors = [m for m in messages if m.level == "error"]
        warnings = [m for m in messages if m.level == "warning"]
        total_errors += len(errors)
        total_warnings += len(warnings)

        _print_results(stack_dir, messages, prefix=entry["name"])

    click.echo(f"\n  Total: {total_errors} error(s), {total_warnings} warning(s)")


def _resolve_rules(stack_dir: pathlib.Path, rules_path: str | None,
                   project_dir: pathlib.Path | None = None) -> LintRules:
    """Resolve lint rules with the correct precedence."""
    # Explicit --rules flag takes highest precedence
    if rules_path:
        from agentic_stacks.lint_rules import load_rules_from_yaml
        return load_rules_from_yaml(pathlib.Path(rules_path))

    # Try to find project-level rules (from common-skills)
    if project_dir:
        rules = load_project_rules(project_dir)
    else:
        # If linting a single stack, look for common-skills in parent project
        parent_stacks = stack_dir.parent  # .stacks/
        parent_project = parent_stacks.parent if parent_stacks.name == ".stacks" else None
        if parent_project:
            rules = load_project_rules(parent_project)
        else:
            rules = LintRules()

    # Merge stack-level overrides
    rules = merge_stack_rules(rules, stack_dir)
    return rules


def _print_rules_source(stack_dir: pathlib.Path, rules_path: str | None):
    """Print where lint rules are being loaded from."""
    if rules_path:
        click.echo(f"  Rules: {rules_path}")
        return

    # Check if this stack lives inside a project's .stacks/
    parent_stacks = stack_dir.parent
    project_dir = parent_stacks.parent if parent_stacks.name == ".stacks" else None

    if project_dir:
        common_rules = project_dir / ".stacks" / "common-skills" / ".lint-rules.yaml"
        if common_rules.exists():
            click.echo(f"  Rules: common-skills/.lint-rules.yaml")
        else:
            click.echo(f"  Rules: built-in defaults")
    else:
        click.echo(f"  Rules: built-in defaults")

    if (stack_dir / ".lint-rules.yaml").exists():
        click.echo(f"  Stack overrides: .lint-rules.yaml")


def _print_results(stack_dir: pathlib.Path, messages: list, prefix: str | None = None):
    """Print lint results."""
    errors = [m for m in messages if m.level == "error"]
    warnings = [m for m in messages if m.level == "warning"]

    label = prefix or stack_dir.name
    if not messages:
        click.echo(f"\n  {label}: clean")
        return

    click.echo(f"\n  {label}: {len(errors)} error(s), {len(warnings)} warning(s)")
    for msg in messages:
        # Show path relative to stack dir for readability
        try:
            rel = pathlib.Path(msg.path).relative_to(stack_dir)
        except ValueError:
            rel = msg.path
        click.echo(f"    {msg.level.upper()}: [{msg.rule}] {rel} — {msg.message}")
