# Phase 1b: `astack` CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `astack` CLI with three local commands: `init` (scaffold a new stack project), `doctor` (validate an existing stack), and `validate` (validate an environment against its schema). Registry commands (`pull`, `push`, `search`, `upgrade`) are Phase 2.

**Architecture:** The CLI is a thin wrapper using Click that calls into the `agentic_stacks` runtime library (Phase 1a). Each command is a module in `src/astack/commands/`. The CLI is distributed as the `agentic-stacks-cli` PyPI package and installs the `astack` binary.

**Tech Stack:** Python 3.11+, Click, agentic-stacks (the runtime from Phase 1a)

---

## File Structure

```
agentic-stacks/
├── src/
│   ├── agentic_stacks/          # (existing - Phase 1a runtime)
│   └── astack/                  # CLI package
│       ├── __init__.py           # main() entrypoint, Click group
│       └── commands/
│           ├── __init__.py
│           ├── init.py           # astack init — scaffold a new stack
│           ├── doctor.py         # astack doctor — validate a stack
│           └── validate.py       # astack validate — validate an environment
├── tests/
│   ├── test_cli_init.py
│   ├── test_cli_doctor.py
│   └── test_cli_validate.py
└── pyproject.toml               # (update: add click dep, astack entrypoint)
```

---

### Task 1: CLI Scaffold and `astack` Entrypoint

**Files:**
- Modify: `pyproject.toml` (add click, add astack entrypoint)
- Create: `src/astack/__init__.py`
- Create: `src/astack/commands/__init__.py`
- Create: `tests/test_cli_base.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cli_base.py
from click.testing import CliRunner
from astack import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "astack" in result.output.lower() or "usage" in result.output.lower()


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_base.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Update pyproject.toml**

Add to the existing `pyproject.toml`:

```toml
# Add click to dependencies (alongside existing pyyaml, jsonschema)
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.20",
    "click>=8.1",
]

# Add astack entrypoint
[project.scripts]
astack = "astack:main"
```

- [ ] **Step 4: Create CLI entrypoint**

```python
# src/astack/__init__.py
"""astack — CLI for Agentic Stacks."""

import click
import agentic_stacks


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="astack")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


def main():
    cli()
```

```python
# src/astack/commands/__init__.py
```

- [ ] **Step 5: Install updated package and run tests**

Run: `pip install -e ".[dev]" && pytest tests/test_cli_base.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/astack/ tests/test_cli_base.py
git commit -m "feat: astack CLI scaffold with click entrypoint"
```

---

### Task 2: `astack init` Command

**Files:**
- Create: `src/astack/commands/init.py`
- Modify: `src/astack/__init__.py` (register command)
- Create: `tests/test_cli_init.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_init.py
import yaml
from click.testing import CliRunner
from astack import cli


def test_init_creates_stack_structure(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "my-stack"), "--name", "my-stack", "--namespace", "myorg"])
    assert result.exit_code == 0

    stack_dir = tmp_path / "my-stack"
    assert (stack_dir / "stack.yaml").exists()
    assert (stack_dir / "skills").is_dir()
    assert (stack_dir / "profiles").is_dir()
    assert (stack_dir / "environments").is_dir()
    assert (stack_dir / "src").is_dir()
    assert (stack_dir / "CLAUDE.md").exists()


def test_init_stack_yaml_content(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "test-stack"), "--name", "test-stack", "--namespace", "testorg"])

    manifest = yaml.safe_load((tmp_path / "test-stack" / "stack.yaml").read_text())
    assert manifest["name"] == "test-stack"
    assert manifest["namespace"] == "testorg"
    assert manifest["version"] == "0.1.0"
    assert "skills" in manifest
    assert "profiles" in manifest


