# Extends & Overrides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators create their own stack (`blahfoo/my-openstack`) that extends a published stack (`agentic-stacks/openstack-kolla`), inheriting skills and profiles while owning their environments, overrides, and state.

**Architecture:** Three new capabilities: (1) an overrides merge layer in the profile engine — profiles → environment → overrides, with enforced keys still protected, (2) `extends` field in `stack.yaml` that declares a parent stack, and (3) `init --extends` CLI command that scaffolds an operator project pointing at a base stack. The pulled parent stack lives in `.stacks/`; the operator's project owns environments, overrides, and state.

**Tech Stack:** Python, PyYAML, Click, pytest, existing `_deep_merge` and `merge_profiles` from `profiles.py`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/agentic_stacks/profiles.py` | Modify | Add `load_overrides()` and `build_config()` — the full merge pipeline |
| `src/agentic_stacks/manifest.py` | Modify | Parse `extends` field, add `resolve_extends()` to locate parent manifest |
| `src/agentic_stacks/environments.py` | Modify | Add `load_environment_overrides()` for the overrides/ subdirectory |
| `src/agentic_stacks/__init__.py` | Modify | Export new public API |
| `src/agentic_stacks_cli/commands/init.py` | Modify | Add `--extends` option, scaffold operator project |
| `src/agentic_stacks_cli/commands/doctor.py` | Modify | Validate extends reference, check parent stack exists in .stacks/ |
| `tests/fixtures/sample-stack/environments/dev/overrides/globals.yml` | Create | Test fixture for overrides |
| `tests/fixtures/parent-stack/` | Create | Test fixture — a minimal "parent" stack |
| `tests/fixtures/child-stack/` | Create | Test fixture — a stack that extends parent-stack |
| `tests/test_overrides.py` | Create | Tests for overrides merge pipeline |
| `tests/test_extends.py` | Create | Tests for extends manifest parsing and resolution |
| `tests/test_cli_init_extends.py` | Create | Tests for `init --extends` scaffolding |

---

### Task 1: Overrides Merge Layer

Add the ability to load YAML override files from a directory and merge them on top of a composed config.

**Files:**
- Modify: `src/agentic_stacks/profiles.py`
- Create: `tests/test_overrides.py`
- Create: `tests/fixtures/sample-stack/environments/dev/overrides/globals.yml`
- Create: `tests/fixtures/sample-stack/environments/dev/overrides/nova.yml`

- [ ] **Step 1: Create override fixture files**

Create `tests/fixtures/sample-stack/environments/dev/overrides/globals.yml`:

```yaml
debug: true
logging:
  level: DEBUG
  file: /var/log/stack.log
```

Create `tests/fixtures/sample-stack/environments/dev/overrides/nova.yml`:

```yaml
compute:
  cpu_allocation_ratio: 4.0
  ram_allocation_ratio: 1.5
```

- [ ] **Step 2: Write failing tests for load_overrides**

Create `tests/test_overrides.py`:

```python
import pathlib
import pytest
import yaml

from agentic_stacks.profiles import load_overrides, merge_profiles, _deep_merge


@pytest.fixture
def overrides_dir(sample_environments_path):
    return sample_environments_path / "dev" / "overrides"


def test_load_overrides(overrides_dir):
    overrides = load_overrides(overrides_dir)
    assert isinstance(overrides, dict)
    assert overrides["debug"] is True
    assert overrides["compute"]["cpu_allocation_ratio"] == 4.0


def test_load_overrides_empty_dir(tmp_path):
    empty = tmp_path / "overrides"
    empty.mkdir()
    overrides = load_overrides(empty)
    assert overrides == {}


def test_load_overrides_missing_dir(tmp_path):
    overrides = load_overrides(tmp_path / "nonexistent")
    assert overrides == {}


