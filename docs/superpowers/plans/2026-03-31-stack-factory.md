# Stack Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `agentic-stacks/stack-factory` repo — a CLI + GitHub Actions pipeline that scaffolds new agentic stack repos from a managed queue, then guides local Claude Code sessions to fill them with researched content.

**Architecture:** Python CLI (Click) manages a `queue.yaml` file and orchestrates repo scaffolding via `gh` CLI. GitHub Actions handle community intake (issue -> queue) and scaffold triggering. A `.factory/` directory dropped into each scaffolded repo contains a CLAUDE.md skill and research plan that guide the local authoring session.

**Tech Stack:** Python 3.12+, Click, PyYAML, Jinja2, GitHub CLI (`gh`), GitHub Actions

---

## File Structure

```
agentic-stacks/stack-factory/
├── pyproject.toml                          # Package config, click entrypoint
├── README.md                               # Repo docs
├── CLAUDE.md                               # Instructions for Claude Code working on THIS repo
├── queue.yaml                              # Stack queue (pre-loaded with 11 stacks)
├── factory/
│   ├── __init__.py                         # Package init
│   ├── cli.py                              # Click group + commands
│   ├── queue.py                            # Queue read/write/query
│   ├── scaffold.py                         # Scaffold orchestration
│   └── github.py                           # gh CLI subprocess wrappers
├── skill/
│   └── CLAUDE.md                           # Authoring skill template (Jinja2)
├── templates/
│   └── research-plan.yaml.j2              # Research plan template
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── stack-request.yml              # Community request form
│   └── workflows/
│       ├── intake.yml                      # Issue approved → queue
│       └── scaffold.yml                    # Dispatch → scaffold repo
└── tests/
    ├── __init__.py
    ├── test_queue.py                       # Queue CRUD tests
    ├── test_scaffold.py                    # Scaffold logic tests
    └── test_cli.py                         # CLI integration tests
```

---

### Task 1: Bootstrap the Repository

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `CLAUDE.md`
- Create: `factory/__init__.py`

- [ ] **Step 1: Clone the empty repo**

```bash
cd /Users/ant/Development/agentic-stacks
gh repo clone agentic-stacks/stack-factory
cd stack-factory
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stack-factory"
version = "0.1.0"
description = "Automated pipeline for creating agentic stacks at scale."
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [
    { name = "Agentic Stacks" },
]
dependencies = [
    "pyyaml>=6.0",
    "click>=8.1",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[project.scripts]
factory = "factory.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["factory"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create factory/__init__.py**

```python
"""Stack Factory — automated pipeline for creating agentic stacks."""
```

- [ ] **Step 4: Create tests/__init__.py**

```python
```

- [ ] **Step 5: Create README.md**

```markdown
# Stack Factory