def test_init_existing_directory_fails(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "stack.yaml").write_text("name: existing\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target), "--name", "x", "--namespace", "y"])
    assert result.exit_code != 0
    assert "already exists" in result.output.lower() or "already" in result.output.lower()


def test_init_default_profiles(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "s"), "--name", "s", "--namespace", "n"])
    stack_dir = tmp_path / "s"
    assert (stack_dir / "profiles" / "security").is_dir()
    assert (stack_dir / "environments" / "_schema.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_init.py -v`
Expected: FAIL

- [ ] **Step 3: Implement init command**

```python
# src/astack/commands/init.py
"""astack init — scaffold a new stack project."""

import json
import pathlib

import click
import yaml


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
def init(path: str, name: str, namespace: str):
    """Scaffold a new stack project."""
    stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (stack_dir / "skills").mkdir()
    (stack_dir / "src").mkdir()
    (stack_dir / "overrides").mkdir()

    profiles_dir = stack_dir / "profiles"
    profiles_dir.mkdir()
    for category in PROFILE_CATEGORIES:
        (profiles_dir / category).mkdir()

    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()

    # Write stack.yaml
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

    # Write environment schema
    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    # Write CLAUDE.md
    claude_md = f"""# {name}

## Stack: {namespace}/{name}

This is an Agentic Stack — a bundle of skills, profiles, and automation
that provides domain expertise for AI agents and humans.

## Quick Start

- `skills/` — Markdown skill files that teach the agent what to do
- `profiles/` — Composable YAML configuration building blocks
- `environments/` — Declarative environment definitions
- `src/` — Automation code

## Validation

Run `astack doctor` to validate this stack.
"""
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized stack '{namespace}/{name}' at {stack_dir}")
```

- [ ] **Step 4: Register command in CLI**

Update `src/astack/__init__.py`:

```python
# src/astack/__init__.py
"""astack — CLI for Agentic Stacks."""

import click
import agentic_stacks

from astack.commands.init import init


@click.group()
@click.version_option(version=agentic_stacks.__version__, prog_name="astack")
def cli():
    """Agentic Stacks CLI — manage composed domain expertise."""
    pass


cli.add_command(init)


def main():
    cli()
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_init.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/astack/commands/init.py src/astack/__init__.py tests/test_cli_init.py
git commit -m "feat: astack init command — scaffold new stack projects"
```

---

### Task 3: `astack doctor` Command

**Files:**
- Create: `src/astack/commands/doctor.py`
- Modify: `src/astack/__init__.py` (register command)
- Create: `tests/test_cli_doctor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_doctor.py
import json
import yaml
from click.testing import CliRunner
from astack import cli


def _create_valid_stack(path):
    """Helper to create a minimal valid stack for testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test",
        "namespace": "testorg",
        "version": "1.0.0",
        "description": "Test stack",
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"},
        ],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [],
        "deprecations": [],
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    schema = {"type": "object", "required": ["name"]}
    (path / "environments" / "_schema.json").write_text(json.dumps(schema))


def test_doctor_valid_stack(tmp_path):
    stack_dir = tmp_path / "stack"
    _create_valid_stack(stack_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert result.exit_code == 0
    assert "ok" in result.output.lower() or "pass" in result.output.lower() or "✓" in result.output or "healthy" in result.output.lower()


def test_doctor_missing_manifest(tmp_path):
    stack_dir = tmp_path / "stack"
    stack_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert result.exit_code != 0
    assert "stack.yaml" in result.output.lower() or "manifest" in result.output.lower()


def test_doctor_invalid_manifest(tmp_path):
    stack_dir = tmp_path / "stack"
    stack_dir.mkdir()
    (stack_dir / "stack.yaml").write_text("just: a string value\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert result.exit_code != 0


def test_doctor_missing_skills_dir(tmp_path):
    stack_dir = tmp_path / "stack"
    _create_valid_stack(stack_dir)
    import shutil
    shutil.rmtree(stack_dir / "skills")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert "skills" in result.output.lower() or "warn" in result.output.lower() or "missing" in result.output.lower()


def test_doctor_deprecated_skills_warning(tmp_path):
    stack_dir = tmp_path / "stack"
    _create_valid_stack(stack_dir)
    manifest = yaml.safe_load((stack_dir / "stack.yaml").read_text())
    manifest["deprecations"] = [
        {"skill": "old-deploy", "since": "0.9.0", "removal": "2.0.0", "replacement": "deploy", "reason": "Replaced"}
    ]
    (stack_dir / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert "deprecat" in result.output.lower()


def test_doctor_defaults_to_cwd(tmp_path, monkeypatch):
    _create_valid_stack(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_doctor.py -v`

- [ ] **Step 3: Implement doctor command**

```python
# src/astack/commands/doctor.py
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
    issues = []
    warnings = []

    # 1. Check manifest
    manifest_path = stack_dir / "stack.yaml"
    try:
        manifest = load_manifest(manifest_path)
        click.echo(f"  manifest: {manifest['full_name']}@{manifest['version']}")
    except ManifestError as e:
        raise click.ClickException(f"Invalid manifest: {e}")

    # 2. Check directory structure
    for dirname in ["skills", "profiles", "environments"]:
        d = stack_dir / dirname
        if not d.is_dir():
            warnings.append(f"Missing directory: {dirname}/")
        else:
            click.echo(f"  {dirname}/: found")

    # 3. Check profile categories
    profiles_path = manifest.get("profiles", {}).get("path", "profiles/")
    profiles_dir = stack_dir / profiles_path
    if profiles_dir.is_dir():
        categories = manifest.get("profiles", {}).get("categories", [])
        for cat in categories:
            if not (profiles_dir / cat).is_dir():
                warnings.append(f"Profile category directory missing: {profiles_path}{cat}/")

    # 4. Check environment schema
    schema_path_str = manifest.get("environment_schema", "")
    if schema_path_str:
        schema_file = stack_dir / schema_path_str
        if schema_file.exists():
            try:
                json.loads(schema_file.read_text())
                click.echo(f"  schema: valid")
            except json.JSONDecodeError as e:
                issues.append(f"Invalid environment schema JSON: {e}")
        else:
            warnings.append(f"Environment schema not found: {schema_path_str}")

    # 5. Check skill entries
    for skill in manifest.get("skills", []):
        entry = stack_dir / skill["entry"]
        if not entry.exists():
            warnings.append(f"Skill entry not found: {skill['name']} -> {skill['entry']}")

    # 6. Report deprecations
    deprecations = manifest.get("deprecations", [])
    if deprecations:
        click.echo(f"\n  Deprecations ({len(deprecations)}):")
        for dep in deprecations:
            click.echo(f"    - {dep['skill']}: deprecated since {dep['since']}, "
                       f"removal in {dep['removal']}, use '{dep['replacement']}' instead")

    # Report
    if issues:
        click.echo(f"\n  Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"    ERROR: {issue}")
        raise click.ClickException(f"Stack has {len(issues)} issue(s)")

    if warnings:
        click.echo(f"\n  Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"    WARN: {warning}")

    click.echo(f"\n  Stack is healthy.")
```

- [ ] **Step 4: Register command in CLI**

Add to `src/astack/__init__.py`:

```python
from astack.commands.doctor import doctor
# ... after cli.add_command(init)
cli.add_command(doctor)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_doctor.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/astack/commands/doctor.py src/astack/__init__.py tests/test_cli_doctor.py
git commit -m "feat: astack doctor command — validate stack projects"
```

---

### Task 4: `astack validate` Command

**Files:**
- Create: `src/astack/commands/validate.py`
- Modify: `src/astack/__init__.py` (register command)
- Create: `tests/test_cli_validate.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_validate.py
import json
import yaml
from click.testing import CliRunner
from astack import cli


def _setup_stack_with_env(path, env_name="dev", env_data=None):
    """Create a stack with an environment for testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test",
        "namespace": "testorg",
        "version": "1.0.0",
        "description": "Test",
        "environment_schema": "environments/_schema.json",
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    envs = path / "environments"
    envs.mkdir()
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["name", "profiles"],
        "properties": {
            "name": {"type": "string"},
            "profiles": {"type": "object"},
        },
    }
    (envs / "_schema.json").write_text(json.dumps(schema, indent=2))
    env_dir = envs / env_name
    env_dir.mkdir()
    if env_data is None:
        env_data = {"name": env_name, "profiles": {"security": "baseline"}}
    (env_dir / "environment.yml").write_text(yaml.dump(env_data, sort_keys=False))


def test_validate_valid_environment(tmp_path):
    stack_dir = tmp_path / "stack"
    _setup_stack_with_env(stack_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "dev", "--path", str(stack_dir)])
    assert result.exit_code == 0
    assert "valid" in result.output.lower() or "ok" in result.output.lower() or "pass" in result.output.lower()


def test_validate_invalid_environment(tmp_path):
    stack_dir = tmp_path / "stack"
    _setup_stack_with_env(stack_dir, env_data={"name": "dev"})  # missing profiles
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "dev", "--path", str(stack_dir)])
    assert result.exit_code != 0
    assert "profiles" in result.output.lower()


def test_validate_missing_environment(tmp_path):
    stack_dir = tmp_path / "stack"
    _setup_stack_with_env(stack_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "nonexistent", "--path", str(stack_dir)])
    assert result.exit_code != 0


def test_validate_list_environments(tmp_path):
    stack_dir = tmp_path / "stack"
    _setup_stack_with_env(stack_dir, env_name="dev")
    _setup_stack_with_env(stack_dir, env_name="staging")  # will just add the env dir
    # Manually add staging since _setup_stack_with_env re-creates the whole thing
    staging_dir = stack_dir / "environments" / "staging"
    staging_dir.mkdir(exist_ok=True)
    staging_data = {"name": "staging", "profiles": {"security": "hardened"}}
    (staging_dir / "environment.yml").write_text(yaml.dump(staging_data, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--list", "--path", str(stack_dir)])
    assert result.exit_code == 0
    assert "dev" in result.output
    assert "staging" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_validate.py -v`

- [ ] **Step 3: Implement validate command**

```python
# src/astack/commands/validate.py
"""astack validate — validate an environment against its schema."""

import json
import pathlib

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    validate_environment,
    EnvironmentError,
)


@click.command()
@click.argument("environment", required=False)
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--list", "list_envs", is_flag=True, help="List available environments")
def validate(environment: str | None, path: str, list_envs: bool):
    """Validate an environment against the stack schema."""
    stack_dir = pathlib.Path(path)

    # Load manifest to find schema path
    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Cannot load manifest: {e}")

    envs_dir = stack_dir / "environments"

    # List mode
    if list_envs:
        envs = list_environments(envs_dir)
        if not envs:
            click.echo("No environments found.")
        else:
            click.echo("Environments:")
            for env_name in envs:
                click.echo(f"  - {env_name}")
        return

    # Validate mode
    if not environment:
        raise click.ClickException("Specify an environment name, or use --list to see available environments.")

    # Load environment
    try:
        env_data = load_environment(envs_dir / environment)
    except EnvironmentError as e:
        raise click.ClickException(str(e))

    # Load schema
    schema_path_str = manifest.get("environment_schema", "")
    if not schema_path_str:
        raise click.ClickException("No environment_schema defined in stack.yaml")

    schema_file = stack_dir / schema_path_str
    if not schema_file.exists():
        raise click.ClickException(f"Schema file not found: {schema_path_str}")

    try:
        schema = json.loads(schema_file.read_text())
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid schema JSON: {e}")

    # Validate
    try:
        validate_environment(env_data, schema)
    except EnvironmentError as e:
        raise click.ClickException(f"Environment '{environment}' is invalid:\n{e}")

    click.echo(f"Environment '{environment}' is valid.")
```

- [ ] **Step 4: Register command in CLI**

Add to `src/astack/__init__.py`:

```python
from astack.commands.validate import validate
# ... after other add_command calls
cli.add_command(validate)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_validate.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/astack/commands/validate.py src/astack/__init__.py tests/test_cli_validate.py
git commit -m "feat: astack validate command — validate environments against schema"
```

---

### Task 5: CLI Integration Test and Final Verification

**Files:**
- Create: `tests/test_cli_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_cli_integration.py
"""End-to-end: init a stack, doctor it, add an environment, validate it."""
import yaml
from click.testing import CliRunner
from astack import cli


def test_full_cli_workflow(tmp_path):
    runner = CliRunner()

    # 1. Init a new stack
    stack_dir = tmp_path / "my-stack"
    result = runner.invoke(cli, ["init", str(stack_dir), "--name", "my-stack", "--namespace", "myorg"])
    assert result.exit_code == 0

    # 2. Doctor the fresh stack (should pass)
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert result.exit_code == 0

    # 3. Create an environment manually
    env_dir = stack_dir / "environments" / "dev"
    env_dir.mkdir()
    env_data = {"name": "dev", "profiles": {"security": "baseline"}}
    (env_dir / "environment.yml").write_text(yaml.dump(env_data, sort_keys=False))

    # 4. Validate the environment
    result = runner.invoke(cli, ["validate", "dev", "--path", str(stack_dir)])
    assert result.exit_code == 0

    # 5. List environments
    result = runner.invoke(cli, ["validate", "--list", "--path", str(stack_dir)])
    assert result.exit_code == 0
    assert "dev" in result.output

    # 6. Validate an invalid environment
    bad_dir = stack_dir / "environments" / "bad"
    bad_dir.mkdir()
    (bad_dir / "environment.yml").write_text(yaml.dump({"name": "bad"}, sort_keys=False))
    result = runner.invoke(cli, ["validate", "bad", "--path", str(stack_dir)])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass (46 runtime + ~17 CLI = ~63 total)

- [ ] **Step 3: Verify CLI works from command line**

Run: `astack --version && astack --help && astack init /tmp/test-stack --name test --namespace test && astack doctor --path /tmp/test-stack && rm -rf /tmp/test-stack`
Expected: All commands work

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_integration.py
git commit -m "feat: CLI integration test — full init/doctor/validate workflow"
```