def test_load_overrides_merges_multiple_files(overrides_dir):
    overrides = load_overrides(overrides_dir)
    # globals.yml keys
    assert overrides["debug"] is True
    assert overrides["logging"]["level"] == "DEBUG"
    # nova.yml keys
    assert overrides["compute"]["cpu_allocation_ratio"] == 4.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_overrides.py -v`
Expected: ImportError — `load_overrides` doesn't exist yet

- [ ] **Step 4: Implement load_overrides**

Add to `src/agentic_stacks/profiles.py`, after the `load_profile` function (after line 24):

```python
def load_overrides(overrides_dir: pathlib.Path) -> dict:
    """Load all YAML files from an overrides directory and merge them.

    Files are merged in sorted filename order. Returns empty dict if
    the directory doesn't exist or is empty.
    """
    overrides_dir = pathlib.Path(overrides_dir)
    if not overrides_dir.is_dir():
        return {}
    result = {}
    for path in sorted(overrides_dir.glob("*.yml")):
        data = load_profile(path)
        result = _deep_merge(result, data)
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_overrides.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks/profiles.py tests/test_overrides.py \
  tests/fixtures/sample-stack/environments/dev/overrides/globals.yml \
  tests/fixtures/sample-stack/environments/dev/overrides/nova.yml
git commit -m "feat: add load_overrides — merge YAML override files from a directory"
```

---

### Task 2: Full Config Build Pipeline

Add `build_config()` that runs the complete merge pipeline: profiles → environment → overrides, with enforced key protection throughout.

**Files:**
- Modify: `src/agentic_stacks/profiles.py`
- Modify: `tests/test_overrides.py`

- [ ] **Step 1: Write failing tests for build_config**

Append to `tests/test_overrides.py`:

```python
from agentic_stacks.profiles import build_config, EnforcedKeyError


def test_build_config_profiles_only():
    profiles = [
        {"security": {"level": "baseline", "tls": True}},
        {"networking": {"driver": "ovn"}},
    ]
    result = build_config(profiles=profiles)
    assert result["security"]["level"] == "baseline"
    assert result["networking"]["driver"] == "ovn"


def test_build_config_with_environment():
    profiles = [{"networking": {"driver": "ovn", "mtu": 1500}}]
    environment = {"networking": {"mtu": 9000}, "inventory": {"hosts": ["h1"]}}
    result = build_config(profiles=profiles, environment=environment)
    assert result["networking"]["driver"] == "ovn"
    assert result["networking"]["mtu"] == 9000
    assert result["inventory"]["hosts"] == ["h1"]


def test_build_config_with_overrides():
    profiles = [{"networking": {"driver": "ovn", "mtu": 1500}}]
    environment = {"networking": {"mtu": 9000}}
    overrides = {"networking": {"mtu": 9200}, "debug": True}
    result = build_config(profiles=profiles, environment=environment, overrides=overrides)
    assert result["networking"]["mtu"] == 9200
    assert result["debug"] is True


def test_build_config_enforced_keys_block_environment():
    profiles = [{"security": {"tls": True, "__enforced": True}}]
    environment = {"security": {"tls": False}}
    with pytest.raises(EnforcedKeyError, match="tls"):
        build_config(profiles=profiles, environment=environment,
                     enforced_marker="__enforced")


def test_build_config_enforced_keys_block_overrides():
    profiles = [{"security": {"tls": True, "__enforced": True}}]
    overrides = {"security": {"tls": False}}
    with pytest.raises(EnforcedKeyError, match="tls"):
        build_config(profiles=profiles, overrides=overrides,
                     enforced_marker="__enforced")


