# Common Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a shared `common-skills` stack with training, guide, orientation, and feedback skills, and wire `init` to auto-pull it.

**Architecture:** The common-skills stack is a regular stack repo at `agentic-stacks/common-skills`. The CLI's `init` command gains a `--no-common` flag and auto-pulls `common-skills` after scaffolding. All existing commands (remove, update, list) work without changes.

**Tech Stack:** Python (Click CLI), Markdown (skill content), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-04-02-common-skills-design.md`

---

### Task 1: Create the common-skills stack repo

**Files:**
- Create: `CLAUDE.md` (in common-skills repo)
- Create: `stack.yaml` (in common-skills repo)
- Create: `README.md` (in common-skills repo)
- Create: `skills/training/README.md`
- Create: `skills/guide/README.md`
- Create: `skills/orientation/README.md`
- Create: `skills/feedback/README.md`

**Repo:** https://github.com/agentic-stacks/common-skills (already exists, empty or near-empty)

- [ ] **Step 1: Clone the repo**

```bash
cd /Users/ant/Development/agentic-stacks
git clone https://github.com/agentic-stacks/common-skills.git
cd common-skills
```

- [ ] **Step 2: Create stack.yaml**

```yaml
name: common-skills
namespace: agentic-stacks
version: 0.1.0
description: >
  Cross-cutting skills for all agentic stacks projects — interactive training,
  guided walkthroughs, project orientation, and operational feedback capture.

repository: https://github.com/agentic-stacks/common-skills

target:
  software: agentic-stacks
  versions:
    - "all"

skills:
  - name: training
    entry: skills/training/
    description: Interactive training — teaches domain knowledge from any pulled stack

  - name: guide
    entry: skills/guide/
    description: Wizard-style guided walkthroughs — assesses environment, builds tailored plans

  - name: orientation
    entry: skills/orientation/
    description: Project overview — reads all pulled stacks and summarizes capabilities

  - name: feedback
    entry: skills/feedback/
    description: Capture operational learnings and write them to domain stacks for upstream contribution

depends_on: []

requires:
  tools: []
```

- [ ] **Step 3: Create CLAUDE.md**

```markdown
# Common Skills

You are a learning and project assistant. You help users learn from their stacks, get guided through tasks, understand what's available, and capture operational learnings.

## Routing Table

| Need | Skill | Entry |
|---|---|---|
| Learn / Train | training | `skills/training/` |
| Walk me through a task | guide | `skills/guide/` |
| What can you help me with? | orientation | `skills/orientation/` |
| Capture a learning / fix | feedback | `skills/feedback/` |

## How These Skills Work

These skills are **cross-cutting** — they work with whatever domain stacks are pulled into the project. Training uses domain stack skills as source material. Guide reads domain stack workflows to build plans. Orientation reads all pulled stacks to give a unified overview. Feedback writes learnings to the appropriate domain stack.
```

- [ ] **Step 4: Create README.md**

```markdown
# common-skills