Automated pipeline for creating [agentic stacks](https://github.com/agentic-stacks/agentic-stacks) at scale.

## How It Works

1. **Queue** — `queue.yaml` tracks which stacks need to be created
2. **Scaffold** — `factory scaffold <name>` creates an empty stack repo with a research plan
3. **Author** — clone the repo, run `claude`, and the `.factory/CLAUDE.md` skill guides the session

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# See what's in the queue
factory list

# Scaffold the next pending stack
factory scaffold --next

# Scaffold a specific stack
factory scaffold prometheus-grafana

# Add a new stack to the queue
factory add minio --target minio --description "S3-compatible object storage"

# Mark a stack as complete
factory complete prometheus-grafana
```

## Community Requests

Open an issue using the "Stack Request" template. Once approved by a maintainer, the stack enters the queue.
```

- [ ] **Step 6: Create CLAUDE.md**

```markdown
# Stack Factory

This repo is the stack factory — an automated pipeline for creating agentic stacks.

## Commands

```bash
pip install -e ".[dev]"
pytest -v --tb=short
factory --help
```

## Architecture

- `factory/` — Click CLI package
  - `cli.py` — CLI commands (list, add, scaffold, approve, status, complete)
  - `queue.py` — Queue CRUD for queue.yaml
  - `scaffold.py` — Scaffold orchestration (creates repos, drops .factory/ into them)
  - `github.py` — gh CLI subprocess wrappers
- `skill/CLAUDE.md` — Jinja2 template for the authoring skill placed in scaffolded repos
- `templates/research-plan.yaml.j2` — Jinja2 template for per-stack research plans
- `queue.yaml` — source of truth for stack queue
```

- [ ] **Step 7: Create venv and install**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml README.md CLAUDE.md factory/__init__.py tests/__init__.py
git commit -m "feat: bootstrap stack-factory repo"
```

---

### Task 2: Queue Module

**Files:**
- Create: `factory/queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write failing tests for queue operations**

```python
# tests/test_queue.py
import tempfile
import pathlib
import pytest
from factory.queue import Queue


@pytest.fixture
def queue_file(tmp_path):
    """Create a queue.yaml with two entries."""
    f = tmp_path / "queue.yaml"
    f.write_text(
        "stacks:\n"
        "  - name: ansible\n"
        "    owner: agentic-stacks\n"
        "    description: Fleet automation\n"
        "    target_software:\n"
        "      - ansible\n"
        "    status: pending\n"
        "    issue: null\n"
        "    repo: null\n"
        "    created: '2026-03-31'\n"
        "  - name: terraform\n"
        "    owner: agentic-stacks\n"
        "    description: IaC provisioning\n"
        "    target_software:\n"
        "      - terraform\n"
        "    status: scaffolded\n"
        "    issue: null\n"
        "    repo: https://github.com/agentic-stacks/terraform\n"
        "    created: '2026-03-31'\n"
    )
    return f


@pytest.fixture
def empty_queue(tmp_path):
    f = tmp_path / "queue.yaml"
    f.write_text("stacks: []\n")
    return f


def test_list_all(queue_file):
    q = Queue(queue_file)
    stacks = q.list()
    assert len(stacks) == 2
    assert stacks[0]["name"] == "ansible"
    assert stacks[1]["name"] == "terraform"


def test_get_existing(queue_file):
    q = Queue(queue_file)
    entry = q.get("ansible")
    assert entry["name"] == "ansible"
    assert entry["status"] == "pending"


def test_get_missing(queue_file):
    q = Queue(queue_file)
    assert q.get("nonexistent") is None


def test_next_pending(queue_file):
    q = Queue(queue_file)
    entry = q.next_pending()
    assert entry["name"] == "ansible"
    assert entry["status"] == "pending"


def test_next_pending_empty(empty_queue):
    q = Queue(empty_queue)
    assert q.next_pending() is None


def test_add(empty_queue):
    q = Queue(empty_queue)
    q.add(
        name="minio",
        owner="agentic-stacks",
        description="S3-compatible object storage",
        target_software=["minio"],
    )
    stacks = q.list()
    assert len(stacks) == 1
    assert stacks[0]["name"] == "minio"
    assert stacks[0]["status"] == "pending"
    assert stacks[0]["target_software"] == ["minio"]


def test_add_duplicate(queue_file):
    q = Queue(queue_file)
    with pytest.raises(ValueError, match="already exists"):
        q.add(
            name="ansible",
            owner="agentic-stacks",
            description="duplicate",
            target_software=["ansible"],
        )


def test_update_status(queue_file):
    q = Queue(queue_file)
    q.update_status("ansible", "scaffolded", repo="https://github.com/agentic-stacks/ansible")
    entry = q.get("ansible")
    assert entry["status"] == "scaffolded"
    assert entry["repo"] == "https://github.com/agentic-stacks/ansible"


def test_update_status_missing(queue_file):
    q = Queue(queue_file)
    with pytest.raises(ValueError, match="not found"):
        q.update_status("nonexistent", "scaffolded")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_queue.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'factory.queue'`

- [ ] **Step 3: Implement queue module**

```python
# factory/queue.py
"""Queue management for stack-factory."""

from datetime import date
from pathlib import Path

import yaml


class Queue:
    """Read and write queue.yaml."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> list[dict]:
        data = yaml.safe_load(self.path.read_text())
        return data.get("stacks", [])

    def _write(self, stacks: list[dict]):
        self.path.write_text(
            yaml.dump({"stacks": stacks}, default_flow_style=False, sort_keys=False)
        )

    def list(self) -> list[dict]:
        return self._read()

    def get(self, name: str) -> dict | None:
        for s in self._read():
            if s["name"] == name:
                return s
        return None

    def next_pending(self) -> dict | None:
        for s in self._read():
            if s["status"] == "pending":
                return s
        return None

    def add(
        self,
        name: str,
        owner: str,
        description: str,
        target_software: list[str],
        issue: int | None = None,
    ):
        stacks = self._read()
        if any(s["name"] == name for s in stacks):
            raise ValueError(f"Stack '{name}' already exists in the queue")
        stacks.append(
            {
                "name": name,
                "owner": owner,
                "description": description,
                "target_software": target_software,
                "status": "pending",
                "issue": issue,
                "repo": None,
                "created": str(date.today()),
            }
        )
        self._write(stacks)

    def update_status(self, name: str, status: str, **fields):
        stacks = self._read()
        for s in stacks:
            if s["name"] == name:
                s["status"] = status
                s.update(fields)
                self._write(stacks)
                return
        raise ValueError(f"Stack '{name}' not found in the queue")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_queue.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add factory/queue.py tests/test_queue.py
git commit -m "feat: add queue module with CRUD operations"
```

---

### Task 3: GitHub Wrapper Module

**Files:**
- Create: `factory/github.py`
- Create: `tests/test_github.py`

- [ ] **Step 1: Write failing tests for github wrappers**

The github module wraps `gh` CLI calls. Tests mock `subprocess.run` to avoid needing real GitHub access.

```python
# tests/test_github.py
from unittest.mock import patch, MagicMock
import pytest
from factory.github import create_repo, repo_exists


@patch("factory.github.subprocess.run")
def test_create_repo(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/agentic-stacks/test\n")
    url = create_repo("agentic-stacks", "test", "/tmp/test-dir")
    mock_run.assert_called_once_with(
        ["gh", "repo", "create", "agentic-stacks/test", "--public", "--source", "/tmp/test-dir", "--push"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert url == "https://github.com/agentic-stacks/test"


@patch("factory.github.subprocess.run")
def test_create_repo_failure(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="already exists")
    with pytest.raises(subprocess.CalledProcessError):
        create_repo("agentic-stacks", "test", "/tmp/test-dir")


@patch("factory.github.subprocess.run")
def test_repo_exists_true(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert repo_exists("agentic-stacks", "test") is True


@patch("factory.github.subprocess.run")
def test_repo_exists_false(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
    assert repo_exists("agentic-stacks", "test") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_github.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'factory.github'`

- [ ] **Step 3: Implement github module**

```python
# factory/github.py
"""GitHub CLI (gh) wrappers."""

import subprocess


def create_repo(owner: str, name: str, source_dir: str) -> str:
    """Create a public GitHub repo from a local directory and push.

    Returns the repo URL.
    """
    result = subprocess.run(
        [
            "gh", "repo", "create", f"{owner}/{name}",
            "--public", "--source", source_dir, "--push",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def repo_exists(owner: str, name: str) -> bool:
    """Check if a GitHub repo exists."""
    try:
        subprocess.run(
            ["gh", "repo", "view", f"{owner}/{name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_github.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add factory/github.py tests/test_github.py
git commit -m "feat: add github CLI wrapper module"
```

---

### Task 4: Scaffold Module

**Files:**
- Create: `factory/scaffold.py`
- Create: `skill/CLAUDE.md`
- Create: `templates/research-plan.yaml.j2`
- Create: `tests/test_scaffold.py`

- [ ] **Step 1: Create the authoring skill template**

This is a Jinja2 template that gets rendered with the stack's name and target software, then placed into the scaffolded repo as `.factory/CLAUDE.md`.

```markdown
{# skill/CLAUDE.md #}
# Stack Factory — Authoring Agent

## Identity

You are building the **{{ name }}** agentic stack for the `{{ owner }}` organization. Your job is to research the target software's official documentation and generate a complete, production-quality stack following the authoring guide.

## Research Plan

Read `.factory/research-plan.yaml` for target software, doc URLs, and version targets.

## Authoring Guide

Follow the authoring guide for quality standards and structure:
https://github.com/agentic-stacks/agentic-stacks/blob/main/docs/guides/authoring-a-stack.md

## Workflow

1. **Discover docs** — for each target software in the research plan, fetch llms.txt, sitemap.xml, and check the GitHub repo. Identify the two most recent major version lines.
2. **Design skill hierarchy** — based on what the software does, propose skill phases (foundation/deploy/operations/diagnose/reference). Present to operator for approval before proceeding.
3. **Research & generate skills** — for each skill, fetch the relevant doc pages, extract exact commands/configs/warnings, write the skill content following authoring guide templates.
4. **Generate CLAUDE.md** — write the stack's CLAUDE.md with identity, critical rules, routing table, and workflows. Base it on the actual skills you created.
5. **Generate stack.yaml** — update the manifest with all skills, target versions, and required tools.
6. **Validate** — run the authoring guide checklist:
   - All skills in stack.yaml have directories with README.md
   - No placeholders (TBD, TODO, FIXME) remain
   - All commands are exact and copy-pasteable
   - Safety warnings precede destructive operations
   - Routing table entries match skill paths

## Rules

- Every command must come from official docs — never reconstruct from memory
- Cover the current major version AND the previous major version
- Note version-specific differences explicitly with version markers
- Use authoring guide templates for consistent structure
- Ask the operator when you hit a design decision (e.g., which components to cover, how to organize complex topics)
- Include doc URLs as references in skills so they can be refreshed later
```

- [ ] **Step 2: Create the research plan template**

```yaml
# templates/research-plan.yaml.j2
name: {{ name }}
owner: {{ owner }}
target_software:
{% for sw in target_software %}
  - name: {{ sw }}
{% endfor %}
suggested_phases:
  - foundation
  - deploy
  - operations
  - diagnose
  - reference
notes: "{{ description }}"
```

- [ ] **Step 3: Write failing tests for scaffold**

```python
# tests/test_scaffold.py
import pathlib
from unittest.mock import patch, MagicMock
import yaml
import pytest
from factory.scaffold import scaffold_stack


@pytest.fixture
def queue_entry():
    return {
        "name": "test-stack",
        "owner": "agentic-stacks",
        "description": "A test stack for testing",
        "target_software": ["test-tool"],
        "status": "pending",
        "issue": None,
        "repo": None,
        "created": "2026-03-31",
    }


def test_scaffold_creates_directory_structure(tmp_path, queue_entry):
    """Scaffold creates the expected directory structure."""
    output_dir = tmp_path / "test-stack"
    with patch("factory.scaffold.SKILL_TEMPLATE", _read_template("skill/CLAUDE.md")):
        with patch("factory.scaffold.RESEARCH_TEMPLATE", _read_template("templates/research-plan.yaml.j2")):
            scaffold_stack(queue_entry, output_dir)

    assert (output_dir / "stack.yaml").exists()
    assert (output_dir / "CLAUDE.md").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "skills").is_dir()
    assert (output_dir / ".factory" / "CLAUDE.md").exists()
    assert (output_dir / ".factory" / "research-plan.yaml").exists()


def test_scaffold_research_plan_content(tmp_path, queue_entry):
    """Research plan contains the target software."""
    output_dir = tmp_path / "test-stack"
    with patch("factory.scaffold.SKILL_TEMPLATE", _read_template("skill/CLAUDE.md")):
        with patch("factory.scaffold.RESEARCH_TEMPLATE", _read_template("templates/research-plan.yaml.j2")):
            scaffold_stack(queue_entry, output_dir)

    plan = yaml.safe_load((output_dir / ".factory" / "research-plan.yaml").read_text())
    assert plan["name"] == "test-stack"
    assert plan["target_software"][0]["name"] == "test-tool"


def test_scaffold_factory_claude_md(tmp_path, queue_entry):
    """Factory CLAUDE.md is interpolated with stack name."""
    output_dir = tmp_path / "test-stack"
    with patch("factory.scaffold.SKILL_TEMPLATE", _read_template("skill/CLAUDE.md")):
        with patch("factory.scaffold.RESEARCH_TEMPLATE", _read_template("templates/research-plan.yaml.j2")):
            scaffold_stack(queue_entry, output_dir)

    content = (output_dir / ".factory" / "CLAUDE.md").read_text()
    assert "test-stack" in content
    assert "agentic-stacks" in content


def _read_template(path: str) -> str:
    """Read a template file relative to the repo root."""
    return (pathlib.Path(__file__).parent.parent / path).read_text()
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/test_scaffold.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'factory.scaffold'`

- [ ] **Step 5: Implement scaffold module**

```python
# factory/scaffold.py
"""Scaffold a new stack repo from a queue entry."""

import pathlib
import json

import yaml
from jinja2 import Template


_ROOT = pathlib.Path(__file__).parent.parent

SKILL_TEMPLATE = (_ROOT / "skill" / "CLAUDE.md").read_text()
RESEARCH_TEMPLATE = (_ROOT / "templates" / "research-plan.yaml.j2").read_text()

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


def scaffold_stack(entry: dict, output_dir: pathlib.Path):
    """Create a scaffolded stack directory from a queue entry.

    Creates the standard agentic-stacks structure plus a .factory/
    directory with the authoring skill and research plan.
    """
    name = entry["name"]
    owner = entry["owner"]
    description = entry["description"]
    target_software = entry["target_software"]

    output_dir.mkdir(parents=True, exist_ok=True)

    # Standard stack directories
    (output_dir / "skills").mkdir()
    (output_dir / "src").mkdir()
    (output_dir / "overrides").mkdir()

    profiles_dir = output_dir / "profiles"
    profiles_dir.mkdir()
    for category in PROFILE_CATEGORIES:
        (profiles_dir / category).mkdir()

    envs_dir = output_dir / "environments"
    envs_dir.mkdir()
    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    # stack.yaml
    manifest = {
        "name": name,
        "owner": owner,
        "version": "0.1.0",
        "description": description,
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
    with open(output_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    # CLAUDE.md (stack's own — will be rewritten by authoring session)
    claude_md = (
        f"# {name}\n\n"
        f"Stack: {owner}/{name}\n\n"
        f"## Authoring Guide\n\n"
        f"Follow the stack authoring guide to build this stack:\n"
        f"https://github.com/agentic-stacks/agentic-stacks/blob/main/docs/guides/authoring-a-stack.md\n\n"
        f"Run `agentic-stacks doctor` to validate.\n"
    )
    (output_dir / "CLAUDE.md").write_text(claude_md)

    # README.md
    readme = (
        f"# {name}\n\n"
        f"An [agentic stack](https://github.com/agentic-stacks/agentic-stacks) "
        f"that teaches AI agents how to operate {name}.\n\n"
        f"## Usage\n\n"
        f"```bash\n"
        f"agentic-stacks init {owner}/{name} my-project\n"
        f"cd my-project\n"
        f"agentic-stacks pull\n"
        f"```\n\n"
        f"Then start Claude Code — it reads `.stacks/{name}/CLAUDE.md` "
        f"and becomes an expert operator.\n"
    )
    (output_dir / "README.md").write_text(readme)

    # .factory/ directory
    factory_dir = output_dir / ".factory"
    factory_dir.mkdir()

    # Render and write authoring skill
    skill_content = Template(SKILL_TEMPLATE).render(
        name=name,
        owner=owner,
        description=description,
        target_software=target_software,
    )
    (factory_dir / "CLAUDE.md").write_text(skill_content)

    # Render and write research plan
    plan_content = Template(RESEARCH_TEMPLATE).render(
        name=name,
        owner=owner,
        description=description,
        target_software=target_software,
    )
    (factory_dir / "research-plan.yaml").write_text(plan_content)

    # .gitignore
    (output_dir / ".gitignore").write_text(
        "# Factory working files\n"
        ".venv/\n"
        "__pycache__/\n"
    )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_scaffold.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add factory/scaffold.py skill/CLAUDE.md templates/research-plan.yaml.j2 tests/test_scaffold.py