def test_build_config_enforced_keys_allow_same_value():
    profiles = [{"security": {"tls": True, "__enforced": True}}]
    environment = {"security": {"tls": True}}
    overrides = {"security": {"tls": True}}
    result = build_config(profiles=profiles, environment=environment,
                          overrides=overrides, enforced_marker="__enforced")
    assert result["security"]["tls"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_overrides.py::test_build_config_profiles_only -v`
Expected: ImportError — `build_config` doesn't exist yet

- [ ] **Step 3: Implement build_config**

Add to `src/agentic_stacks/profiles.py`, after the `merge_profiles` function (after line 132):

```python
def build_config(
    profiles: list[dict],
    environment: dict | None = None,
    overrides: dict | None = None,
    enforced_marker: str | None = None,
) -> dict:
    """Build final config: profiles → environment → overrides.

    Merges profiles first (with optional enforced key protection),
    then layers the environment values, then layers overrides.
    Enforced keys are protected across all three layers.
    """
    # Step 1: merge profiles
    merged = merge_profiles(profiles, enforced_marker=enforced_marker)

    # Collect enforced keys from the merged result
    enforced_keys: dict[str, Any] = {}
    if enforced_marker:
        enforced_keys = _collect_enforced_keys(merged, enforced_marker)
        _remove_marker(merged, enforced_marker)

    # Step 2: layer environment
    if environment:
        if enforced_keys:
            _check_enforced(environment, enforced_keys)
        merged = _deep_merge(merged, environment)

    # Step 3: layer overrides
    if overrides:
        if enforced_keys:
            _check_enforced(overrides, enforced_keys)
        merged = _deep_merge(merged, overrides)

    return merged


def _check_enforced(data: dict, enforced_keys: dict[str, Any]) -> None:
    """Raise EnforcedKeyError if data tries to change an enforced value."""
    for enforced_path, enforced_value in enforced_keys.items():
        new_value = _get_nested(data, enforced_path)
        if new_value is not _SENTINEL and new_value != enforced_value:
            raise EnforcedKeyError(
                f"Cannot override enforced key '{enforced_path}': "
                f"tried to change {enforced_value!r} to {new_value!r}"
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_overrides.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/profiles.py tests/test_overrides.py
git commit -m "feat: add build_config — full merge pipeline with enforced key protection"
```

---

### Task 3: Environment Overrides Loader

Add `load_environment_overrides()` to environments.py — loads the overrides/ subdirectory within an environment.

**Files:**
- Modify: `src/agentic_stacks/environments.py`
- Modify: `tests/test_environments.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_environments.py`:

```python
from agentic_stacks.environments import load_environment_overrides


def test_load_environment_overrides(sample_environments_path):
    overrides = load_environment_overrides(sample_environments_path / "dev")
    assert isinstance(overrides, dict)
    assert overrides["debug"] is True
    assert overrides["compute"]["cpu_allocation_ratio"] == 4.0


def test_load_environment_overrides_no_dir(tmp_path):
    env_dir = tmp_path / "staging"
    env_dir.mkdir()
    (env_dir / "environment.yml").write_text("name: staging\n")
    overrides = load_environment_overrides(env_dir)
    assert overrides == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_environments.py::test_load_environment_overrides -v`
Expected: ImportError — `load_environment_overrides` doesn't exist yet

- [ ] **Step 3: Implement load_environment_overrides**

Add to `src/agentic_stacks/environments.py`, after `validate_environment` (after line 50):

```python
def load_environment_overrides(env_dir: pathlib.Path) -> dict:
    """Load overrides from the overrides/ subdirectory of an environment.

    Returns empty dict if no overrides directory exists.
    """
    from agentic_stacks.profiles import load_overrides
    return load_overrides(pathlib.Path(env_dir) / "overrides")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_environments.py -v`
Expected: All tests PASS (existing + 2 new)

- [ ] **Step 5: Export from __init__.py**

In `src/agentic_stacks/__init__.py`, add the new imports:

Add to the imports from `profiles`:
```python
from agentic_stacks.profiles import (
    load_profile,
    load_profiles_by_category,
    merge_profiles,
    load_overrides,
    build_config,
    EnforcedKeyError,
)
```

Add to the imports from `environments`:
```python
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    create_environment,
    validate_environment,
    load_environment_overrides,
    EnvironmentError,
)
```

Add `"load_overrides"`, `"build_config"`, and `"load_environment_overrides"` to `__all__`.

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks/environments.py src/agentic_stacks/__init__.py \
  tests/test_environments.py
git commit -m "feat: add load_environment_overrides — bridge between environments and overrides"
```

---

### Task 4: Parse `extends` in Manifest

Add support for the `extends` field in `stack.yaml` and a resolver that locates the parent stack's manifest.

**Files:**
- Modify: `src/agentic_stacks/manifest.py`
- Create: `tests/fixtures/parent-stack/stack.yaml`
- Create: `tests/fixtures/parent-stack/profiles/security/baseline.yml`
- Create: `tests/fixtures/parent-stack/skills/deploy/README.md`
- Create: `tests/fixtures/child-stack/stack.yaml`
- Create: `tests/fixtures/child-stack/environments/prod/environment.yml`
- Create: `tests/test_extends.py`

- [ ] **Step 1: Create parent-stack fixture**

Create `tests/fixtures/parent-stack/stack.yaml`:

```yaml
name: openstack-kolla
namespace: agentic-stacks
version: "1.3.0"
description: "Agent-driven OpenStack deployment"

target:
  software: openstack
  versions: ["2024.2", "2025.1"]

skills:
  - name: deploy
    entry: skills/deploy/
    description: "Deploy OpenStack"
  - name: health-check
    entry: skills/health-check/
    description: "Check health"

profiles:
  categories: [security, networking, storage, scale]
  path: profiles/
  merge_order: "security first (enforced), then declared order"

environment_schema: environments/_schema.json
depends_on: []
requires:
  tools: [kolla-ansible]
  python: ">=3.11"
deprecations: []
```

Create `tests/fixtures/parent-stack/profiles/security/baseline.yml`:

```yaml
security:
  level: baseline
  tls_required: true
```

Create `tests/fixtures/parent-stack/skills/deploy/README.md`:

```markdown
# Deploy Skill
Placeholder for testing.
```

- [ ] **Step 2: Create child-stack fixture**

Create `tests/fixtures/child-stack/stack.yaml`:

```yaml
name: my-openstack
namespace: blahfoo
version: "1.0.0"
description: "Our production OpenStack"

extends:
  name: openstack-kolla
  namespace: agentic-stacks
  version: "^1.3"

environment_schema: environments/_schema.json
depends_on: []
deprecations: []
```

Create `tests/fixtures/child-stack/environments/prod/environment.yml`:

```yaml
name: prod
description: Production OpenStack
profiles:
  security: baseline
  networking: ovn
  storage: ceph
  scale: ha
inventory:
  controllers: [ctrl-01, ctrl-02, ctrl-03]
```

- [ ] **Step 3: Write failing tests**

Create `tests/test_extends.py`:

```python
import pathlib
import pytest
import yaml

from agentic_stacks.manifest import load_manifest, resolve_extends, ManifestError

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_load_manifest_with_extends():
    manifest = load_manifest(FIXTURES / "child-stack" / "stack.yaml")
    assert manifest["name"] == "my-openstack"
    assert manifest["namespace"] == "blahfoo"
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "^1.3"


def test_load_manifest_without_extends():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert "extends" not in manifest or manifest.get("extends") is None


def test_resolve_extends_finds_parent():
    child = load_manifest(FIXTURES / "child-stack" / "stack.yaml")
    stacks_dir = FIXTURES  # parent-stack lives here as "parent-stack"

    # Simulate .stacks/ layout: .stacks/agentic-stacks/openstack-kolla/1.3.0/
    parent_path = FIXTURES / "parent-stack" / "stack.yaml"
    parent = resolve_extends(child, search_dirs=[FIXTURES / "parent-stack"])
    assert parent["name"] == "openstack-kolla"
    assert parent["namespace"] == "agentic-stacks"


def test_resolve_extends_not_found():
    child = load_manifest(FIXTURES / "child-stack" / "stack.yaml")
    with pytest.raises(ManifestError, match="not found"):
        resolve_extends(child, search_dirs=[])


def test_resolve_extends_returns_none_if_no_extends():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    result = resolve_extends(manifest, search_dirs=[])
    assert result is None


def test_child_inherits_parent_skills():
    child = load_manifest(FIXTURES / "child-stack" / "stack.yaml")
    parent = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    # Child has no skills of its own — inherits from parent
    assert child.get("skills", []) == []
    assert len(parent["skills"]) == 2


def test_child_has_own_environments():
    child_dir = FIXTURES / "child-stack"
    from agentic_stacks.environments import load_environment
    env = load_environment(child_dir / "environments" / "prod")
    assert env["name"] == "prod"
    assert env["inventory"]["controllers"] == ["ctrl-01", "ctrl-02", "ctrl-03"]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_extends.py -v`
Expected: ImportError — `resolve_extends` doesn't exist yet

- [ ] **Step 5: Implement extends support in manifest.py**

Modify `src/agentic_stacks/manifest.py`. Add `resolve_extends` after `load_manifest`:

```python
def resolve_extends(manifest: dict, search_dirs: list[pathlib.Path]) -> dict | None:
    """Locate and load the parent stack manifest declared in 'extends'.

    Args:
        manifest: A loaded manifest dict (from load_manifest).
        search_dirs: Directories to search for the parent stack.
            Typically [project_dir / ".stacks" / namespace / name / version].
            Each dir should contain a stack.yaml at its root.

    Returns:
        The parent manifest dict, or None if no extends field.

    Raises:
        ManifestError: If extends is declared but parent can't be found.
    """
    extends = manifest.get("extends")
    if not extends:
        return None

    parent_name = extends["name"]
    parent_namespace = extends.get("namespace", "")

    for search_dir in search_dirs:
        candidate = pathlib.Path(search_dir) / "stack.yaml"
        if candidate.exists():
            parent = load_manifest(candidate)
            if parent["name"] == parent_name:
                if not parent_namespace or parent["namespace"] == parent_namespace:
                    return parent

    raise ManifestError(
        f"Parent stack '{parent_namespace}/{parent_name}' not found. "
        f"Run 'agentic-stacks pull {parent_namespace}/{parent_name}' first."
    )
```

Also update the defaults in `load_manifest` — add `extends` to the optional fields. After line 51 (the `manifest.setdefault("target", ...)` block), add:

```python
    # extends is optional — not set by default, just preserved if present
```

No change needed — `load_manifest` already preserves unknown keys. The `extends` field will pass through as-is.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_extends.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/agentic_stacks/manifest.py tests/test_extends.py \
  tests/fixtures/parent-stack/ tests/fixtures/child-stack/
git commit -m "feat: add extends field parsing and resolve_extends to locate parent stacks"
```

---

### Task 5: `init --extends` CLI Command

Add `--extends` option to the init command that scaffolds an operator project pointing at a base stack.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/init.py`
- Create: `tests/test_cli_init_extends.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_init_extends.py`:

```python
import pathlib
import pytest
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli


def test_init_extends_creates_structure(tmp_path):
    target = tmp_path / "my-openstack"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-openstack",
        "--namespace", "blahfoo",
        "--extends", "agentic-stacks/openstack-kolla@1.3.0",
    ])
    assert result.exit_code == 0, result.output

    assert (target / "stack.yaml").exists()
    assert (target / "environments").is_dir()
    assert (target / "state").is_dir()
    assert (target / "CLAUDE.md").exists()

    # Should NOT create skills/ or profiles/ — inherited from parent
    assert not (target / "skills").exists()
    assert not (target / "profiles").exists()


def test_init_extends_stack_yaml_content(tmp_path):
    target = tmp_path / "my-openstack"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-openstack",
        "--namespace", "blahfoo",
        "--extends", "agentic-stacks/openstack-kolla@1.3.0",
    ])

    with open(target / "stack.yaml") as f:
        manifest = yaml.safe_load(f)

    assert manifest["name"] == "my-openstack"
    assert manifest["namespace"] == "blahfoo"
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "1.3.0"


def test_init_extends_creates_example_environment(tmp_path):
    target = tmp_path / "my-openstack"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-openstack",
        "--namespace", "blahfoo",
        "--extends", "agentic-stacks/openstack-kolla@1.3.0",
    ])

    env_file = target / "environments" / "example" / "environment.yml"
    assert env_file.exists()
    with open(env_file) as f:
        env = yaml.safe_load(f)
    assert env["name"] == "example"
    assert "profiles" in env

    overrides_dir = target / "environments" / "example" / "overrides"
    assert overrides_dir.is_dir()


def test_init_extends_creates_stacks_lock(tmp_path):
    target = tmp_path / "my-openstack"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-openstack",
        "--namespace", "blahfoo",
        "--extends", "agentic-stacks/openstack-kolla@1.3.0",
    ])

    lock_file = target / "stacks.lock"
    assert lock_file.exists()
    with open(lock_file) as f:
        lock = yaml.safe_load(f)
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["version"] == "1.3.0"


def test_init_extends_creates_gitignore(tmp_path):
    target = tmp_path / "my-openstack"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-openstack",
        "--namespace", "blahfoo",
        "--extends", "agentic-stacks/openstack-kolla@1.3.0",
    ])

    gitignore = target / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text()
    assert ".stacks/" in content


def test_init_without_extends_unchanged(tmp_path):
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

    with open(target / "stack.yaml") as f:
        manifest = yaml.safe_load(f)
    assert "extends" not in manifest


def test_init_extends_bad_format(tmp_path):
    target = tmp_path / "bad"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "x",
        "--namespace", "y",
        "--extends", "no-version-here",
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_init_extends.py -v`
Expected: Tests fail — `--extends` option doesn't exist yet

- [ ] **Step 3: Implement --extends in init.py**

Replace `src/agentic_stacks_cli/commands/init.py` with:

```python
"""astack init — scaffold a new stack project."""

import json
import pathlib
import re

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


def _parse_extends(ref: str) -> tuple[str, str, str]:
    """Parse 'namespace/name@version' into (namespace, name, version)."""
    match = re.match(r"^([^/]+)/([^@]+)@(.+)$", ref)
    if not match:
        raise click.ClickException(
            f"Invalid extends reference: '{ref}'. "
            "Expected format: namespace/name@version"
        )
    return match.group(1), match.group(2), match.group(3)


@click.command()
@click.argument("path", type=click.Path())
@click.option("--name", required=True, help="Stack name")
@click.option("--namespace", required=True, help="Stack namespace (e.g., org name)")
@click.option("--extends", "extends_ref", default=None,
              help="Base stack to extend (namespace/name@version)")
def init(path: str, name: str, namespace: str, extends_ref: str | None):
    """Scaffold a new stack project."""
    stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)

    if extends_ref:
        _init_operator_project(stack_dir, name, namespace, extends_ref)
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
                           extends_ref: str):
    """Scaffold an operator project that extends a base stack."""
    ext_namespace, ext_name, ext_version = _parse_extends(extends_ref)

    # Create operator directory structure
    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()

    (stack_dir / "state").mkdir()

    # Example environment with overrides directory
    example_env = envs_dir / "example"
    example_env.mkdir()
    (example_env / "overrides").mkdir()

    example_data = {
        "name": "example",
        "description": f"Example environment for {name}",
        "profiles": {},
        "approval": {"tier": "human-approve"},
    }
    with open(example_env / "environment.yml", "w") as f:
        yaml.dump(example_data, f, default_flow_style=False, sort_keys=False)

    # Manifest with extends
    manifest = {
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"{name} — extends {ext_namespace}/{ext_name}",
        "extends": {
            "name": ext_name,
            "namespace": ext_namespace,
            "version": ext_version,
        },
        "environment_schema": "environments/_schema.json",
        "depends_on": [],
        "deprecations": [],
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    # stacks.lock pinning the base stack
    lock = {
        "stacks": [{
            "name": f"{ext_namespace}/{ext_name}",
            "version": ext_version,
            "digest": "",
            "registry": f"ghcr.io/{ext_namespace}/{ext_name}:{ext_version}",
        }]
    }
    with open(stack_dir / "stacks.lock", "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)

    # .gitignore
    (stack_dir / ".gitignore").write_text(".stacks/\n*.db\n__pycache__/\n")

    # CLAUDE.md
    claude_md = (
        f"# {name}\n\n"
        f"Operator project extending `{ext_namespace}/{ext_name}@{ext_version}`.\n\n"
        f"## Setup\n\n"
        f"```bash\n"
        f"agentic-stacks pull  # downloads base stack to .stacks/\n"
        f"```\n\n"
        f"## Environments\n\n"
        f"Each environment in `environments/` has:\n"
        f"- `environment.yml` — profile selections, inventory, config\n"
        f"- `overrides/` — raw YAML overrides merged on top\n\n"
        f"## Deploy\n\n"
        f"The agent reads skills from `.stacks/`, composes config from profiles + "
        f"environment + overrides, and executes.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized operator project '{namespace}/{name}' at {stack_dir}")
    click.echo(f"  Extends: {ext_namespace}/{ext_name}@{ext_version}")
    click.echo(f"  Run 'agentic-stacks pull' to download the base stack.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_init_extends.py tests/test_cli_init.py -v`
Expected: All tests PASS (new extends tests + existing init tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/init.py tests/test_cli_init_extends.py
git commit -m "feat: add init --extends — scaffold operator project extending a base stack"
```

---

### Task 6: Doctor Validates extends

Update `doctor` to check the `extends` field and verify the parent stack is available.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/doctor.py`
- Modify: `tests/test_cli_doctor.py`

- [ ] **Step 1: Read current doctor tests**

Read `tests/test_cli_doctor.py` to understand existing patterns.

- [ ] **Step 2: Write failing tests**

Append to `tests/test_cli_doctor.py`:

```python
def test_doctor_extends_warns_missing_parent(tmp_path):
    """Doctor warns when extends parent is not in .stacks/."""
    stack_dir = tmp_path / "my-project"
    stack_dir.mkdir()
    manifest = {
        "name": "my-openstack", "namespace": "blahfoo", "version": "0.1.0",
        "description": "test",
        "extends": {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.3.0"},
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f)
    (stack_dir / "environments").mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert "parent stack" in result.output.lower() or "extends" in result.output.lower()


def test_doctor_extends_ok_with_parent(tmp_path):
    """Doctor passes when extends parent exists in .stacks/."""
    stack_dir = tmp_path / "my-project"
    stack_dir.mkdir()
    manifest = {
        "name": "my-openstack", "namespace": "blahfoo", "version": "0.1.0",
        "description": "test",
        "extends": {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.3.0"},
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f)
    (stack_dir / "environments").mkdir()

    # Simulate pulled parent
    parent_dir = stack_dir / ".stacks" / "agentic-stacks" / "openstack-kolla" / "1.3.0"
    parent_dir.mkdir(parents=True)
    parent_manifest = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.3.0",
        "description": "Parent stack",
    }
    with open(parent_dir / "stack.yaml", "w") as f:
        yaml.dump(parent_manifest, f)

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(stack_dir)])
    assert result.exit_code == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_doctor.py::test_doctor_extends_warns_missing_parent -v`
Expected: Assertion fails — doctor doesn't check extends yet

- [ ] **Step 4: Read and modify doctor.py**

Read `src/agentic_stacks_cli/commands/doctor.py` first to see the current structure, then add extends validation. After the manifest is loaded and basic checks run, add:

```python
    # Check extends
    extends = manifest.get("extends")
    if extends:
        ext_name = extends.get("name", "")
        ext_namespace = extends.get("namespace", "")
        ext_version = extends.get("version", "")
        click.echo(f"  Extends: {ext_namespace}/{ext_name}@{ext_version}")

        # Look for parent in .stacks/
        parent_candidates = list(
            (stack_dir / ".stacks" / ext_namespace / ext_name).glob("*/stack.yaml")
        )
        if parent_candidates:
            click.echo(f"  ✓ Parent stack found")
        else:
            click.echo(f"  ⚠ Parent stack not found in .stacks/ — run 'agentic-stacks pull'")
            warnings += 1
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_doctor.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/doctor.py tests/test_cli_doctor.py
git commit -m "feat: doctor validates extends — warns if parent stack not pulled"
```

---

### Task 7: Run Full Test Suite and Final Integration

Run the complete test suite, verify everything works together, update CLAUDE.md.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Test the CLI manually**

```bash
# Scaffold an operator project
.venv/bin/agentic-stacks init /tmp/test-project \
  --name my-openstack --namespace blahfoo \
  --extends agentic-stacks/openstack-kolla@1.3.0

# Inspect the result
cat /tmp/test-project/stack.yaml
cat /tmp/test-project/stacks.lock
cat /tmp/test-project/environments/example/environment.yml
ls /tmp/test-project/

# Doctor it
.venv/bin/agentic-stacks doctor --path /tmp/test-project

# Clean up
rm -rf /tmp/test-project
```

- [ ] **Step 3: Update CLAUDE.md**

Add to the Architecture section of `CLAUDE.md` after the existing content:

```markdown
## Extends & Overrides

**Extends:** A stack can declare `extends:` in `stack.yaml` to inherit skills and profiles from a parent stack. The parent is pulled to `.stacks/` via `agentic-stacks pull`. `resolve_extends()` in `manifest.py` locates the parent manifest.

**Overrides:** Each environment can have an `overrides/` subdirectory containing YAML files that merge on top of the composed config. `load_overrides()` in `profiles.py` loads and merges them.

**Config build pipeline:** `build_config()` in `profiles.py` runs the full merge: profiles → environment → overrides, with enforced key protection across all three layers.

**Operator project:** `agentic-stacks init --extends namespace/name@version` scaffolds a project that inherits from a base stack. It creates `environments/`, `state/`, `stacks.lock`, and `.gitignore` but no `skills/` or `profiles/` (those come from the parent).
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with extends and overrides architecture"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-28-extends-and-overrides.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?