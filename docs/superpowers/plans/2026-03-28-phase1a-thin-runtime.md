# Phase 1a: `agentic_stacks` Thin Runtime — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the thin runtime Python package that handles the mechanical parts universal to every stack: profile loading/merging, environment validation, config diffing, state tracking, approval gates, and manifest parsing.

**Architecture:** A pure Python library with no stack-specific logic. Each module has one responsibility and a clean interface. Stacks import what they need. No abstract base classes — concrete implementations that work. The package lives in `src/agentic_stacks/` in this repo and is published to PyPI as `agentic-stacks`.

**Tech Stack:** Python 3.11+, PyYAML, jsonschema, pytest, hatchling (build)

---

## File Structure

```
agentic-stacks/
├── src/
│   └── agentic_stacks/
│       ├── __init__.py              # Package version, public API re-exports
│       ├── manifest.py              # stack.yaml parsing and validation
│       ├── profiles.py              # Profile loading, category ordering, deep merge
│       ├── environments.py          # Environment CRUD and schema validation
│       ├── config_diff.py           # Diff current vs proposed config
│       ├── state_store.py           # Append-only action log
│       ├── approval.py              # Approval gate engine (auto/notify/human)
│       └── schema.py                # JSON Schema validation utilities
├── tests/
│   ├── conftest.py                  # Shared fixtures (tmp dirs, sample stacks)
│   ├── test_manifest.py
│   ├── test_profiles.py
│   ├── test_environments.py
│   ├── test_config_diff.py
│   ├── test_state_store.py
│   ├── test_approval.py
│   └── test_schema.py
├── pyproject.toml                   # Package build config (replaces placeholder)
└── tests/fixtures/                  # Sample stack structures for testing
    └── sample-stack/
        ├── stack.yaml
        ├── profiles/
        │   ├── security/
        │   │   └── baseline.yml
        │   ├── networking/
        │   │   ├── option-a.yml
        │   │   └── option-b.yml
        │   └── storage/
        │       └── default.yml
        └── environments/
            ├── _schema.json
            └── dev/
                └── environment.yml
```

---

### Task 1: Project Setup

**Files:**
- Modify: `pyproject.toml` (replace placeholder with real config)
- Create: `src/agentic_stacks/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/sample-stack/stack.yaml`
- Create: `tests/fixtures/sample-stack/profiles/security/baseline.yml`
- Create: `tests/fixtures/sample-stack/profiles/networking/option-a.yml`
- Create: `tests/fixtures/sample-stack/profiles/networking/option-b.yml`
- Create: `tests/fixtures/sample-stack/profiles/storage/default.yml`
- Create: `tests/fixtures/sample-stack/environments/_schema.json`
- Create: `tests/fixtures/sample-stack/environments/dev/environment.yml`

- [ ] **Step 1: Create pyproject.toml with dev dependencies**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agentic-stacks"
version = "0.1.0"
description = "Agentic Stacks"
requires-python = ">=3.11"
authors = [
    { name = "Agentic Stacks" },
]
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]

[tool.hatch.build.targets.wheel]
packages = ["src/agentic_stacks"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package __init__.py**

```python
"""Agentic Stacks — thin runtime for composed domain expertise."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create test fixtures — sample stack.yaml**

```yaml
# tests/fixtures/sample-stack/stack.yaml
name: sample-stack
namespace: test
version: "1.0.0"
description: "A sample stack for testing"

target:
  software: sample
  versions: ["1.0", "2.0"]

skills:
  - name: deploy
    entry: skills/deploy/
    description: "Deploy the thing"
  - name: health-check
    entry: skills/health-check/
    description: "Check if the thing is healthy"

profiles:
  categories: [security, networking, storage]
  path: profiles/
  merge_order: "security first (enforced), then declared order"

environment_schema: environments/_schema.json

depends_on: []

requires:
  tools: [sample-tool]
  python: ">=3.11"

deprecations:
  - skill: old-deploy
    since: "0.9.0"
    removal: "2.0.0"
    replacement: deploy
    reason: "Replaced with improved deploy skill"
```

- [ ] **Step 4: Create test fixtures — profiles**

```yaml
# tests/fixtures/sample-stack/profiles/security/baseline.yml
security:
  level: baseline
  enforced: true
  tls_required: true
  min_password_length: 16
```

```yaml
# tests/fixtures/sample-stack/profiles/networking/option-a.yml
networking:
  driver: option-a
  mtu: 1500
  dns_servers:
    - 8.8.8.8
```

```yaml
# tests/fixtures/sample-stack/profiles/networking/option-b.yml
networking:
  driver: option-b
  mtu: 9000
  dns_servers:
    - 1.1.1.1
```

```yaml
# tests/fixtures/sample-stack/profiles/storage/default.yml
storage:
  backend: local
  path: /var/data
```

- [ ] **Step 5: Create test fixtures — environment schema and example**

```json
// tests/fixtures/sample-stack/environments/_schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "profiles"],
  "properties": {
    "name": { "type": "string" },
    "description": { "type": "string" },
    "profiles": {
      "type": "object",
      "required": ["security", "networking", "storage"],
      "properties": {
        "security": { "type": "string" },
        "networking": { "type": "string" },
        "storage": { "type": "string" }
      }
    },
    "approval": {
      "type": "object",
      "properties": {
        "tier": { "type": "string", "enum": ["auto", "auto-notify", "human-approve"] }
      }
    }
  }
}
```

```yaml
# tests/fixtures/sample-stack/environments/dev/environment.yml
name: dev
description: Development environment