git commit -m "feat: add scaffold module with authoring skill and research plan templates"
```

---

### Task 5: CLI Commands

**Files:**
- Create: `factory/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI commands**

```python
# tests/test_cli.py
from click.testing import CliRunner
import yaml
import pytest
from factory.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def queue_dir(tmp_path):
    """Create a temp queue.yaml and return the directory."""
    q = tmp_path / "queue.yaml"
    q.write_text(
        "stacks:\n"
        "  - name: ansible\n"
        "    owner: agentic-stacks\n"
        "    description: Fleet automation\n"
        "    target_software:\n"
        "      - ansible\n"
        "    status: pending\n"
        "    issue: null\n"
        "    repo: null\n"
        "    created: '2026-03-31'\n"
        "  - name: terraform\n"
        "    owner: agentic-stacks\n"
        "    description: IaC provisioning\n"
        "    target_software:\n"
        "      - terraform\n"
        "    status: complete\n"
        "    issue: null\n"
        "    repo: https://github.com/agentic-stacks/terraform\n"
        "    created: '2026-03-31'\n"
    )
    return tmp_path


def test_list(runner, queue_dir):
    result = runner.invoke(cli, ["list", "--queue", str(queue_dir / "queue.yaml")])
    assert result.exit_code == 0
    assert "ansible" in result.output
    assert "pending" in result.output
    assert "terraform" in result.output
    assert "complete" in result.output


def test_add(runner, queue_dir):
    result = runner.invoke(
        cli,
        [
            "add", "minio",
            "--target", "minio",
            "--description", "S3-compatible object storage",
            "--queue", str(queue_dir / "queue.yaml"),
        ],
    )
    assert result.exit_code == 0
    assert "Added 'minio'" in result.output

    data = yaml.safe_load((queue_dir / "queue.yaml").read_text())
    assert any(s["name"] == "minio" for s in data["stacks"])


def test_add_duplicate(runner, queue_dir):
    result = runner.invoke(
        cli,
        [
            "add", "ansible",
            "--target", "ansible",
            "--description", "duplicate",
            "--queue", str(queue_dir / "queue.yaml"),
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_status(runner, queue_dir):
    result = runner.invoke(cli, ["status", "ansible", "--queue", str(queue_dir / "queue.yaml")])
    assert result.exit_code == 0
    assert "ansible" in result.output
    assert "pending" in result.output


def test_status_not_found(runner, queue_dir):
    result = runner.invoke(cli, ["status", "nonexistent", "--queue", str(queue_dir / "queue.yaml")])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_complete(runner, queue_dir):
    result = runner.invoke(cli, ["complete", "ansible", "--queue", str(queue_dir / "queue.yaml")])
    assert result.exit_code == 0
    assert "complete" in result.output

    data = yaml.safe_load((queue_dir / "queue.yaml").read_text())
    entry = next(s for s in data["stacks"] if s["name"] == "ansible")
    assert entry["status"] == "complete"


def test_approve(runner, queue_dir, tmp_path):
    """Test approve command adds to queue from issue fields."""
    result = runner.invoke(
        cli,
        [
            "approve",
            "--name", "redis",
            "--target", "redis",
            "--description", "In-memory data store",
            "--issue", "42",
            "--queue", str(queue_dir / "queue.yaml"),
        ],
    )
    assert result.exit_code == 0
    assert "Approved" in result.output

    data = yaml.safe_load((queue_dir / "queue.yaml").read_text())
    entry = next(s for s in data["stacks"] if s["name"] == "redis")
    assert entry["issue"] == 42
    assert entry["status"] == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'factory.cli'`

