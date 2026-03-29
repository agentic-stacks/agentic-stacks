# Simplified Operator Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators create projects that extend published stacks (`agentic-stacks init my-cloud --from agentic-stacks/openstack-kolla@1.3.0`), scaffolding a multi-environment project where the agent guides them through building their deployment config based on the stack's captured domain expertise.

**Architecture:** A stack declares a `project` field in `stack.yaml` describing what an operator project looks like (which directories per environment, what config is needed). `init --from` reads this to scaffold the project, generates a CLAUDE.md wiring the agent to the stack's skills, and creates `stacks.lock`. The operator then works *with* the agent — the agent reads the stack's skills to know the domain, reads the operator's config to know specifics. The profile engine and merge machinery stay as internal tools for stack authors, not exposed to operators.

**Tech Stack:** Python, PyYAML, Click, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/agentic_stacks/manifest.py` | Modify | Parse `project` field and `extends` field in stack.yaml |
| `src/agentic_stacks_cli/commands/init.py` | Modify | Add `--from` option, scaffold operator project from stack's `project` spec |
| `src/agentic_stacks_cli/commands/doctor.py` | Modify | Validate operator projects (check extends, parent stack, environments) |
| `tests/fixtures/parent-stack/` | Create | Fixture: a stack with a `project` field |
| `tests/test_manifest_project.py` | Create | Tests for project field parsing |
| `tests/test_cli_init_from.py` | Create | Tests for `init --from` scaffolding |
| `tests/test_cli_doctor_operator.py` | Create | Tests for doctor on operator projects |

---

### Task 1: Parse `project` Field in Manifest

Add support for the `project` field in `stack.yaml` that declares what an operator project looks like.

**Files:**
- Modify: `src/agentic_stacks/manifest.py`
- Create: `tests/fixtures/parent-stack/stack.yaml`
- Create: `tests/fixtures/parent-stack/skills/deploy/README.md`
- Create: `tests/fixtures/parent-stack/skills/health-check/README.md`
- Create: `tests/fixtures/parent-stack/profiles/security/baseline.yml`
- Create: `tests/fixtures/parent-stack/environments/_schema.json`
- Create: `tests/test_manifest_project.py`

- [ ] **Step 1: Create parent-stack fixture**

Create `tests/fixtures/parent-stack/stack.yaml`:

```yaml
name: openstack-kolla
namespace: agentic-stacks
version: "1.3.0"
description: "Agent-driven OpenStack deployment on kolla-ansible"

target:
  software: openstack
  versions: ["2024.2", "2025.1"]

skills:
  - name: deploy
    entry: skills/deploy/
    description: "Runs kolla-ansible deploy lifecycle"
  - name: health-check
    entry: skills/health-check/
    description: "Validates environment health"

profiles:
  categories: [security, networking, storage, scale]
  path: profiles/
  merge_order: "security first (enforced), then declared order"

environment_schema: environments/_schema.json

project:
  environments: true
  per_environment:
    - config.yml
    - inventory/
    - files/
    - secrets/

docs_sources:
  - https://docs.openstack.org/kolla-ansible/latest/

depends_on: []
requires:
  tools: [kolla-ansible, openstack-cli]
  python: ">=3.11"
deprecations: []
```

Create `tests/fixtures/parent-stack/skills/deploy/README.md`:

```markdown
# Deploy Skill
Placeholder for testing.
```

Create `tests/fixtures/parent-stack/skills/health-check/README.md`:

```markdown
# Health Check Skill
Placeholder for testing.
```

Create `tests/fixtures/parent-stack/profiles/security/baseline.yml`:

```yaml
security:
  level: baseline
  tls_required: true
```

Create `tests/fixtures/parent-stack/environments/_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name"]
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_manifest_project.py`:

```python
import pathlib
import pytest
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_manifest_with_project_field():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert manifest["name"] == "openstack-kolla"
    assert "project" in manifest
    assert manifest["project"]["environments"] is True
    assert "config.yml" in manifest["project"]["per_environment"]
    assert "inventory/" in manifest["project"]["per_environment"]
    assert "files/" in manifest["project"]["per_environment"]
    assert "secrets/" in manifest["project"]["per_environment"]


def test_manifest_with_docs_sources():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert "docs_sources" in manifest
    assert "kolla-ansible" in manifest["docs_sources"][0]


def test_manifest_without_project_gets_default():
    manifest = load_manifest(FIXTURES / "sample-stack" / "stack.yaml")
    assert manifest["project"] == {}


