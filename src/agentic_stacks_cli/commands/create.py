"""agentic-stacks create — scaffold a new stack."""

import pathlib

import click
import yaml


def _training_skill(name: str) -> str:
    """Return the training skill template for a new stack."""
    return f"""\
# Training Mode

When the user asks to be trained on this stack, switch from task-execution
mode to teaching mode. Use the stack's skills as your source material.

## Getting Started

1. **Assess the learner.** Ask what they already know about {name} and
   related technologies. Adjust depth accordingly.

2. **Build a curriculum.** Read every skill in this stack. Sequence them
   from foundational concepts to advanced operations. Present the
   learning path and let the user adjust it.

3. **Teach concepts before procedures.** For each skill, explain the
   *why* before the *how*. Use the skill's content as your source
   material — not generic knowledge.

4. **Make it interactive.** After explaining a concept, give the user
   a practical task or question. Use real commands and configurations
   from the skill content. Ask them to predict outcomes before
   showing answers.

5. **Check understanding.** Ask questions between topics. If the user
   struggles, go deeper on prerequisites. If they're moving quickly,
   skip ahead or go deeper on advanced material.

6. **Connect the dots.** Explicitly link concepts across skills.
   Help the user build a mental model of how everything fits together.

7. **Summarize each section.** Recap key concepts and what the user
   can now do before moving on.

## Handling Specific Requests

- "Train me on this stack" — start from the beginning with an assessment.
- "Train me on [topic]" — jump to the relevant skill and teach from there.
- "Quiz me" — test knowledge on material covered so far.
- "What should I learn next?" — recommend the next topic based on progress.

## Session Continuity

Track which topics the user has covered in this session. If they want
to stop and continue later, summarize where they left off and what
topics remain.
"""


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

    # Scaffold training skill
    training_dir = stack_dir / "skills" / "training"
    training_dir.mkdir(parents=True)
    training_dir.joinpath("README.md").write_text(_training_skill(name))

    manifest = {
        "name": name,
        "owner": owner,
        "version": "0.1.0",
        "description": f"{name} stack",
        "target": {"software": name, "versions": []},
        "skills": [
            {
                "name": "training",
                "entry": "skills/training/",
                "description": "Interactive training — teaches this stack's domain to new users",
            },
        ],
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
        f"|---|---|---|\n"
        f"| Learn / Train | training | skills/training/ |\n\n"
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