- [ ] **Step 3: Implement CLI**

```python
# factory/cli.py
"""Stack Factory CLI."""

from pathlib import Path

import click
import yaml

from factory.queue import Queue


def _default_queue() -> Path:
    return Path(__file__).parent.parent / "queue.yaml"


def _queue_option(f):
    return click.option(
        "--queue", type=click.Path(exists=True), default=None,
        help="Path to queue.yaml (default: repo root)",
    )(f)


@click.group()
def cli():
    """Stack Factory — automated pipeline for creating agentic stacks."""
    pass


@cli.command("list")
@_queue_option
def list_cmd(queue):
    """Show all stacks in the queue."""
    q = Queue(queue or _default_queue())
    stacks = q.list()
    if not stacks:
        click.echo("Queue is empty.")
        return

    # Column widths
    max_name = max(len(s["name"]) for s in stacks)
    max_status = max(len(s["status"]) for s in stacks)

    for s in stacks:
        click.echo(f"  {s['name']:<{max_name}}  {s['status']:<{max_status}}  {s['description']}")


@cli.command()
@click.argument("name")
@click.option("--target", required=True, help="Target software (comma-separated)")
@click.option("--description", required=True, help="Stack description")
@click.option("--owner", default="agentic-stacks", help="GitHub org/owner")
@_queue_option
def add(name, target, description, owner, queue):
    """Add a new stack to the queue."""
    q = Queue(queue or _default_queue())
    target_list = [t.strip() for t in target.split(",")]
    try:
        q.add(name=name, owner=owner, description=description, target_software=target_list)
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"Added '{name}' to the queue.")


@cli.command()
@click.argument("name")
@_queue_option
def status(name, queue):
    """Show details for a stack."""
    q = Queue(queue or _default_queue())
    entry = q.get(name)
    if entry is None:
        raise click.ClickException(f"Stack '{name}' not found in the queue.")

    click.echo(f"  Name:     {entry['name']}")
    click.echo(f"  Owner:    {entry['owner']}")
    click.echo(f"  Status:   {entry['status']}")
    click.echo(f"  Target:   {', '.join(entry['target_software'])}")
    click.echo(f"  Desc:     {entry['description']}")
    if entry.get("repo"):
        click.echo(f"  Repo:     {entry['repo']}")
    if entry.get("issue"):
        click.echo(f"  Issue:    #{entry['issue']}")


@cli.command()
@click.argument("name")
@_queue_option
def complete(name, queue):
    """Mark a stack as complete."""
    q = Queue(queue or _default_queue())
    try:
        q.update_status(name, "complete")
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"Marked '{name}' as complete.")


@cli.command()
@click.option("--name", required=True, help="Stack name")
@click.option("--target", required=True, help="Target software (comma-separated)")
@click.option("--description", required=True, help="Stack description")
@click.option("--issue", required=True, type=int, help="GitHub issue number")
@click.option("--owner", default="agentic-stacks", help="GitHub org/owner")
@_queue_option
def approve(name, target, description, issue, owner, queue):
    """Approve a stack request from a GitHub issue."""
    q = Queue(queue or _default_queue())
    target_list = [t.strip() for t in target.split(",")]
    try:
        q.add(
            name=name,
            owner=owner,
            description=description,
            target_software=target_list,
            issue=issue,
        )
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"Approved '{name}' from issue #{issue}.")


@cli.command()
@click.argument("name", required=False)
@click.option("--next", "use_next", is_flag=True, help="Scaffold the next pending stack")
@click.option("--output", type=click.Path(), default=None, help="Output directory (default: ./<name>)")
@click.option("--no-github", is_flag=True, help="Skip GitHub repo creation")
@_queue_option
def scaffold(name, use_next, output, no_github, queue):
    """Scaffold a stack repo from the queue."""
    from factory.scaffold import scaffold_stack
    from factory.github import create_repo, repo_exists
    from pathlib import Path

    q = Queue(queue or _default_queue())

    if use_next:
        entry = q.next_pending()
        if entry is None:
            raise click.ClickException("No pending stacks in the queue.")
    elif name:
        entry = q.get(name)
        if entry is None:
            raise click.ClickException(f"Stack '{name}' not found in the queue.")
        if entry["status"] != "pending":
            raise click.ClickException(
                f"Stack '{name}' has status '{entry['status']}', expected 'pending'."
            )
    else:
        raise click.ClickException("Provide a stack name or use --next.")

    stack_name = entry["name"]
    owner = entry["owner"]
    output_dir = Path(output) if output else Path(f"./{stack_name}")

    if output_dir.exists() and any(output_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {output_dir}")

    click.echo(f"Scaffolding {owner}/{stack_name}...")
    scaffold_stack(entry, output_dir)
    click.echo(f"  Created stack at {output_dir}")

    repo_url = None
    if not no_github:
        if repo_exists(owner, stack_name):
            click.echo(f"  GitHub repo {owner}/{stack_name} already exists, pushing...")
        click.echo(f"  Creating GitHub repo {owner}/{stack_name}...")
        repo_url = create_repo(owner, stack_name, str(output_dir))
        click.echo(f"  Repo: {repo_url}")

    q.update_status(stack_name, "scaffolded", repo=repo_url)
    click.echo(f"  Queue updated: {stack_name} → scaffolded")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add factory/cli.py tests/test_cli.py
git commit -m "feat: add CLI commands (list, add, status, complete, scaffold)"
```