An [agentic stack](https://github.com/agentic-stacks/agentic-stacks) that provides cross-cutting skills for all projects — interactive training, guided walkthroughs, project orientation, and operational feedback capture.

Pulled automatically when you run `agentic-stacks init`. Can be removed with `agentic-stacks remove common-skills`.

## Skills

| Skill | Description |
|-------|-------------|
| **training** | Interactive teaching mode — assesses your knowledge, builds a curriculum from pulled stacks, teaches with exercises and quizzes |
| **guide** | Guided walkthroughs — asks about your environment, builds a tailored step-by-step plan, walks you through it |
| **orientation** | Project overview — reads all pulled stacks and summarizes what's available, suggests starting points |
| **feedback** | Capture learnings — writes fixes, workarounds, and notes to the right place in domain stacks for upstream contribution |

## Usage

These skills activate automatically when you talk to your agent:

```
> train me on this stack
> guide me through deploying Kubernetes
> what can you help me with?
> capture that NTP fix we just did
```

## Opting Out

```bash
# Skip during init
agentic-stacks init my-project --no-common

# Remove after init
agentic-stacks remove common-skills
```
```

- [ ] **Step 5: Create skills/training/README.md**

```markdown
# Training Mode

When the user asks to be trained on a stack, switch from task-execution
mode to teaching mode. Use the domain stack's skills as your source material.

## Getting Started

1. **Assess the learner.** Ask what they already know about the domain and
   related technologies. Adjust depth accordingly.

2. **Build a curriculum.** Read every skill in the relevant domain stack.
   Sequence them from foundational concepts to advanced operations. Present
   the learning path and let the user adjust it.

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
```

- [ ] **Step 6: Create skills/guide/README.md**

```markdown
# Guided Walkthrough

When the user asks to be guided through a task, switch to guided mode.
Read the domain stack's workflows and skills to build a tailored plan.

## Process

1. **Ask what they want to accomplish.** Understand the goal before
   jumping into steps. Examples: "deploy a Kubernetes cluster,"
   "set up RAID on these servers," "configure monitoring."

2. **Identify the right domain stack.** Read `.stacks/*/CLAUDE.md`
   to find which stack covers this task. If multiple stacks are
   relevant, note which parts come from which stack.

3. **Assess the environment.** Ask targeted questions:
   - How many hosts? What hardware?
   - What OS and version?
   - What's the network topology?
   - What's already deployed vs. starting fresh?
   - Any constraints (air-gapped, compliance, etc.)?

4. **Build a tailored plan.** Using the domain stack's workflows
   and the user's environment details, create a step-by-step plan.
   Reference specific skills for each step. Show the plan and let
   the user adjust before starting.

5. **Walk through each step.** For each step:
   - Explain what this step does and why
   - Show the exact commands or configuration
   - Confirm before executing anything destructive
   - Check: did it work? If not, route to the stack's diagnose skills

6. **Handle failures.** If a step fails:
   - Check the domain stack's diagnose skills for the symptom
   - Check known-issues for version-specific problems
   - Help troubleshoot before moving on

7. **Summarize.** At the end, recap:
   - What was accomplished
   - Current state of the environment
   - Next steps or recommended follow-up tasks

## Handling Specific Requests

- "Guide me through [task]" — start the full process from step 1.
- "What's the next step?" — continue from where you left off.
- "Skip this step" — move on, noting what was skipped.
- "Go back" — revisit the previous step.
```

- [ ] **Step 7: Create skills/orientation/README.md**

```markdown
# Project Orientation

When the user asks what's available, what they can do, or how to get
started, read all pulled stacks and give a unified overview.

## Process

1. **Scan all stacks.** Read `.stacks/*/CLAUDE.md` for every pulled
   stack in this project. Extract:
   - Stack name and domain
   - Identity (what it's an expert in)
   - Key capabilities from the routing table
   - Available workflows

2. **Present a unified summary.** For each stack, give a 1-2 sentence
   description of what it can help with, followed by its key capabilities.

3. **Highlight composition.** If multiple stacks are pulled, explain
   how they work together. Examples:
   - "hardware-dell + kubernetes-talos = bare metal Kubernetes deployment"
   - "openstack-kolla + ceph = OpenStack with Ceph-backed storage"
   - "ansible + hardware-dell = fleet-wide server management"

4. **Suggest starting points.** Based on what's pulled, recommend
   what the user might want to do first:
   - New to the domain? → "Try: train me on [stack]"
   - Ready to deploy? → "Try: guide me through [task]"
   - Have a specific question? → Just ask directly

5. **Mention available modes.** Let the user know they can:
   - **Train** — learn a domain interactively
   - **Guide** — get walked through a task step by step
   - **Operate** — just ask questions and get expert answers
   - **Capture** — document learnings for future reference

## Handling Specific Requests

- "What can you help me with?" — full orientation.
- "What stacks do I have?" — just list the stacks and their domains.
- "How do these stacks work together?" — focus on composition.
```

- [ ] **Step 8: Create skills/feedback/README.md**

```markdown
# Feedback Capture

When the user wants to capture a learning, fix, workaround, or
operational note, write it to the appropriate domain stack so it
can be contributed upstream.

## Process

1. **Understand what happened.** Ask:
   - What was the issue or discovery?
   - Which domain does it relate to? (Match to a pulled stack)
   - Is this a bug/workaround, a missing doc, or a process improvement?

2. **Find the right location.** Based on the type of feedback:
   - **Known issue / workaround** → `skills/reference/known-issues/` in the domain stack
   - **Missing or incorrect command** → the relevant skill file in the domain stack
   - **New operational procedure** → suggest creating a new skill or adding to an existing one
   - **Version-specific behavior** → the version-specific known-issues file

3. **Write the entry.** Use the domain stack's existing format:

   For known issues:
   ```markdown
   ### [Short Description]

   **Symptom:** What the operator sees
   **Cause:** Why it happens
   **Workaround:** Exact steps to fix it
   **Affected versions:** x.y.z through x.y.w
   **Status:** Open / Fixed in x.y.w
   ```

   For skill content updates, match the existing style of the target file.

4. **Show the diff.** After writing, show the user what changed:
   ```bash
   cd .stacks/[stack-name]
   git diff
   ```

5. **Explain upstream contribution.** Tell the user:
   - The change is in `.stacks/[stack-name]/` which is a clone of the upstream repo
   - They can fork, commit, and open a PR to contribute it back
   - Or they can open an issue describing the problem and fix

## Handling Specific Requests

- "Capture this" / "Document that" — start the feedback process.
- "Add this to known issues" — go directly to known-issues format.
- "Update the [skill] docs" — go directly to skill content update.
```

- [ ] **Step 9: Commit and push**

```bash
cd /Users/ant/Development/agentic-stacks/common-skills
git add .
git commit -m "feat: initial common-skills stack with training, guide, orientation, and feedback"
git push
```

- [ ] **Step 10: Validate with doctor**

```bash
cd /Users/ant/Development/agentic-stacks/agentic-stacks
source .venv/bin/activate
agentic-stacks doctor --path /Users/ant/Development/agentic-stacks/common-skills
```

---

### Task 2: Add `--no-common` flag and auto-pull to `init`

**Files:**
- Modify: `src/agentic_stacks_cli/commands/init.py`
- Test: `tests/test_cli_init.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_init.py`:

```python
from unittest.mock import patch, MagicMock


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_pulls_common_skills(mock_pull, tmp_path):
    """init auto-pulls common-skills by default."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    mock_pull.assert_called_once()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_no_common_flag(mock_pull, tmp_path):
    """--no-common skips the auto-pull."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--no-common", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    mock_pull.assert_not_called()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_common_skills_failure_non_fatal(mock_pull, tmp_path):
    """If common-skills pull fails, init still succeeds with a warning."""
    mock_pull.side_effect = Exception("Network unavailable")
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "proj" / "stacks.lock").exists()
    assert "common-skills" in result.output.lower() or "warning" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate
pytest tests/test_cli_init.py::test_init_pulls_common_skills tests/test_cli_init.py::test_init_no_common_flag tests/test_cli_init.py::test_init_common_skills_failure_non_fatal -v
```

Expected: FAIL — `_pull_common_skills` does not exist.

- [ ] **Step 3: Implement the changes in init.py**

Replace the contents of `src/agentic_stacks_cli/commands/init.py`:

```python
"""agentic-stacks init — scaffold an operator project."""

import pathlib

import click
import yaml


COMMON_SKILLS_REF = "agentic-stacks/common-skills"


def _pull_common_skills(stack_dir: pathlib.Path):
    """Auto-pull common-skills into the project."""
    from agentic_stacks_cli.commands.pull import _parse_ref, _clone_or_pull, _validate_repo_url
    from agentic_stacks_cli.config import load_config
    from agentic_stacks_cli.lock import read_lock, add_to_lock, write_lock
    from agentic_stacks_cli.registry_repo import ensure_registry, load_formula

    import subprocess

    namespace, name = _parse_ref(COMMON_SKILLS_REF)
    cfg = load_config()

    repo_url = None
    formula = None
    try:
        registry_path = ensure_registry(
            repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
        )
        formula = load_formula(registry_path, namespace, name)
        repo_url = formula["repository"]
    except Exception:
        pass

    if not repo_url:
        repo_url = f"https://github.com/{namespace}/{name}"

    dest = stack_dir / ".stacks" / name
    click.echo(f"Pulling {COMMON_SKILLS_REF}...")
    _validate_repo_url(repo_url)
    _clone_or_pull(repo_url, dest)
    click.echo(f"  → .stacks/{name}/")

    version = formula.get("version", "latest") if formula else "latest"
    commit_sha = ""
    if (dest / ".git").is_dir():
        result = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            commit_sha = result.stdout.strip()

    lock_path = stack_dir / "stacks.lock"
    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=COMMON_SKILLS_REF, version=version,
                       digest=commit_sha, registry=repo_url)
    for entry in lock["stacks"]:
        if entry["name"] == COMMON_SKILLS_REF:
            entry["repository"] = repo_url
    write_lock(lock, lock_path)