profiles:
  security: baseline
  networking: option-a
  storage: default

approval:
  tier: auto
```

- [ ] **Step 6: Create conftest.py with shared fixtures**

```python
# tests/conftest.py
import pathlib
import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_stack_path():
    return FIXTURES_DIR / "sample-stack"


@pytest.fixture
def sample_profiles_path(sample_stack_path):
    return sample_stack_path / "profiles"


@pytest.fixture
def sample_environments_path(sample_stack_path):
    return sample_stack_path / "environments"
```

- [ ] **Step 7: Set up venv and verify pytest runs**

Run: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && pytest --co`

Expected: "no tests ran" (collected 0 items) — confirms setup works.

- [ ] **Step 8: Commit**

```bash
git init
git add pyproject.toml src/ tests/
git commit -m "feat: project setup with fixtures and dev dependencies"
```

---

### Task 2: Schema Validation Utilities

**Files:**
- Create: `src/agentic_stacks/schema.py`
- Create: `tests/test_schema.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_schema.py
import json
import pytest
from agentic_stacks.schema import validate_against_schema, ValidationError


def test_valid_data_passes(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {
        "name": "dev",
        "profiles": {
            "security": "baseline",
            "networking": "option-a",
            "storage": "default",
        },
    }
    # Should not raise
    validate_against_schema(data, schema)


def test_missing_required_field_raises(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {"name": "dev"}  # missing 'profiles'
    with pytest.raises(ValidationError, match="profiles"):
        validate_against_schema(data, schema)


def test_invalid_enum_value_raises(sample_stack_path):
    schema_path = sample_stack_path / "environments" / "_schema.json"
    schema = json.loads(schema_path.read_text())
    data = {
        "name": "dev",
        "profiles": {
            "security": "baseline",
            "networking": "option-a",
            "storage": "default",
        },
        "approval": {"tier": "invalid-tier"},
    }
    with pytest.raises(ValidationError, match="invalid-tier"):
        validate_against_schema(data, schema)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_schema.py -v`

Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 3: Implement schema.py**

```python
# src/agentic_stacks/schema.py
"""JSON Schema validation utilities."""

import jsonschema


class ValidationError(Exception):
    """Raised when data fails schema validation."""

    def __init__(self, message: str, errors: list[str]):
        self.errors = errors
        super().__init__(message)


def validate_against_schema(data: dict, schema: dict) -> None:
    """Validate data against a JSON Schema. Raises ValidationError on failure."""
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.absolute_path)
            prefix = f"{path}: " if path else ""
            messages.append(f"{prefix}{error.message}")
        raise ValidationError(
            f"Validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {m}" for m in messages),
            errors=messages,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_schema.py -v`

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/schema.py tests/test_schema.py
git commit -m "feat: schema validation utilities"
```

---

### Task 3: Stack Manifest Parser

**Files:**
- Create: `src/agentic_stacks/manifest.py`
- Create: `tests/test_manifest.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_manifest.py
import pytest
from agentic_stacks.manifest import load_manifest, ManifestError