---

### Task 6: Pre-Load the Initial Queue

**Files:**
- Create: `queue.yaml`

- [ ] **Step 1: Create queue.yaml with the 11 initial stacks**

```yaml
# queue.yaml
stacks:
  - name: ansible
    owner: agentic-stacks
    description: "Fleet automation — playbook patterns, inventory management, roles"
    target_software:
      - ansible
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: terraform
    owner: agentic-stacks
    description: "Infrastructure as Code provisioning — providers, state, modules"
    target_software:
      - terraform
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: proxmox
    owner: agentic-stacks
    description: "Hypervisor management — VM lifecycle, storage, networking, clustering"
    target_software:
      - proxmox
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: linux
    owner: agentic-stacks
    description: "OS-level operations — systemd, networking, storage, performance tuning"
    target_software:
      - linux
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: minio
    owner: agentic-stacks
    description: "S3-compatible object storage — deployment, buckets, replication, monitoring"
    target_software:
      - minio
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: zfs
    owner: agentic-stacks
    description: "ZFS storage management — pools, datasets, snapshots, scrubs, send/receive"
    target_software:
      - zfs
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: prometheus-grafana
    owner: agentic-stacks
    description: "Monitoring stack — Prometheus metrics collection, Grafana dashboards, alerting"
    target_software:
      - prometheus
      - grafana
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: loki
    owner: agentic-stacks
    description: "Log aggregation — Grafana Loki deployment, LogQL queries, retention"
    target_software:
      - loki
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: vault
    owner: agentic-stacks
    description: "Secrets management — Vault server, policies, secrets engines, PKI"
    target_software:
      - vault
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: keycloak
    owner: agentic-stacks
    description: "Identity and SSO — realm setup, client config, federation, themes"
    target_software:
      - keycloak
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"

  - name: opnsense
    owner: agentic-stacks
    description: "Network firewall/router — rules, VPN, DHCP, DNS, HA, plugins"
    target_software:
      - opnsense
    status: pending
    issue: null
    repo: null
    created: "2026-03-31"
```