def _init_operator_project(stack_dir: pathlib.Path):
    """Scaffold a project directory with stacks.lock, .gitignore, CLAUDE.md."""
    lock = {"stacks": []}
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    project_name = stack_dir.name
    claude_md = (
        f"# {project_name}\n\n"
        f"This project uses agentic stacks for domain expertise.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads all stacks to .stacks/\n"
        f"```\n\n"
        f"## Discover Stacks\n\n"
        f"```bash\n"
        f"agentic-stacks search \"keyword\"  # find stacks\n"
        f"agentic-stacks pull <name>        # add a stack to this project\n"
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


@click.command()
@click.argument("path", required=False, default=None, type=click.Path())
@click.option("--no-common", is_flag=True, default=False,
              help="Skip auto-pulling common-skills.")
def init(path: str | None, no_common: bool):
    """Initialize a project.

    Works like git init — run in an existing directory or provide a path
    to create one. Add stacks later with 'agentic-stacks pull'.

    \b
    Examples:
      agentic-stacks init                  # init current directory
      agentic-stacks init my-deployment    # create and init my-deployment/
      agentic-stacks init --no-common      # skip common-skills
    """
    if path is None:
        stack_dir = pathlib.Path(".")
    else:
        stack_dir = pathlib.Path(path)
        stack_dir.mkdir(parents=True, exist_ok=True)

    # Don't re-init if already initialized
    if (stack_dir / "stacks.lock").exists():
        raise click.ClickException(
            f"Already initialized — {stack_dir / 'stacks.lock'} exists."
        )

    _init_operator_project(stack_dir)

    if not no_common:
        try:
            _pull_common_skills(stack_dir)
        except Exception as e:
            click.echo(f"  Warning: could not pull common-skills ({e})")
            click.echo(f"  Project initialized without common-skills.")

    click.echo(f"  Run 'agentic-stacks search' to discover stacks.")
    click.echo(f"  Run 'agentic-stacks pull <name>' to add one.")
```

- [ ] **Step 4: Run the new tests to verify they pass**

```bash
pytest tests/test_cli_init.py::test_init_pulls_common_skills tests/test_cli_init.py::test_init_no_common_flag tests/test_cli_init.py::test_init_common_skills_failure_non_fatal -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Run the full init test suite to check for regressions**

```bash
pytest tests/test_cli_init.py -v
```

Expected: all tests PASS. Some existing tests may need `@patch("agentic_stacks_cli.commands.init._pull_common_skills")` added if they fail due to the auto-pull attempting a real git clone.

- [ ] **Step 6: Fix any existing test regressions**

If existing init tests fail because `_pull_common_skills` tries to clone for real, add the mock decorator to each affected test:

```python
@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_creates_project_in_named_dir(mock_pull, tmp_path):
    # ... existing test body unchanged
```

- [ ] **Step 7: Run the full test suite**

```bash
pytest -v --tb=short
```

Expected: all 145+ tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/agentic_stacks_cli/commands/init.py tests/test_cli_init.py
git commit -m "feat: auto-pull common-skills on init, add --no-common flag"
```

---

### Task 3: Publish common-skills to registry

**Files:**
- None in this repo (registry operations)

- [ ] **Step 1: Publish the common-skills stack**

```bash
cd /Users/ant/Development/agentic-stacks/common-skills
source /Users/ant/Development/agentic-stacks/agentic-stacks/.venv/bin/activate
agentic-stacks publish --path .
```

This generates a formula YAML and submits it to the registry. The registry sync workflow will pick it up.

- [ ] **Step 2: Verify it's discoverable**

```bash
agentic-stacks search common-skills
```

Expected: common-skills appears in results.

- [ ] **Step 3: Test the full flow end-to-end**

```bash
cd /tmp
agentic-stacks init test-common-skills
ls test-common-skills/.stacks/common-skills/
cat test-common-skills/stacks.lock
```

Expected: `.stacks/common-skills/` exists with all four skills, `stacks.lock` has a `common-skills` entry.

- [ ] **Step 4: Test --no-common**

```bash
cd /tmp
agentic-stacks init test-no-common --no-common
ls test-no-common/.stacks/ 2>/dev/null || echo "No .stacks directory (expected)"
cat test-no-common/stacks.lock
```

Expected: no `.stacks/` directory, `stacks.lock` has empty stacks list.

- [ ] **Step 5: Test remove**

```bash
cd /tmp/test-common-skills
agentic-stacks remove common-skills
ls .stacks/ 2>/dev/null || echo "No .stacks directory (expected)"
cat stacks.lock
```

Expected: common-skills removed from `.stacks/` and `stacks.lock`.

- [ ] **Step 6: Commit CLI changes and push**

```bash
cd /Users/ant/Development/agentic-stacks/agentic-stacks
git push
```

- [ ] **Step 7: Clean up test directories**

```bash
rm -rf /tmp/test-common-skills /tmp/test-no-common
```