def test_load_valid_manifest(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["name"] == "sample-stack"
    assert manifest["namespace"] == "test"
    assert manifest["version"] == "1.0.0"
    assert len(manifest["skills"]) == 2
    assert manifest["skills"][0]["name"] == "deploy"
    assert manifest["profiles"]["categories"] == ["security", "networking", "storage"]
    assert manifest["target"]["versions"] == ["1.0", "2.0"]


def test_load_manifest_missing_file(tmp_path):
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(tmp_path / "nonexistent.yaml")


def test_load_manifest_missing_required_fields(tmp_path):
    bad_manifest = tmp_path / "stack.yaml"
    bad_manifest.write_text("description: missing name and version\n")
    with pytest.raises(ManifestError, match="name"):
        load_manifest(bad_manifest)


def test_manifest_deprecations(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert len(manifest["deprecations"]) == 1
    dep = manifest["deprecations"][0]
    assert dep["skill"] == "old-deploy"
    assert dep["replacement"] == "deploy"


def test_manifest_full_name(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["full_name"] == "test/sample-stack"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_manifest.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement manifest.py**

```python
# src/agentic_stacks/manifest.py
"""Stack manifest (stack.yaml) parsing and validation."""

import pathlib
import yaml


REQUIRED_FIELDS = ["name", "namespace", "version", "description"]


class ManifestError(Exception):
    """Raised when a stack manifest is invalid or missing."""
    pass


def load_manifest(path: pathlib.Path) -> dict:
    """Load and validate a stack.yaml manifest file.

    Args:
        path: Path to stack.yaml file.

    Returns:
        Parsed manifest dict with computed 'full_name' field added.

    Raises:
        ManifestError: If the file is missing or has invalid content.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        text = path.read_text()
        manifest = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ManifestError(f"Invalid YAML in {path}: {e}")

    if not isinstance(manifest, dict):
        raise ManifestError(f"Manifest must be a YAML mapping, got {type(manifest).__name__}")

    missing = [f for f in REQUIRED_FIELDS if f not in manifest]
    if missing:
        raise ManifestError(
            f"Manifest {path} missing required fields: {', '.join(missing)}"
        )

    manifest.setdefault("skills", [])
    manifest.setdefault("profiles", {"categories": [], "path": "profiles/"})
    manifest.setdefault("depends_on", [])
    manifest.setdefault("deprecations", [])
    manifest.setdefault("requires", {})
    manifest.setdefault("target", {"software": "", "versions": []})

    manifest["full_name"] = f"{manifest['namespace']}/{manifest['name']}"

    return manifest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_manifest.py -v`

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/manifest.py tests/test_manifest.py
git commit -m "feat: stack manifest parser with validation"
```

---

### Task 4: Profile Engine

**Files:**
- Create: `src/agentic_stacks/profiles.py`
- Create: `tests/test_profiles.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_profiles.py
import pytest
from agentic_stacks.profiles import (
    load_profile,
    load_profiles_by_category,
    merge_profiles,
    EnforcedKeyError,
)


def test_load_single_profile(sample_profiles_path):
    profile = load_profile(sample_profiles_path / "security" / "baseline.yml")
    assert profile["security"]["level"] == "baseline"
    assert profile["security"]["enforced"] is True


def test_load_profiles_by_category(sample_profiles_path):
    profiles = load_profiles_by_category(
        sample_profiles_path,
        selections={"security": "baseline", "networking": "option-a", "storage": "default"},
        category_order=["security", "networking", "storage"],
    )
    assert len(profiles) == 3
    assert profiles[0]["security"]["level"] == "baseline"
    assert profiles[1]["networking"]["driver"] == "option-a"
    assert profiles[2]["storage"]["backend"] == "local"


def test_load_missing_profile_raises(sample_profiles_path):
    with pytest.raises(FileNotFoundError):
        load_profiles_by_category(
            sample_profiles_path,
            selections={"security": "nonexistent"},
            category_order=["security"],
        )


def test_merge_profiles_basic():
    profiles = [
        {"a": 1, "b": {"x": 10}},
        {"b": {"y": 20}, "c": 3},
    ]
    result = merge_profiles(profiles)
    assert result == {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}


def test_merge_profiles_later_overrides_earlier():
    profiles = [
        {"a": 1, "b": {"x": 10}},
        {"a": 2, "b": {"x": 99}},
    ]
    result = merge_profiles(profiles)
    assert result["a"] == 2
    assert result["b"]["x"] == 99


def test_merge_profiles_enforced_keys_protected():
    profiles = [
        {"security": {"tls_required": True, "enforced": True}},
        {"security": {"tls_required": False}},
    ]
    with pytest.raises(EnforcedKeyError, match="tls_required"):
        merge_profiles(profiles, enforced_marker="enforced")


def test_merge_profiles_enforced_allows_same_value():
    profiles = [
        {"security": {"tls_required": True, "enforced": True}},
        {"security": {"tls_required": True}},
    ]
    result = merge_profiles(profiles, enforced_marker="enforced")
    assert result["security"]["tls_required"] is True


def test_full_profile_pipeline(sample_profiles_path):
    profiles = load_profiles_by_category(
        sample_profiles_path,
        selections={"security": "baseline", "networking": "option-a", "storage": "default"},
        category_order=["security", "networking", "storage"],
    )
    merged = merge_profiles(profiles, enforced_marker="enforced")
    assert merged["security"]["tls_required"] is True
    assert merged["networking"]["driver"] == "option-a"
    assert merged["storage"]["backend"] == "local"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_profiles.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement profiles.py**

```python
# src/agentic_stacks/profiles.py
"""Profile loading, category ordering, and deep merge with enforced key protection."""

import copy
import pathlib
from typing import Any

import yaml


class EnforcedKeyError(Exception):
    """Raised when a merge attempts to override an enforced key."""
    pass


def load_profile(path: pathlib.Path) -> dict:
    """Load a single YAML profile file."""
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Profile must be a YAML mapping: {path}")
    return data


def load_profiles_by_category(
    profiles_dir: pathlib.Path,
    selections: dict[str, str],
    category_order: list[str],
) -> list[dict]:
    """Load profiles in category order based on selections.

    Args:
        profiles_dir: Root profiles/ directory.
        selections: Mapping of category name to profile name (e.g., {"networking": "option-a"}).
        category_order: Order in which to load categories (determines merge precedence).

    Returns:
        List of profile dicts, ordered by category_order.
    """
    profiles_dir = pathlib.Path(profiles_dir)
    result = []
    for category in category_order:
        if category not in selections:
            continue
        profile_name = selections[category]
        profile_path = profiles_dir / category / f"{profile_name}.yml"
        result.append(load_profile(profile_path))
    return result


def _collect_enforced_keys(data: dict, marker: str, path: str = "") -> dict[str, Any]:
    """Walk a dict and collect keys that are siblings of an enforced marker."""
    enforced = {}
    if isinstance(data, dict):
        if data.get(marker) is True:
            for key, value in data.items():
                if key != marker:
                    full_key = f"{path}.{key}" if path else key
                    enforced[full_key] = value
        for key, value in data.items():
            if key != marker and isinstance(value, dict):
                child_path = f"{path}.{key}" if path else key
                enforced.update(_collect_enforced_keys(value, marker, child_path))
    return enforced


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Returns a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _get_nested(data: dict, dotted_key: str) -> Any:
    """Get a value from a nested dict using a dotted key path."""
    keys = dotted_key.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return _SENTINEL
        current = current[key]
    return current


_SENTINEL = object()


def merge_profiles(
    profiles: list[dict],
    enforced_marker: str | None = None,
) -> dict:
    """Merge a list of profiles using deep merge.

    Args:
        profiles: List of profile dicts, in merge order (later overrides earlier).
        enforced_marker: If set, keys that are siblings of this marker in earlier
            profiles cannot be overridden to different values by later profiles.

    Returns:
        Merged profile dict.
    """
    if not profiles:
        return {}

    enforced_keys: dict[str, Any] = {}
    result = {}

    for profile in profiles:
        if enforced_marker:
            # Check if this profile tries to override any enforced key
            for enforced_path, enforced_value in enforced_keys.items():
                new_value = _get_nested(profile, enforced_path)
                if new_value is not _SENTINEL and new_value != enforced_value:
                    raise EnforcedKeyError(
                        f"Cannot override enforced key '{enforced_path}': "
                        f"tried to change {enforced_value!r} to {new_value!r}"
                    )

            # Collect any new enforced keys from this profile
            enforced_keys.update(
                _collect_enforced_keys(profile, enforced_marker)
            )

        result = _deep_merge(result, profile)

    # Remove enforced markers from the result
    if enforced_marker:
        _remove_marker(result, enforced_marker)

    return result


def _remove_marker(data: dict, marker: str) -> None:
    """Remove all instances of the enforced marker key from a nested dict."""
    keys_to_remove = [k for k in data if k == marker]
    for key in keys_to_remove:
        del data[key]
    for value in data.values():
        if isinstance(value, dict):
            _remove_marker(value, marker)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_profiles.py -v`

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/profiles.py tests/test_profiles.py
git commit -m "feat: profile engine with deep merge and enforced key protection"
```

---

### Task 5: Environment Manager

**Files:**
- Create: `src/agentic_stacks/environments.py`
- Create: `tests/test_environments.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_environments.py
import json
import shutil
import pytest
import yaml
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    create_environment,
    validate_environment,
    EnvironmentError,
)


def test_load_environment(sample_environments_path):
    env = load_environment(sample_environments_path / "dev")
    assert env["name"] == "dev"
    assert env["profiles"]["networking"] == "option-a"


def test_load_missing_environment(sample_environments_path):
    with pytest.raises(EnvironmentError, match="not found"):
        load_environment(sample_environments_path / "nonexistent")


def test_list_environments(sample_environments_path):
    envs = list_environments(sample_environments_path)
    assert "dev" in envs


def test_create_environment(tmp_path):
    envs_dir = tmp_path / "environments"
    envs_dir.mkdir()
    env_data = {
        "name": "staging",
        "profiles": {
            "security": "baseline",
            "networking": "option-a",
            "storage": "default",
        },
        "approval": {"tier": "auto-notify"},
    }
    create_environment(envs_dir, "staging", env_data)
    assert (envs_dir / "staging" / "environment.yml").exists()
    loaded = yaml.safe_load((envs_dir / "staging" / "environment.yml").read_text())
    assert loaded["name"] == "staging"


def test_create_duplicate_environment_raises(tmp_path):
    envs_dir = tmp_path / "environments"
    envs_dir.mkdir()
    env_data = {"name": "dev", "profiles": {"security": "baseline"}}
    create_environment(envs_dir, "dev", env_data)
    with pytest.raises(EnvironmentError, match="already exists"):
        create_environment(envs_dir, "dev", env_data)


def test_validate_environment_valid(sample_stack_path):
    schema = json.loads(
        (sample_stack_path / "environments" / "_schema.json").read_text()
    )
    env = yaml.safe_load(
        (sample_stack_path / "environments" / "dev" / "environment.yml").read_text()
    )
    # Should not raise
    validate_environment(env, schema)


def test_validate_environment_invalid(sample_stack_path):
    schema = json.loads(
        (sample_stack_path / "environments" / "_schema.json").read_text()
    )
    env = {"name": "bad"}  # missing profiles
    with pytest.raises(EnvironmentError, match="profiles"):
        validate_environment(env, schema)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_environments.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement environments.py**

```python
# src/agentic_stacks/environments.py
"""Environment CRUD and schema validation."""

import pathlib

import yaml

from agentic_stacks.schema import validate_against_schema, ValidationError


class EnvironmentError(Exception):
    """Raised on environment operation failures."""
    pass


def load_environment(env_dir: pathlib.Path) -> dict:
    """Load an environment.yml from an environment directory.

    Args:
        env_dir: Path to the environment directory (e.g., environments/dev/).

    Returns:
        Parsed environment dict.
    """
    env_dir = pathlib.Path(env_dir)
    env_file = env_dir / "environment.yml"
    if not env_file.exists():
        raise EnvironmentError(f"Environment not found: {env_dir}")
    with open(env_file) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise EnvironmentError(f"Environment must be a YAML mapping: {env_file}")
    return data


def list_environments(environments_dir: pathlib.Path) -> list[str]:
    """List all environment names in an environments directory.

    Returns directories that contain an environment.yml file.
    Skips entries starting with '_' (like _schema.json).
    """
    environments_dir = pathlib.Path(environments_dir)
    if not environments_dir.exists():
        return []
    return sorted(
        d.name
        for d in environments_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "environment.yml").exists()
    )


def create_environment(
    environments_dir: pathlib.Path,
    name: str,
    data: dict,
) -> pathlib.Path:
    """Create a new environment directory with an environment.yml.

    Args:
        environments_dir: Root environments/ directory.
        name: Name for the new environment.
        data: Environment data to write.

    Returns:
        Path to the created environment directory.
    """
    environments_dir = pathlib.Path(environments_dir)
    env_dir = environments_dir / name
    if env_dir.exists():
        raise EnvironmentError(f"Environment already exists: {env_dir}")
    env_dir.mkdir(parents=True)
    env_file = env_dir / "environment.yml"
    with open(env_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return env_dir


def validate_environment(data: dict, schema: dict) -> None:
    """Validate environment data against a JSON Schema.

    Raises EnvironmentError with details on failure.
    """
    try:
        validate_against_schema(data, schema)
    except ValidationError as e:
        raise EnvironmentError(str(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_environments.py -v`

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/environments.py tests/test_environments.py
git commit -m "feat: environment manager with CRUD and validation"
```

---

### Task 6: Config Diff Engine

**Files:**
- Create: `src/agentic_stacks/config_diff.py`
- Create: `tests/test_config_diff.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config_diff.py
from agentic_stacks.config_diff import diff_configs, DiffEntry


def test_no_changes():
    old = {"a": 1, "b": {"x": 10}}
    new = {"a": 1, "b": {"x": 10}}
    result = diff_configs(old, new)
    assert result == []


def test_value_changed():
    old = {"a": 1}
    new = {"a": 2}
    result = diff_configs(old, new)
    assert len(result) == 1
    assert result[0] == DiffEntry(path="a", old=1, new=2, kind="changed")


def test_key_added():
    old = {"a": 1}
    new = {"a": 1, "b": 2}
    result = diff_configs(old, new)
    assert len(result) == 1
    assert result[0] == DiffEntry(path="b", old=None, new=2, kind="added")


def test_key_removed():
    old = {"a": 1, "b": 2}
    new = {"a": 1}
    result = diff_configs(old, new)
    assert len(result) == 1
    assert result[0] == DiffEntry(path="b", old=2, new=None, kind="removed")


def test_nested_changes():
    old = {"a": {"b": {"c": 1}}}
    new = {"a": {"b": {"c": 2}}}
    result = diff_configs(old, new)
    assert len(result) == 1
    assert result[0] == DiffEntry(path="a.b.c", old=1, new=2, kind="changed")


def test_mixed_changes():
    old = {"keep": 1, "change": "old", "remove": True, "nested": {"a": 1}}
    new = {"keep": 1, "change": "new", "add": "hi", "nested": {"a": 1, "b": 2}}
    result = diff_configs(old, new)
    paths = {r.path: r for r in result}
    assert "keep" not in paths
    assert paths["change"].kind == "changed"
    assert paths["remove"].kind == "removed"
    assert paths["add"].kind == "added"
    assert paths["nested.b"].kind == "added"


def test_format_diff():
    old = {"a": 1, "b": 2}
    new = {"a": 99, "c": 3}
    result = diff_configs(old, new)
    formatted = "\n".join(entry.format() for entry in result)
    assert "a:" in formatted
    assert "1" in formatted
    assert "99" in formatted
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_diff.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement config_diff.py**

```python
# src/agentic_stacks/config_diff.py
"""Diff current vs proposed configuration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiffEntry:
    path: str
    old: Any
    new: Any
    kind: str  # "added", "removed", "changed"

    def format(self) -> str:
        if self.kind == "added":
            return f"  + {self.path}: {self.new!r}"
        elif self.kind == "removed":
            return f"  - {self.path}: {self.old!r}"
        else:
            return f"  ~ {self.path}: {self.old!r} → {self.new!r}"


def diff_configs(old: dict, new: dict, _prefix: str = "") -> list[DiffEntry]:
    """Compare two config dicts and return a list of differences.

    Args:
        old: The current/existing config.
        new: The proposed/new config.

    Returns:
        List of DiffEntry describing each change.
    """
    entries = []
    all_keys = sorted(set(list(old.keys()) + list(new.keys())))

    for key in all_keys:
        path = f"{_prefix}.{key}" if _prefix else key
        in_old = key in old
        in_new = key in new

        if in_old and not in_new:
            entries.append(DiffEntry(path=path, old=old[key], new=None, kind="removed"))
        elif in_new and not in_old:
            entries.append(DiffEntry(path=path, old=None, new=new[key], kind="added"))
        elif isinstance(old[key], dict) and isinstance(new[key], dict):
            entries.extend(diff_configs(old[key], new[key], _prefix=path))
        elif old[key] != new[key]:
            entries.append(DiffEntry(path=path, old=old[key], new=new[key], kind="changed"))

    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_diff.py -v`

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/config_diff.py tests/test_config_diff.py
git commit -m "feat: config diff engine"
```

---

### Task 7: Append-Only State Store

**Files:**
- Create: `src/agentic_stacks/state_store.py`
- Create: `tests/test_state_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_state_store.py
import json
from datetime import datetime, timezone
from agentic_stacks.state_store import StateStore


def test_empty_store(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    assert store.list() == []


def test_append_and_list(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(
        action="deploy",
        environment="dev",
        actor="operator",
        outcome="success",
        details={"version": "1.0"},
    )
    entries = store.list()
    assert len(entries) == 1
    assert entries[0]["action"] == "deploy"
    assert entries[0]["environment"] == "dev"
    assert entries[0]["actor"] == "operator"
    assert entries[0]["outcome"] == "success"
    assert entries[0]["details"] == {"version": "1.0"}
    assert "timestamp" in entries[0]


def test_append_multiple(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="success")
    store.append(action="upgrade", environment="staging", actor="operator", outcome="failed")
    assert len(store.list()) == 3


def test_filter_by_environment(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="deploy", environment="prod", actor="agent", outcome="success")
    dev_entries = store.list(environment="dev")
    assert len(dev_entries) == 1
    assert dev_entries[0]["environment"] == "dev"


def test_filter_by_action(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="success")
    deploys = store.list(action="deploy")
    assert len(deploys) == 1


def test_persistence_across_instances(tmp_path):
    state_file = tmp_path / "state.jsonl"
    store1 = StateStore(state_file)
    store1.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store2 = StateStore(state_file)
    assert len(store2.list()) == 1


def test_last(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="failed")
    last = store.last(environment="dev")
    assert last["action"] == "health-check"
    assert last["outcome"] == "failed"


def test_last_empty(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    assert store.last() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state_store.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement state_store.py**

```python
# src/agentic_stacks/state_store.py
"""Append-only state store for tracking actions."""

import json
import pathlib
from datetime import datetime, timezone
from typing import Any


class StateStore:
    """Append-only log of actions taken, stored as JSONL.

    Each entry records: action, environment, actor, outcome, details, timestamp.
    The file is human-readable and git-friendly.
    """

    def __init__(self, path: pathlib.Path):
        self._path = pathlib.Path(path)

    def append(
        self,
        action: str,
        environment: str,
        actor: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict:
        """Append an entry to the state store.

        Args:
            action: What was done (e.g., "deploy", "health-check").
            environment: Which environment (e.g., "dev", "prod").
            actor: Who did it (e.g., "operator", "agent").
            outcome: Result (e.g., "success", "failed").
            details: Optional extra data.

        Returns:
            The entry that was written.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "environment": environment,
            "actor": actor,
            "outcome": outcome,
            "details": details or {},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def list(
        self,
        environment: str | None = None,
        action: str | None = None,
    ) -> list[dict]:
        """Read all entries, optionally filtered.

        Args:
            environment: Filter to this environment.
            action: Filter to this action type.

        Returns:
            List of entry dicts, oldest first.
        """
        if not self._path.exists():
            return []
        entries = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if environment and entry.get("environment") != environment:
                    continue
                if action and entry.get("action") != action:
                    continue
                entries.append(entry)
        return entries

    def last(
        self,
        environment: str | None = None,
        action: str | None = None,
    ) -> dict | None:
        """Return the most recent entry matching filters, or None."""
        entries = self.list(environment=environment, action=action)
        return entries[-1] if entries else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state_store.py -v`

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/state_store.py tests/test_state_store.py
git commit -m "feat: append-only state store"
```

---

### Task 8: Approval Gate Engine

**Files:**
- Create: `src/agentic_stacks/approval.py`
- Create: `tests/test_approval.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_approval.py
import pytest
from agentic_stacks.approval import (
    ApprovalGate,
    ApprovalResult,
    ApprovalTier,
)


def test_auto_tier_approves_immediately():
    gate = ApprovalGate(tier=ApprovalTier.AUTO)
    result = gate.request(
        action="deploy",
        environment="dev",
        description="Deploy to dev",
    )
    assert result.approved is True
    assert result.tier == ApprovalTier.AUTO


def test_auto_notify_approves_with_notification():
    notifications = []
    gate = ApprovalGate(
        tier=ApprovalTier.AUTO_NOTIFY,
        notify_fn=lambda msg: notifications.append(msg),
    )
    result = gate.request(
        action="deploy",
        environment="staging",
        description="Deploy to staging",
    )
    assert result.approved is True
    assert result.tier == ApprovalTier.AUTO_NOTIFY
    assert len(notifications) == 1
    assert "staging" in notifications[0]


def test_human_approve_uses_prompt():
    gate = ApprovalGate(
        tier=ApprovalTier.HUMAN_APPROVE,
        prompt_fn=lambda msg: True,
    )
    result = gate.request(
        action="deploy",
        environment="prod",
        description="Deploy to prod",
    )
    assert result.approved is True
    assert result.tier == ApprovalTier.HUMAN_APPROVE


def test_human_approve_rejection():
    gate = ApprovalGate(
        tier=ApprovalTier.HUMAN_APPROVE,
        prompt_fn=lambda msg: False,
    )
    result = gate.request(
        action="deploy",
        environment="prod",
        description="Deploy to prod",
    )
    assert result.approved is False


def test_human_approve_no_prompt_fn_raises():
    gate = ApprovalGate(tier=ApprovalTier.HUMAN_APPROVE)
    with pytest.raises(RuntimeError, match="prompt_fn"):
        gate.request(action="deploy", environment="prod", description="Deploy")


def test_from_string():
    assert ApprovalTier.from_string("auto") == ApprovalTier.AUTO
    assert ApprovalTier.from_string("auto-notify") == ApprovalTier.AUTO_NOTIFY
    assert ApprovalTier.from_string("human-approve") == ApprovalTier.HUMAN_APPROVE


def test_from_string_invalid():
    with pytest.raises(ValueError, match="Unknown"):
        ApprovalTier.from_string("invalid")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_approval.py -v`

Expected: FAIL with ImportError

- [ ] **Step 3: Implement approval.py**

```python
# src/agentic_stacks/approval.py
"""Approval gate engine — auto, auto-notify, or human-approve."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ApprovalTier(Enum):
    AUTO = "auto"
    AUTO_NOTIFY = "auto-notify"
    HUMAN_APPROVE = "human-approve"

    @classmethod
    def from_string(cls, value: str) -> "ApprovalTier":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown approval tier: {value!r}. "
            f"Valid tiers: {', '.join(m.value for m in cls)}"
        )


@dataclass(frozen=True)
class ApprovalResult:
    approved: bool
    tier: ApprovalTier
    action: str
    environment: str
    description: str


class ApprovalGate:
    """Gate that controls whether an action can proceed.

    Args:
        tier: The approval tier for this gate.
        notify_fn: Called with a message string for auto-notify tier.
        prompt_fn: Called with a message string for human-approve tier.
            Must return True (approved) or False (rejected).
    """

    def __init__(
        self,
        tier: ApprovalTier,
        notify_fn: Callable[[str], None] | None = None,
        prompt_fn: Callable[[str], bool] | None = None,
    ):
        self._tier = tier
        self._notify_fn = notify_fn
        self._prompt_fn = prompt_fn

    def request(
        self,
        action: str,
        environment: str,
        description: str,
    ) -> ApprovalResult:
        """Request approval for an action.

        Returns:
            ApprovalResult indicating whether the action was approved.
        """
        message = f"[{self._tier.value}] {action} on {environment}: {description}"

        if self._tier == ApprovalTier.AUTO:
            approved = True

        elif self._tier == ApprovalTier.AUTO_NOTIFY:
            approved = True
            if self._notify_fn:
                self._notify_fn(message)

        elif self._tier == ApprovalTier.HUMAN_APPROVE:
            if self._prompt_fn is None:
                raise RuntimeError(
                    "prompt_fn is required for human-approve tier"
                )
            approved = self._prompt_fn(message)

        else:
            approved = False

        return ApprovalResult(
            approved=approved,
            tier=self._tier,
            action=action,
            environment=environment,
            description=description,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_approval.py -v`

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/approval.py tests/test_approval.py
git commit -m "feat: approval gate engine"
```

---

### Task 9: Public API and Integration Test

**Files:**
- Modify: `src/agentic_stacks/__init__.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write failing integration test**

```python
# tests/test_integration.py
"""End-to-end test: load a stack, merge profiles, validate env, diff, track state."""
import json
from agentic_stacks import (
    load_manifest,
    load_profiles_by_category,
    merge_profiles,
    load_environment,
    validate_environment,
    diff_configs,
    StateStore,
    ApprovalGate,
    ApprovalTier,
)


def test_full_pipeline(sample_stack_path, tmp_path):
    # 1. Load manifest
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["full_name"] == "test/sample-stack"

    # 2. Load environment
    env = load_environment(sample_stack_path / "environments" / "dev")
    assert env["name"] == "dev"

    # 3. Validate environment against schema
    schema = json.loads(
        (sample_stack_path / "environments" / "_schema.json").read_text()
    )
    validate_environment(env, schema)

    # 4. Load and merge profiles based on environment selections
    profiles = load_profiles_by_category(
        sample_stack_path / "profiles",
        selections=env["profiles"],
        category_order=manifest["profiles"]["categories"],
    )
    merged = merge_profiles(profiles, enforced_marker="enforced")
    assert merged["security"]["tls_required"] is True
    assert merged["networking"]["driver"] == "option-a"

    # 5. Diff against a hypothetical "current" config
    current = {"security": {"tls_required": True}, "networking": {"driver": "option-b"}}
    diffs = diff_configs(current, merged)
    changed_paths = {d.path for d in diffs}
    assert "networking.driver" in changed_paths

    # 6. Approval gate
    tier = ApprovalTier.from_string(env["approval"]["tier"])
    gate = ApprovalGate(tier=tier)
    result = gate.request(
        action="deploy",
        environment=env["name"],
        description="Deploy dev environment",
    )
    assert result.approved is True

    # 7. Track in state store
    store = StateStore(tmp_path / "state.jsonl")
    store.append(
        action="deploy",
        environment=env["name"],
        actor="agent",
        outcome="success",
        details={"stack": manifest["full_name"], "version": manifest["version"]},
    )
    last = store.last(environment="dev")
    assert last["outcome"] == "success"
    assert last["details"]["stack"] == "test/sample-stack"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`

Expected: FAIL with ImportError (public API not exported yet)

- [ ] **Step 3: Update __init__.py with public API**

```python
# src/agentic_stacks/__init__.py
"""Agentic Stacks — thin runtime for composed domain expertise."""

__version__ = "0.1.0"

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks.profiles import (
    load_profile,
    load_profiles_by_category,
    merge_profiles,
    EnforcedKeyError,
)
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    create_environment,
    validate_environment,
    EnvironmentError,
)
from agentic_stacks.config_diff import diff_configs, DiffEntry
from agentic_stacks.state_store import StateStore
from agentic_stacks.approval import ApprovalGate, ApprovalResult, ApprovalTier
from agentic_stacks.schema import validate_against_schema, ValidationError

__all__ = [
    "load_manifest",
    "ManifestError",
    "load_profile",
    "load_profiles_by_category",
    "merge_profiles",
    "EnforcedKeyError",
    "load_environment",
    "list_environments",
    "create_environment",
    "validate_environment",
    "EnvironmentError",
    "diff_configs",
    "DiffEntry",
    "StateStore",
    "ApprovalGate",
    "ApprovalResult",
    "ApprovalTier",
    "validate_against_schema",
    "ValidationError",
]
```

- [ ] **Step 4: Run all tests**

Run: `pytest -v`

Expected: All tests pass (schema: 3, manifest: 5, profiles: 8, environments: 7, config_diff: 7, state_store: 8, approval: 7, integration: 1 = 46 total)

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks/__init__.py tests/test_integration.py
git commit -m "feat: public API exports and integration test"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

Run: `pip install pytest-cov && pytest --cov=agentic_stacks --cov-report=term-missing -v`

Expected: All 46 tests pass, high coverage across all modules.

- [ ] **Step 2: Verify package builds cleanly**

Run: `rm -rf dist && pyproject-build`

Expected: Successfully builds wheel and sdist.

- [ ] **Step 3: Verify package installs and imports**

Run: `pip install dist/agentic_stacks-0.1.0-py3-none-any.whl --force-reinstall && python3 -c "import agentic_stacks; print(agentic_stacks.__version__)"`

Expected: Prints `0.1.0`

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final verification — all tests passing, package builds clean"
```