- [ ] **Step 2: Verify queue loads correctly**

```bash
python3 -c "from factory.queue import Queue; q = Queue('queue.yaml'); print(f'{len(q.list())} stacks loaded'); [print(f'  {s[\"name\"]:20s} {s[\"status\"]}') for s in q.list()]"
```

Expected: 11 stacks, all pending

- [ ] **Step 3: Commit**

```bash
git add queue.yaml
git commit -m "feat: pre-load queue with 11 initial stacks from TODO"
```

---

### Task 7: GitHub Actions — Issue Template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/stack-request.yml`

- [ ] **Step 1: Create issue template**

```yaml
# .github/ISSUE_TEMPLATE/stack-request.yml
name: Stack Request
description: Request a new agentic stack to be created
labels: ["stack-request"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for requesting a new stack! Once approved by a maintainer,
        it will be added to the factory queue and scaffolded.
  - type: input
    id: name
    attributes:
      label: Stack name
      description: "Lowercase, hyphenated (e.g., prometheus-grafana)"
      placeholder: "my-stack"
    validations:
      required: true
  - type: input
    id: target_software
    attributes:
      label: Target software
      description: "Comma-separated list of software this stack covers"
      placeholder: "prometheus, grafana"
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: What should this stack cover?
      description: "Describe the key areas: deployment, operations, troubleshooting, etc."
      placeholder: "Monitoring stack — metrics collection, dashboarding, alerting rules..."
    validations:
      required: true
  - type: textarea
    id: context
    attributes:
      label: Additional context
      description: "Any links to docs, related stacks, or special considerations"
    validations:
      required: false
```