def test_manifest_with_extends_field(tmp_path):
    data = {
        "name": "my-cloud", "namespace": "blahfoo",
        "version": "1.0.0", "description": "My cloud",
        "extends": {
            "name": "openstack-kolla",
            "namespace": "agentic-stacks",
            "version": "^1.3",
        },
    }
    path = tmp_path / "stack.yaml"
    path.write_text(yaml.dump(data))
    manifest = load_manifest(path)
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "^1.3"


def test_manifest_without_extends_gets_none():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert manifest.get("extends") is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_manifest_project.py -v`
Expected: `test_manifest_without_project_gets_default` fails — no default for `project`

- [ ] **Step 4: Add defaults for project and extends in manifest.py**

In `src/agentic_stacks/manifest.py`, add after line 51 (`manifest.setdefault("target", ...)`):

```python
    manifest.setdefault("project", {})
    manifest.setdefault("docs_sources", [])
    if "extends" not in manifest:
        manifest["extends"] = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_manifest_project.py tests/test_manifest.py -v`
Expected: All tests PASS (new + existing)

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks/manifest.py tests/test_manifest_project.py \
  tests/fixtures/parent-stack/
git commit -m "feat: parse project, docs_sources, and extends fields in stack manifest"
```

---

### Task 2: `init --from` Scaffolds Operator Project

Add `--from` option that reads the base stack's manifest (from the registry API) to scaffold a multi-environment operator project.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/init.py`
- Create: `tests/test_cli_init_from.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_init_from.py`:

```python
import pathlib
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_init_from_creates_structure(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])
    assert result.exit_code == 0, result.output

    assert (target / "stack.yaml").exists()
    assert (target / "environments").is_dir()
    assert (target / "state").is_dir()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()
    assert (target / "CLAUDE.md").exists()

    # Operator projects do NOT have skills/ or profiles/
    assert not (target / "skills").exists()
    assert not (target / "profiles").exists()


def test_init_from_stack_yaml_has_extends(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    manifest = yaml.safe_load((target / "stack.yaml").read_text())
    assert manifest["name"] == "my-cloud"
    assert manifest["namespace"] == "blahfoo"
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "1.3.0"


def test_init_from_creates_example_environment(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    example_env = target / "environments" / "example"
    assert example_env.is_dir()
    assert (example_env / "config.yml").exists()
    assert (example_env / "inventory").is_dir()
    assert (example_env / "files").is_dir()
    assert (example_env / "secrets").is_dir()

    config = yaml.safe_load((example_env / "config.yml").read_text())
    assert config["name"] == "example"


def test_init_from_stacks_lock(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    lock = yaml.safe_load((target / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["version"] == "1.3.0"


def test_init_from_gitignore(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    content = (target / ".gitignore").read_text()
    assert ".stacks/" in content


def test_init_from_claude_md_references_stack(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    claude = (target / "CLAUDE.md").read_text()
    assert "openstack-kolla" in claude
    assert ".stacks/" in claude
    assert "deploy" in claude.lower()


def test_init_from_no_project_field_uses_defaults(tmp_path):
    """A stack without a project field still works — just no per_environment dirs."""
    target = tmp_path / "my-stack"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-thing",
        "--namespace", "myorg",
        "--from", f"{FIXTURES / 'sample-stack'}",
    ])
    assert result.exit_code == 0, result.output
    assert (target / "stack.yaml").exists()
    assert (target / "environments").is_dir()

    example_env = target / "environments" / "example"
    assert example_env.is_dir()
    assert (example_env / "config.yml").exists()
    # No inventory/ etc. because sample-stack has no project.per_environment
    assert not (example_env / "inventory").exists()


def test_init_without_from_unchanged(tmp_path):
    """Existing init behavior is not affected."""
    target = tmp_path / "regular-stack"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-stack",
        "--namespace", "test",
    ])
    assert result.exit_code == 0
    assert (target / "skills").is_dir()
    assert (target / "profiles").is_dir()

    manifest = yaml.safe_load((target / "stack.yaml").read_text())
    assert manifest.get("extends") is None


def test_init_from_bad_path(tmp_path):
    target = tmp_path / "bad"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "x",
        "--namespace", "y",
        "--from", "/nonexistent/path",
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_init_from.py -v`
Expected: Error — `--from` option doesn't exist

- [ ] **Step 3: Implement --from in init.py**

Replace `src/agentic_stacks_cli/commands/init.py`:

```python
"""astack init — scaffold a new stack or operator project."""

import json
import pathlib

import click
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError


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


@click.command()
@click.argument("path", type=click.Path())
@click.option("--name", required=True, help="Stack name")
@click.option("--namespace", required=True, help="Stack namespace (e.g., org name)")
@click.option("--from", "from_stack", default=None,
              help="Base stack to extend — path to local stack dir or namespace/name@version")
def init(path: str, name: str, namespace: str, from_stack: str | None):
    """Scaffold a new stack or operator project."""
    stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)

    if from_stack:
        _init_operator_project(stack_dir, name, namespace, from_stack)
    else:
        _init_stack(stack_dir, name, namespace)


def _init_stack(stack_dir: pathlib.Path, name: str, namespace: str):
    """Scaffold a new stack (original behavior)."""
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
        "namespace": namespace,
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

    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    claude_md = f"# {name}\n\nStack: {namespace}/{name}\n\nRun `agentic-stacks doctor` to validate.\n"
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized stack '{namespace}/{name}' at {stack_dir}")


def _init_operator_project(stack_dir: pathlib.Path, name: str, namespace: str,
                           from_stack: str):
    """Scaffold an operator project that extends a base stack."""
    # Load the base stack manifest
    from_path = pathlib.Path(from_stack)
    if from_path.is_dir():
        manifest_path = from_path / "stack.yaml"
    else:
        raise click.ClickException(
            f"Stack path not found: {from_stack}. "
            "Pass a local path to a stack directory."
        )

    try:
        parent = load_manifest(manifest_path)
    except ManifestError as e:
        raise click.ClickException(f"Invalid base stack: {e}")

    parent_name = parent["name"]
    parent_namespace = parent["namespace"]
    parent_version = parent["version"]
    project_spec = parent.get("project", {})
    per_env = project_spec.get("per_environment", [])

    # Create directories
    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()
    (stack_dir / "state").mkdir()

    # Scaffold example environment
    example_env = envs_dir / "example"
    example_env.mkdir()

    example_config = {
        "name": "example",
        "description": f"Example environment — edit this for your deployment",
    }
    with open(example_env / "config.yml", "w") as f:
        yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)

    # Create per-environment directories from parent's project spec
    for item in per_env:
        if item.endswith("/"):
            (example_env / item.rstrip("/")).mkdir(exist_ok=True)

    # Operator's stack.yaml with extends
    operator_manifest = {
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"{name} — extends {parent_namespace}/{parent_name}",
        "extends": {
            "name": parent_name,
            "namespace": parent_namespace,
            "version": parent_version,
        },
        "depends_on": [],
        "deprecations": [],
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(operator_manifest, f, default_flow_style=False, sort_keys=False)

    # stacks.lock
    lock = {
        "stacks": [{
            "name": f"{parent_namespace}/{parent_name}",
            "version": parent_version,
            "digest": "",
            "registry": f"ghcr.io/{parent_namespace}/{parent_name}:{parent_version}",
        }]
    }
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    # .gitignore
    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n.venv/\n")

    # CLAUDE.md — wires the agent to the stack's skills
    skills_list = parent.get("skills", [])
    skills_md = ""
    if skills_list:
        skills_md = "\n## Available Skills\n\n"
        for skill in skills_list:
            skills_md += f"- **{skill['name']}** — {skill.get('description', '')}\n"

    per_env_md = ""
    if per_env:
        per_env_md = "\n## Environment Structure\n\nEach environment in `environments/` contains:\n\n"
        per_env_md += "- `config.yml` — your deployment choices\n"
        for item in per_env:
            if item != "config.yml":
                per_env_md += f"- `{item}` — edit as needed for your deployment\n"

    claude_md = (
        f"# {name}\n\n"
        f"Operator project extending "
        f"`{parent_namespace}/{parent_name}@{parent_version}`.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads the base stack to .stacks/\n"
        f"```\n\n"
        f"## How This Works\n\n"
        f"The base stack's skills are in "
        f"`.stacks/{parent_namespace}/{parent_name}/{parent_version}/skills/`. "
        f"Read them to understand how to deploy, configure, and operate "
        f"{parent.get('target', {}).get('software', 'this software')}.\n\n"
        f"The stack's CLAUDE.md at "
        f"`.stacks/{parent_namespace}/{parent_name}/{parent_version}/CLAUDE.md` "
        f"is the primary guide — it describes what config is needed, "
        f"where files go, and how the automation works.\n\n"
        f"Work with the operator to build out each environment.\n"
        f"{skills_md}"
        f"{per_env_md}"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized operator project '{namespace}/{name}' at {stack_dir}")
    click.echo(f"  Extends: {parent_namespace}/{parent_name}@{parent_version}")
    click.echo(f"  Run 'agentic-stacks pull' to download the base stack.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_init_from.py tests/test_cli_init.py -v`
Expected: All tests PASS (new + existing init tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/init.py tests/test_cli_init_from.py
git commit -m "feat: add init --from — scaffold operator project from base stack"
```

---

### Task 3: Doctor Validates Operator Projects

Update doctor to understand operator projects — check extends reference, verify parent stack is pulled, validate environment structure.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/doctor.py`
- Create: `tests/test_cli_doctor_operator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_doctor_operator.py`:

```python
import json
import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_operator_project(path, parent_pulled=False):
    """Helper to create a minimal operator project for testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "my-cloud", "namespace": "blahfoo",
        "version": "0.1.0", "description": "My cloud",
        "extends": {
            "name": "openstack-kolla",
            "namespace": "agentic-stacks",
            "version": "1.3.0",
        },
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "environments").mkdir()
    (path / "state").mkdir()

    env = path / "environments" / "prod"
    env.mkdir()
    (env / "config.yml").write_text(yaml.dump({"name": "prod"}))

    if parent_pulled:
        parent_dir = (path / ".stacks" / "agentic-stacks" /
                      "openstack-kolla" / "1.3.0")
        parent_dir.mkdir(parents=True)
        parent_manifest = {
            "name": "openstack-kolla", "namespace": "agentic-stacks",
            "version": "1.3.0", "description": "Parent stack",
            "skills": [{"name": "deploy", "entry": "skills/deploy/",
                        "description": "Deploy"}],
            "project": {
                "environments": True,
                "per_environment": ["config.yml", "inventory/", "files/"],
            },
        }
        (parent_dir / "stack.yaml").write_text(
            yaml.dump(parent_manifest, sort_keys=False))
        (parent_dir / "skills").mkdir()
        (parent_dir / "skills" / "deploy").mkdir()


def test_doctor_operator_project_with_parent(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    assert result.exit_code == 0
    assert "extends" in result.output.lower() or "openstack-kolla" in result.output


def test_doctor_operator_project_missing_parent(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    # Should warn but not fail
    assert result.exit_code == 0
    assert "pull" in result.output.lower()


def test_doctor_operator_project_lists_environments(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    assert "prod" in result.output


def test_doctor_still_works_for_regular_stacks(tmp_path):
    """Existing doctor behavior unaffected."""
    path = tmp_path / "stack"
    path.mkdir()
    manifest = {
        "name": "test", "namespace": "testorg", "version": "1.0.0",
        "description": "Test",
        "skills": [{"name": "deploy", "entry": "skills/deploy/",
                    "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(
        json.dumps({"type": "object", "required": ["name"]}))

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(path)])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_doctor_operator.py -v`
Expected: `test_doctor_operator_project_missing_parent` fails — doctor doesn't check extends

- [ ] **Step 3: Implement operator-aware doctor**

Replace `src/agentic_stacks_cli/commands/doctor.py`:

```python
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
    )
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_doctor_operator.py tests/test_cli_doctor.py -v`
Expected: All tests PASS (new + existing)

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/doctor.py tests/test_cli_doctor_operator.py
git commit -m "feat: doctor validates operator projects — checks extends, parent, environments"
```

---

### Task 4: Full Test Suite + Docs

Run the complete test suite, manually test the CLI, update CLAUDE.md.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Manual CLI test**

```bash
# Scaffold an operator project from the test fixture
.venv/bin/agentic-stacks init /tmp/test-cloud \
  --name my-cloud --namespace blahfoo \
  --from tests/fixtures/parent-stack

# Inspect
cat /tmp/test-cloud/stack.yaml
cat /tmp/test-cloud/CLAUDE.md
cat /tmp/test-cloud/stacks.lock
ls -la /tmp/test-cloud/environments/example/

# Doctor it (should warn about missing parent)
.venv/bin/agentic-stacks doctor --path /tmp/test-cloud

# Cleanup
rm -rf /tmp/test-cloud
```

- [ ] **Step 3: Update CLAUDE.md**

Add to the end of `CLAUDE.md`:

```markdown
## Operator Projects

`agentic-stacks init --from <stack-path>` scaffolds an operator project that extends a base stack. The operator project has `environments/`, `state/`, and `stacks.lock` but no `skills/` or `profiles/` — those come from the parent stack in `.stacks/`.

The stack's `project` field in `stack.yaml` declares what each environment directory should contain (`config.yml`, `inventory/`, `files/`, `secrets/`, etc.). The generated `CLAUDE.md` wires the agent to the stack's skills.

The agent reads the parent stack's skills to know the domain and the operator's config to know specifics. The operator works with the agent to build out their deployment iteratively.

`doctor` detects operator projects (via the `extends` field) and validates: parent stack is pulled, environments exist, state directory present.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add operator projects section to CLAUDE.md"
```
