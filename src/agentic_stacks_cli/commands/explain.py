"""agentic-stacks explain — summarize what a stack teaches an agent."""

import pathlib
import re

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.lock import read_lock


@click.command()
@click.argument("name", required=False, default=None)
@click.option("--path", "target_dir", default=".", type=click.Path(exists=True),
              help="Project or stack directory")
def explain(name: str | None, target_dir: str):
    """Explain what a stack teaches an agent.

    Shows a human-readable summary: identity, skills, profiles, dependencies,
    requirements, and workflows. Useful for understanding what a pulled stack
    provides before using it.

    \b
    Examples:
      agentic-stacks explain                     # explain stack in current dir
      agentic-stacks explain kubernetes-talos     # explain a pulled stack
      agentic-stacks explain --path ./my-project  # explain all stacks in project
    """
    target = pathlib.Path(target_dir)

    if name:
        # Explain a specific pulled stack
        stack_dir = _find_stack(target, name)
        if not stack_dir:
            raise click.ClickException(
                f"Stack '{name}' not found. Is it pulled? Check with 'agentic-stacks list'.")
        _explain_stack(stack_dir)
        return

    # If in a stack directory (has stack.yaml), explain it
    if (target / "stack.yaml").exists():
        _explain_stack(target)
        return

    # If in a project directory, explain all pulled stacks
    if (target / "stacks.lock").exists():
        _explain_project(target)
        return

    raise click.ClickException(
        "Not a stack or project. Use 'agentic-stacks explain <name>' or run from a stack/project directory.")


def _find_stack(project_dir: pathlib.Path, name: str) -> pathlib.Path | None:
    """Find a pulled stack by name (short or full)."""
    short_name = name.split("/")[-1]
    candidate = project_dir / ".stacks" / short_name
    if (candidate / "stack.yaml").exists():
        return candidate
    return None


def _explain_project(project_dir: pathlib.Path):
    """Explain all stacks in a project."""
    lock = read_lock(project_dir / "stacks.lock")
    stacks = lock.get("stacks", [])

    if not stacks:
        click.echo("No stacks in this project.")
        return

    click.echo(f"Project: {project_dir.resolve().name}")
    click.echo(f"Stacks: {len(stacks)}\n")

    for entry in stacks:
        short_name = entry["name"].split("/")[-1]
        stack_dir = project_dir / ".stacks" / short_name
        if (stack_dir / "stack.yaml").exists():
            _explain_stack(stack_dir)
            click.echo("")  # blank line between stacks
        else:
            click.echo(f"  {entry['name']}: not pulled\n")


def _explain_stack(stack_dir: pathlib.Path):
    """Print a human-readable summary of a stack."""
    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        click.echo(f"  Could not load stack: {e}")
        return

    full_name = manifest["full_name"]
    version = manifest.get("version", "?")
    description = manifest.get("description", "")
    target = manifest.get("target", {})
    skills = manifest.get("skills", [])
    depends_on = manifest.get("depends_on", [])
    requires = manifest.get("requires", {})
    profiles = manifest.get("profiles", {})
    deprecations = manifest.get("deprecations", [])
    docs_sources = manifest.get("docs_sources", [])

    # Header
    click.echo(f"  {full_name}@{version}")
    if description:
        click.echo(f"  {description}")

    # Target
    if target.get("software"):
        versions = ", ".join(target.get("versions", [])) or "any"
        click.echo(f"\n  Target: {target['software']} ({versions})")

    # Skills
    if skills:
        click.echo(f"\n  Skills ({len(skills)}):")
        for skill in skills:
            desc = skill.get("description", "")
            entry = skill.get("entry", "")
            click.echo(f"    {skill['name']}: {desc}")
            click.echo(f"      entry: {entry}")

    # Profiles
    categories = profiles.get("categories", [])
    if categories:
        click.echo(f"\n  Profiles: {', '.join(categories)}")

    # Dependencies
    if depends_on:
        click.echo(f"\n  Depends on: {', '.join(_dep_name(d) for d in depends_on)}")

    # Requirements
    tools = requires.get("tools", [])
    python_req = requires.get("python", "")
    if tools or python_req:
        click.echo(f"\n  Requirements:")
        if python_req:
            click.echo(f"    Python {python_req}")
        for tool in tools:
            if isinstance(tool, dict):
                click.echo(f"    {tool.get('name', '?')}: {tool.get('description', '')}")
            else:
                click.echo(f"    {tool}")

    # Deprecations
    if deprecations:
        click.echo(f"\n  Deprecations ({len(deprecations)}):")
        for dep in deprecations:
            click.echo(f"    {dep['skill']} → {dep['replacement']} (since {dep['since']})")

    # Documentation sources
    if docs_sources:
        click.echo(f"\n  Documentation sources:")
        for url in docs_sources:
            click.echo(f"    {url}")

    # CLAUDE.md summary — extract workflows if present
    claude_path = stack_dir / "CLAUDE.md"
    if claude_path.exists():
        workflows = _extract_workflows(claude_path.read_text())
        if workflows:
            click.echo(f"\n  Workflows:")
            for wf in workflows:
                click.echo(f"    - {wf}")


def _dep_name(dep) -> str:
    """Extract a readable name from a depends_on entry."""
    if isinstance(dep, str):
        return dep
    if isinstance(dep, dict):
        name = dep.get("name", "")
        owner = dep.get("owner", dep.get("namespace", ""))
        if owner:
            return f"{owner}/{name}"
        return name
    return str(dep)


def _extract_workflows(claude_md_content: str) -> list[str]:
    """Extract workflow names from CLAUDE.md ## Workflows section."""
    workflows = []
    in_workflows = False

    for line in claude_md_content.splitlines():
        if re.match(r"^##\s+Workflows?\s*$", line, re.IGNORECASE):
            in_workflows = True
            continue
        if in_workflows:
            # Stop at the next ## heading
            if re.match(r"^##\s+", line) and not re.match(r"^###", line):
                break
            # Capture ### sub-headings as workflow names
            wf_match = re.match(r"^###\s+(.+)", line)
            if wf_match:
                workflows.append(wf_match.group(1).strip())

    return workflows