- [ ] **Step 2: Commit**

```bash
git add .github/ISSUE_TEMPLATE/stack-request.yml
git commit -m "feat: add stack request issue template"
```

---

### Task 8: GitHub Actions — Intake Workflow

**Files:**
- Create: `.github/workflows/intake.yml`

- [ ] **Step 1: Create intake workflow**

```yaml
# .github/workflows/intake.yml
name: Intake — Approved Stack Request

on:
  issues:
    types: [labeled]

jobs:
  intake:
    if: github.event.label.name == 'approved' && contains(github.event.issue.labels.*.name, 'stack-request')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install factory
        run: pip install -e .

      - name: Parse issue body
        id: parse
        uses: actions/github-script@v7
        with:
          script: |
            const body = context.payload.issue.body;
            const getName = (id) => {
              const match = body.match(new RegExp(`### ${id}\\s*\\n\\s*(.+)`));
              return match ? match[1].trim() : '';
            };
            core.setOutput('name', getName('Stack name'));
            core.setOutput('target', getName('Target software'));
            core.setOutput('description', getName('What should this stack cover\\?'));

      - name: Add to queue
        run: |
          factory approve \
            --name "${{ steps.parse.outputs.name }}" \
            --target "${{ steps.parse.outputs.target }}" \
            --description "${{ steps.parse.outputs.description }}" \
            --issue "${{ github.event.issue.number }}"

      - name: Commit queue update
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add queue.yaml
          git commit -m "feat: add ${{ steps.parse.outputs.name }} to queue (from #${{ github.event.issue.number }})"
          git push

      - name: Comment on issue
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `Added **${{ steps.parse.outputs.name }}** to the factory queue. It will be scaffolded when a maintainer triggers the scaffold workflow.`
            });
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/intake.yml
git commit -m "feat: add intake workflow for approved stack requests"
```

---

### Task 9: GitHub Actions — Scaffold Workflow

**Files:**
- Create: `.github/workflows/scaffold.yml`

- [ ] **Step 1: Create scaffold workflow**

```yaml
# .github/workflows/scaffold.yml
name: Scaffold Stack

on:
  workflow_dispatch:
    inputs:
      name:
        description: "Stack name from the queue (or leave empty for --next)"
        required: false
        default: ""

jobs:
  scaffold:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install factory
        run: pip install -e .

      - name: Scaffold stack
        env:
          GH_TOKEN: ${{ secrets.FACTORY_PAT }}
        run: |
          if [ -n "${{ inputs.name }}" ]; then
            factory scaffold "${{ inputs.name }}"
          else
            factory scaffold --next
          fi

      - name: Commit queue update
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add queue.yaml
          git diff --cached --quiet || (git commit -m "chore: update queue after scaffold" && git push)
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/scaffold.yml
git commit -m "feat: add scaffold workflow with manual dispatch"
```

---

### Task 10: Run Full Test Suite and Push

**Files:** None (validation only)

- [ ] **Step 1: Run the full test suite**

```bash
pytest -v --tb=short
```

Expected: all tests pass (queue: 8, github: 4, scaffold: 3, cli: 7 = 22 tests)

- [ ] **Step 2: Verify CLI works end-to-end**

```bash
factory list
factory status ansible
```

Expected: shows 11 stacks, ansible details

- [ ] **Step 3: Push to GitHub**

```bash
git push -u origin main
```

- [ ] **Step 4: Verify repo on GitHub**

```bash
gh repo view agentic-stacks/stack-factory
```
