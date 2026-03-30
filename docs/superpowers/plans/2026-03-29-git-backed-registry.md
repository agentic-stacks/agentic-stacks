# Git-Backed Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Homebrew-style git-backed registry where a central repo holds formula YAML files pointing to stack source repos, and the CLI searches/pulls from local formulas instead of the API.

**Architecture:** The registry repo (`github.com/agentic-stacks/registry`) contains formula YAML files scoped by owner (`stacks/<owner>/<name>.yaml`). A GitHub Action auto-syncs formulas from stack repos in the `agentic-stacks` org. The CLI clones/caches the registry repo locally at `~/.config/agentic-stacks/registry/` and reads formulas for search and pull operations. The existing DB/API stays as a website cache.

**Tech Stack:** Python, PyYAML, Click, subprocess (git), pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/agentic_stacks_cli/registry_repo.py` | Create | Clone/update registry repo cache, read/search/write formulas |
| `src/agentic_stacks_cli/commands/search.py` | Rewrite | Search local formulas instead of API |
| `src/agentic_stacks_cli/commands/pull.py` | Modify | Resolve stacks via formulas when pulling by reference |
| `src/agentic_stacks_cli/commands/publish.py` | Modify | Generate formula + open PR to registry repo |
| `src/agentic_stacks_cli/config.py` | Modify | Add `registry_repo` default |
| `tests/fixtures/registry/stacks/agentic-stacks/openstack-kolla.yaml` | Create | Test fixture formula |
| `tests/fixtures/registry/stacks/agentic-stacks/kubernetes-talos.yaml` | Create | Test fixture formula |
| `tests/fixtures/registry/stacks/agentic-stacks/dell-hardware.yaml` | Create | Test fixture formula |
| `tests/test_registry_repo.py` | Create | Tests for formula read/search/write |
| `tests/test_cli_search.py` | Rewrite | Tests for formula-based search |
| `tests/test_cli_pull.py` | Modify | Tests for formula-based pull |

---

### Task 1: Formula Fixtures

Create test fixture formulas for the 3 existing stacks. These are the canonical formula format.

**Files:**
- Create: `tests/fixtures/registry/stacks/agentic-stacks/openstack-kolla.yaml`
- Create: `tests/fixtures/registry/stacks/agentic-stacks/kubernetes-talos.yaml`
- Create: `tests/fixtures/registry/stacks/agentic-stacks/dell-hardware.yaml`

- [ ] **Step 1: Create openstack-kolla formula**

Create `tests/fixtures/registry/stacks/agentic-stacks/openstack-kolla.yaml`:

```yaml
name: openstack-kolla
owner: agentic-stacks
version: "0.1.0"
repository: https://github.com/agentic-stacks/openstack-kolla
tag: v0.1.0
sha256: ""
description: >
  Agent-driven OpenStack cloud deployment and operations using kolla-ansible.
target:
  software: openstack
  versions: ["2025.1", "2025.2"]
skills:
  - name: config-build
    description: "Build globals.yml, inventory, and service configs from operator requirements"
  - name: deploy
    description: "Full kolla-ansible deploy lifecycle"
  - name: health-check
    description: "Validate environment health"
  - name: diagnose
    description: "Systematic troubleshooting"
  - name: day-two
    description: "Day-two operations"
  - name: decision-guides
    description: "Choose between networking and storage options"
  - name: compatibility
    description: "Version compatibility matrix"
  - name: known-issues
    description: "Known bugs and workarounds"
depends_on: []
requires:
  tools:
    - kolla-ansible
    - openstack
    - docker
  python: ">=3.11"
```

- [ ] **Step 2: Create kubernetes-talos formula**

Create `tests/fixtures/registry/stacks/agentic-stacks/kubernetes-talos.yaml`:

```yaml
name: kubernetes-talos
owner: agentic-stacks
version: "0.1.0"
repository: https://github.com/agentic-stacks/kubernetes-talos
tag: v0.1.0
sha256: ""
description: >
  Complete operational knowledge for deploying and operating production
  Kubernetes clusters using Talos Linux.
target:
  software: talos-linux
  versions: ["1.9.x", "1.8.x"]
skills:
  - name: concepts
    description: "Talos architecture, immutable OS model, API-driven operations"
  - name: machine-config
    description: "Generating, patching, and managing Talos machine configurations"
  - name: infrastructure
    description: "Platform-specific provisioning (bare metal, VM, cloud)"
  - name: bootstrap
    description: "Initial cluster creation"
  - name: networking
    description: "CNI selection and configuration"
  - name: storage
    description: "CSI selection and configuration"
  - name: gitops
    description: "Flux and ArgoCD bootstrap"
  - name: ingress
    description: "Ingress controllers and TLS automation"
  - name: observability
    description: "Monitoring, logging, tracing"
  - name: security
    description: "Policy engines, secrets management, RBAC"
  - name: health-check
    description: "Cluster validation procedures"
  - name: scaling
    description: "Adding/removing nodes"
  - name: upgrades
    description: "Rolling upgrade procedures"
  - name: backup-restore
    description: "etcd backup, Velero, disaster recovery"
  - name: certificate-mgmt
    description: "Certificate rotation and monitoring"
  - name: troubleshooting
    description: "Symptom-based diagnostic decision trees"
  - name: known-issues
    description: "Version-specific bugs and workarounds"
  - name: compatibility
    description: "Component compatibility matrices"
  - name: decision-guides
    description: "Trade-off matrices for choosing components"
depends_on: []
requires:
  tools:
    - talosctl
    - kubectl
    - helm
```

- [ ] **Step 3: Create dell-hardware formula**

Create `tests/fixtures/registry/stacks/agentic-stacks/dell-hardware.yaml`:

```yaml
name: dell-hardware
owner: agentic-stacks
version: "0.2.0"
repository: https://github.com/agentic-stacks/dell-hardware
tag: v0.2.0
sha256: ""
description: >
  Teaches AI agents to manage Dell PowerEdge server hardware — BIOS, iDRAC,
  RAID, firmware updates, and hardware inventory.
target:
  software: Dell PowerEdge / iDRAC
  versions: ["iDRAC9 (14G/15G/16G)", "iDRAC10 (17G)"]
skills:
  - name: concepts
    description: "PowerEdge architecture, iDRAC fundamentals"
  - name: tools
    description: "Tool landscape — racadm, perccli, mvcli, Ansible OpenManage"
  - name: architecture
    description: "Container-based tooling approach"
  - name: container-setup
    description: "Build and run Dell tools container"
  - name: initial-config
    description: "First-time iDRAC setup"
  - name: bios
    description: "BIOS configuration via SCP"
  - name: idrac
    description: "iDRAC management and config-as-code"
  - name: raid
    description: "RAID management with perccli and mvcli"
  - name: firmware
    description: "Firmware updates and rollback"
  - name: inventory
    description: "Hardware inventory and asset export"
  - name: openmanage
    description: "Ansible dellemc.openmanage fleet operations"
  - name: diagnose-hardware
    description: "Hardware failure diagnosis"
  - name: diagnose-connectivity
    description: "Network/iDRAC connectivity troubleshooting"
  - name: diagnose-storage
    description: "Storage troubleshooting"
  - name: known-issues
    description: "Version-specific bugs and workarounds"
  - name: compatibility
    description: "Compatibility matrices"
  - name: decision-guides
    description: "Decision aids for tools and strategies"
depends_on: []
requires:
  tools:
    - docker
    - docker-compose
    - git
```

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/registry/
git commit -m "test: add formula fixtures for registry repo"
```

---

### Task 2: Registry Repo Reader

Build the module that reads and searches formula YAML files from a local directory.

**Files:**
- Create: `src/agentic_stacks_cli/registry_repo.py`
- Create: `tests/test_registry_repo.py`

- [ ] **Step 1: Write tests for formula loading**

Create `tests/test_registry_repo.py`:

```python
import pathlib
import pytest
import yaml

from agentic_stacks_cli.registry_repo import (
    load_formula,
    list_formulas,
    search_formulas,
    write_formula,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


def test_load_formula():
    formula = load_formula(FIXTURES, "agentic-stacks", "openstack-kolla")
    assert formula["name"] == "openstack-kolla"
    assert formula["owner"] == "agentic-stacks"
    assert formula["repository"] == "https://github.com/agentic-stacks/openstack-kolla"
    assert len(formula["skills"]) > 0


def test_load_formula_not_found():
    with pytest.raises(FileNotFoundError):
        load_formula(FIXTURES, "agentic-stacks", "nonexistent")


def test_list_formulas():
    formulas = list_formulas(FIXTURES)
    names = [f["name"] for f in formulas]
    assert "openstack-kolla" in names
    assert "kubernetes-talos" in names
    assert "dell-hardware" in names


def test_list_formulas_empty(tmp_path):
    formulas = list_formulas(tmp_path)
    assert formulas == []


def test_search_by_name():
    results = search_formulas(FIXTURES, "openstack")
    assert any(f["name"] == "openstack-kolla" for f in results)


def test_search_by_description():
    results = search_formulas(FIXTURES, "kubernetes")
    assert any(f["name"] == "kubernetes-talos" for f in results)


def test_search_by_target():
    results = search_formulas(FIXTURES, "talos-linux")
    assert any(f["name"] == "kubernetes-talos" for f in results)


def test_search_by_skill():
    results = search_formulas(FIXTURES, "RAID")
    assert any(f["name"] == "dell-hardware" for f in results)


def test_search_no_match():
    results = search_formulas(FIXTURES, "zzz-nonexistent-zzz")
    assert results == []


def test_search_case_insensitive():
    results = search_formulas(FIXTURES, "OPENSTACK")
    assert any(f["name"] == "openstack-kolla" for f in results)


def test_write_formula(tmp_path):
    formula = {
        "name": "test-stack",
        "owner": "test-org",
        "version": "1.0.0",
        "repository": "https://github.com/test-org/test-stack",
        "tag": "v1.0.0",
        "sha256": "",
        "description": "A test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "description": "Deploy it"}],
        "depends_on": [],
        "requires": {"tools": ["test-tool"]},
    }
    write_formula(tmp_path, formula)
    written = tmp_path / "stacks" / "test-org" / "test-stack.yaml"
    assert written.exists()
    loaded = yaml.safe_load(written.read_text())
    assert loaded["name"] == "test-stack"
    assert loaded["owner"] == "test-org"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_registry_repo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agentic_stacks_cli.registry_repo'`

- [ ] **Step 3: Implement registry_repo.py**

Create `src/agentic_stacks_cli/registry_repo.py`:

```python
"""Local registry repo — read, search, and write formula YAML files."""

import pathlib
from typing import Any

import yaml


Formula = dict[str, Any]

STACKS_DIR = "stacks"


def load_formula(registry_path: pathlib.Path, owner: str, name: str) -> Formula:
    """Load a single formula by owner/name."""
    formula_path = registry_path / STACKS_DIR / owner / f"{name}.yaml"
    if not formula_path.exists():
        raise FileNotFoundError(f"Formula not found: {owner}/{name}")
    with open(formula_path) as f:
        return yaml.safe_load(f)


def list_formulas(registry_path: pathlib.Path) -> list[Formula]:
    """List all formulas in the registry."""
    stacks_dir = registry_path / STACKS_DIR
    if not stacks_dir.exists():
        return []
    formulas = []
    for owner_dir in sorted(stacks_dir.iterdir()):
        if not owner_dir.is_dir():
            continue
        for formula_file in sorted(owner_dir.glob("*.yaml")):
            with open(formula_file) as f:
                formulas.append(yaml.safe_load(f))
    return formulas


def search_formulas(registry_path: pathlib.Path, query: str) -> list[Formula]:
    """Search formulas by name, description, target software, or skill names."""
    query_lower = query.lower()
    results = []
    for formula in list_formulas(registry_path):
        searchable = " ".join([
            formula.get("name", ""),
            formula.get("description", ""),
            formula.get("owner", ""),
            formula.get("target", {}).get("software", ""),
            " ".join(s.get("name", "") + " " + s.get("description", "")
                     for s in formula.get("skills", [])),
        ]).lower()
        if query_lower in searchable:
            results.append(formula)
    return results


def write_formula(registry_path: pathlib.Path, formula: Formula) -> pathlib.Path:
    """Write a formula YAML file to the registry directory."""
    owner = formula["owner"]
    name = formula["name"]
    owner_dir = registry_path / STACKS_DIR / owner
    owner_dir.mkdir(parents=True, exist_ok=True)
    formula_path = owner_dir / f"{name}.yaml"
    with open(formula_path, "w") as f:
        yaml.dump(formula, f, default_flow_style=False, sort_keys=False)
    return formula_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_registry_repo.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/registry_repo.py tests/test_registry_repo.py
git commit -m "feat: add registry repo reader for formula YAML files"
```

---

### Task 3: Registry Cache (Clone/Update)

Add functions to clone and update the registry repo locally, and wire into config.

**Files:**
- Modify: `src/agentic_stacks_cli/config.py`
- Modify: `src/agentic_stacks_cli/registry_repo.py`
- Create: `tests/test_registry_cache.py`

- [ ] **Step 1: Write tests for cache management**

Create `tests/test_registry_cache.py`:

```python
import pathlib
import subprocess
from unittest.mock import patch, call

from agentic_stacks_cli.registry_repo import ensure_registry, registry_cache_path


def test_registry_cache_path():
    path = registry_cache_path()
    assert str(path).endswith("agentic-stacks/registry")


def test_registry_cache_path_custom():
    path = registry_cache_path(config_dir=pathlib.Path("/tmp/test"))
    assert path == pathlib.Path("/tmp/test/registry")


@patch("agentic_stacks_cli.registry_repo.subprocess.run")
def test_ensure_registry_clones_when_missing(mock_run, tmp_path):
    cache_dir = tmp_path / "registry"
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    ensure_registry(
        repo_url="https://github.com/agentic-stacks/registry",
        cache_dir=cache_dir,
    )

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "clone"
    assert "https://github.com/agentic-stacks/registry" in args


@patch("agentic_stacks_cli.registry_repo.subprocess.run")
def test_ensure_registry_updates_when_exists(mock_run, tmp_path):
    cache_dir = tmp_path / "registry"
    cache_dir.mkdir()
    (cache_dir / ".git").mkdir()
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    ensure_registry(
        repo_url="https://github.com/agentic-stacks/registry",
        cache_dir=cache_dir,
    )

    # Should fetch + reset, not clone
    assert mock_run.call_count == 2
    first_args = mock_run.call_args_list[0][0][0]
    assert "fetch" in first_args
    second_args = mock_run.call_args_list[1][0][0]
    assert "reset" in second_args
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_registry_cache.py -v`
Expected: FAIL — `ImportError: cannot import name 'ensure_registry'`

- [ ] **Step 3: Update config defaults**

In `src/agentic_stacks_cli/config.py`, update `CONFIG_DEFAULTS`:

```python
CONFIG_DEFAULTS = {
    "registry_repo": "https://github.com/agentic-stacks/registry",
    "default_namespace": "agentic-stacks",
    "api_url": "https://agentic-stacks.ajmesserli.workers.dev/api/v1",
    "token": None,
}
```

(Replace `"registry": "ghcr.io"` with `"registry_repo"`)

- [ ] **Step 4: Add ensure_registry and registry_cache_path to registry_repo.py**

Add to the top of `src/agentic_stacks_cli/registry_repo.py`, after existing imports:

```python
import subprocess

DEFAULT_REGISTRY_REPO = "https://github.com/agentic-stacks/registry"
DEFAULT_CONFIG_DIR = pathlib.Path.home() / ".config" / "agentic-stacks"


def registry_cache_path(config_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Return the path to the local registry cache."""
    base = config_dir if config_dir else DEFAULT_CONFIG_DIR
    return base / "registry"


def ensure_registry(
    repo_url: str = DEFAULT_REGISTRY_REPO,
    cache_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    """Clone or update the local registry cache. Returns the cache path."""
    if cache_dir is None:
        cache_dir = registry_cache_path()

    if (cache_dir / ".git").is_dir():
        subprocess.run(
            ["git", "-C", str(cache_dir), "fetch", "--quiet"],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(cache_dir), "reset", "--hard", "origin/main", "--quiet"],
            capture_output=True, text=True,
        )
    else:
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", repo_url, str(cache_dir)],
            capture_output=True, text=True,
        )

    return cache_dir
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_registry_cache.py tests/test_registry_repo.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/registry_repo.py src/agentic_stacks_cli/config.py tests/test_registry_cache.py
git commit -m "feat: add registry cache clone/update and config defaults"
```

---

### Task 4: Rewrite Search to Use Local Formulas

Replace the API-based search with local formula search.

**Files:**
- Rewrite: `src/agentic_stacks_cli/commands/search.py`
- Rewrite: `tests/test_cli_search.py`

- [ ] **Step 1: Write new search tests**

Rewrite `tests/test_cli_search.py`:

```python
import pathlib
from unittest.mock import patch
from click.testing import CliRunner
import yaml

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_name(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "openstack", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "openstack-kolla" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_target(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "talos-linux", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "kubernetes-talos" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_skill(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "RAID", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "dell-hardware" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_no_results(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "zzz-nonexistent", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "No stacks found" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_shows_description(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "dell", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "Dell PowerEdge" in result.output or "dell-hardware" in result.output


def test_search_no_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_cli_search.py -v`
Expected: FAIL — `ImportError: cannot import name 'ensure_registry' from 'agentic_stacks_cli.commands.search'`

- [ ] **Step 3: Rewrite search command**

Replace `src/agentic_stacks_cli/commands/search.py`:

```python
"""agentic-stacks search — find stacks in the registry."""

import pathlib

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import ensure_registry, search_formulas


@click.command()
@click.argument("query")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def search(query: str, config_path: str | None):
    """Search for stacks in the registry."""
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    repo_url = cfg.get("registry_repo", "https://github.com/agentic-stacks/registry")

    try:
        registry_path = ensure_registry(repo_url=repo_url)
    except Exception as e:
        raise click.ClickException(f"Could not update registry: {e}")

    results = search_formulas(registry_path, query)

    if not results:
        click.echo(f"No stacks found for '{query}'.")
        return

    click.echo(f"Found {len(results)} stack(s):\n")
    for formula in results:
        owner = formula.get("owner", "")
        name = formula.get("name", "")
        version = formula.get("version", "")
        desc = formula.get("description", "").strip()
        click.echo(f"  {owner}/{name}@{version}")
        if desc:
            click.echo(f"    {desc}")
        click.echo()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_cli_search.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/search.py tests/test_cli_search.py
git commit -m "feat: rewrite search to use local registry formulas"
```

---

### Task 5: Update Pull to Resolve via Formulas

When pulling a stack by reference (not from lock), look up the formula to get the repository URL instead of constructing it from convention.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/pull.py`
- Modify: `tests/test_cli_pull.py`

- [ ] **Step 1: Add formula-resolution test**

Add to `tests/test_cli_pull.py`:

```python
import pathlib

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_resolves_from_formula(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "openstack-kolla",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/openstack-kolla",
        tmp_path / ".stacks" / "openstack-kolla",
    )


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_formula_not_found_falls_back(mock_clone, mock_ensure, tmp_path):
    """When formula doesn't exist, fall back to GitHub URL convention."""
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "someuser/unknown-stack",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/someuser/unknown-stack",
        tmp_path / ".stacks" / "unknown-stack",
    )
```

Also update the existing `test_pull_by_name` and `test_pull_by_namespace_name` tests to mock `ensure_registry`:

```python
@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_name(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "openstack-kolla",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/openstack-kolla",
        tmp_path / ".stacks" / "openstack-kolla",
    )


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_owner_name(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "agentic-stacks/dell-hardware",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/dell-hardware",
        tmp_path / ".stacks" / "dell-hardware",
    )
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `.venv/bin/pytest tests/test_cli_pull.py -v`
Expected: New tests FAIL — `ensure_registry` not imported in pull

- [ ] **Step 3: Update pull command to resolve via formulas**

In `src/agentic_stacks_cli/commands/pull.py`, add import and modify the pull function:

Add to imports:

```python
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import ensure_registry, load_formula
```

Replace the block after `namespace, name = _parse_ref(reference)` (around line 71) that constructs `repo_url`:

```python
    namespace, name = _parse_ref(reference)

    # Try to resolve from registry formula
    repo_url = None
    try:
        registry_path = ensure_registry(
            repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
        )
        formula = load_formula(registry_path, namespace, name)
        repo_url = formula["repository"]
    except (FileNotFoundError, Exception):
        pass

    # Fall back to GitHub URL convention
    if not repo_url:
        repo_url = f"{GITHUB_BASE}/{namespace}/{name}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_cli_pull.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/pull.py tests/test_cli_pull.py
git commit -m "feat: resolve stacks from registry formulas in pull"
```

---

### Task 6: Sync Script for GitHub Action

Create the Python script that scans the `agentic-stacks` org and generates formula YAML files. This will live in the registry repo but we build and test it here first.

**Files:**
- Create: `scripts/sync_formulas.py`
- Create: `tests/test_sync_formulas.py`

- [ ] **Step 1: Write tests for formula generation from manifest**

Create `tests/test_sync_formulas.py`:

```python
import pathlib
import yaml
import pytest

# Import the script's functions directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sync_formulas",
    pathlib.Path(__file__).parent.parent / "scripts" / "sync_formulas.py",
)
sync = importlib.util.module_from_spec(spec)


def _load_sync():
    spec.loader.exec_module(sync)
    return sync


def test_manifest_to_formula():
    mod = _load_sync()
    manifest = {
        "name": "test-stack",
        "owner": "test-org",
        "version": "0.1.0",
        "description": "A test stack",
        "repository": "https://github.com/test-org/test-stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy", "description": "Deploy it"},
            {"name": "diagnose", "entry": "skills/diagnose", "description": "Fix it"},
        ],
        "depends_on": [],
        "requires": {"tools": [{"name": "test-tool", "description": "A tool"}], "python": ">=3.11"},
    }
    formula = mod.manifest_to_formula(manifest)
    assert formula["name"] == "test-stack"
    assert formula["owner"] == "test-org"
    assert formula["repository"] == "https://github.com/test-org/test-stack"
    assert formula["tag"] == "v0.1.0"
    assert formula["sha256"] == ""
    # Skills should not include 'entry' field
    assert "entry" not in formula["skills"][0]
    assert formula["skills"][0]["name"] == "deploy"
    # Tools should be flattened to names
    assert formula["requires"]["tools"] == ["test-tool"]


def test_manifest_to_formula_namespace_fallback():
    """Supports old manifests with 'namespace' instead of 'owner'."""
    mod = _load_sync()
    manifest = {
        "name": "old-stack",
        "namespace": "old-org",
        "version": "1.0.0",
        "description": "Old style",
        "repository": "https://github.com/old-org/old-stack",
        "target": {"software": "test", "versions": []},
        "skills": [],
        "depends_on": [],
        "requires": {},
    }
    formula = mod.manifest_to_formula(manifest)
    assert formula["owner"] == "old-org"


def test_write_formulas_to_directory(tmp_path):
    mod = _load_sync()
    formulas = [
        {
            "name": "stack-a",
            "owner": "org-a",
            "version": "1.0.0",
            "repository": "https://github.com/org-a/stack-a",
            "tag": "v1.0.0",
            "sha256": "",
            "description": "Stack A",
            "target": {},
            "skills": [],
            "depends_on": [],
            "requires": {},
        },
    ]
    mod.write_formulas(tmp_path, formulas)
    written = tmp_path / "stacks" / "org-a" / "stack-a.yaml"
    assert written.exists()
    loaded = yaml.safe_load(written.read_text())
    assert loaded["name"] == "stack-a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_sync_formulas.py -v`
Expected: FAIL — script doesn't exist yet

- [ ] **Step 3: Create the sync script**

Create `scripts/sync_formulas.py`:

```python
#!/usr/bin/env python3
"""Sync formula YAML files from stack repos in the agentic-stacks org.

Usage:
    python sync_formulas.py --org agentic-stacks --output ./stacks
    python sync_formulas.py --org agentic-stacks --output ./stacks --token ghp_...

Requires: PyYAML, and either `gh` CLI (authenticated) or a --token arg.
"""

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any
from base64 import b64decode

import yaml


def manifest_to_formula(manifest: dict[str, Any]) -> dict[str, Any]:
    """Convert a stack.yaml manifest into a registry formula."""
    owner = manifest.get("owner") or manifest.get("namespace", "")
    name = manifest["name"]
    version = manifest.get("version", "0.0.0")

    # Strip 'entry' from skills — formulas only need name + description
    skills = []
    for skill in manifest.get("skills", []):
        skills.append({
            "name": skill["name"],
            "description": skill.get("description", ""),
        })

    # Flatten tools to just names if they're dicts
    requires = dict(manifest.get("requires", {}))
    if "tools" in requires:
        tools = requires["tools"]
        if tools and isinstance(tools[0], dict):
            requires["tools"] = [t["name"] for t in tools]

    return {
        "name": name,
        "owner": owner,
        "version": str(version),
        "repository": manifest.get("repository", ""),
        "tag": f"v{version}",
        "sha256": "",
        "description": manifest.get("description", "").strip(),
        "target": manifest.get("target", {}),
        "skills": skills,
        "depends_on": manifest.get("depends_on", []),
        "requires": requires,
    }


def write_formulas(output_dir: pathlib.Path, formulas: list[dict]) -> None:
    """Write formula YAML files to output_dir/stacks/<owner>/<name>.yaml."""
    for formula in formulas:
        owner = formula["owner"]
        name = formula["name"]
        owner_dir = output_dir / "stacks" / owner
        owner_dir.mkdir(parents=True, exist_ok=True)
        formula_path = owner_dir / f"{name}.yaml"
        with open(formula_path, "w") as f:
            yaml.dump(formula, f, default_flow_style=False, sort_keys=False)


def fetch_repos(org: str, token: str | None = None) -> list[str]:
    """List all repos in a GitHub org."""
    cmd = ["gh", "api", f"orgs/{org}/repos", "--paginate", "--jq", ".[].name"]
    if token:
        cmd.extend(["--header", f"Authorization: token {token}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error listing repos: {result.stderr}", file=sys.stderr)
        return []
    return [name.strip() for name in result.stdout.strip().split("\n") if name.strip()]


def fetch_manifest(org: str, repo: str, token: str | None = None) -> dict | None:
    """Fetch stack.yaml from a repo. Returns None if not found."""
    cmd = ["gh", "api", f"repos/{org}/{repo}/contents/stack.yaml", "--jq", ".content"]
    if token:
        cmd.extend(["--header", f"Authorization: token {token}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        content = b64decode(result.stdout.strip()).decode("utf-8")
        return yaml.safe_load(content)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Sync registry formulas from GitHub org")
    parser.add_argument("--org", default="agentic-stacks", help="GitHub org to scan")
    parser.add_argument("--output", default=".", help="Output directory (registry repo root)")
    parser.add_argument("--token", default=None, help="GitHub token (optional, uses gh auth)")
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output)
    print(f"Scanning {args.org}...")

    repos = fetch_repos(args.org, args.token)
    print(f"Found {len(repos)} repos")

    formulas = []
    for repo in repos:
        manifest = fetch_manifest(args.org, repo, args.token)
        if manifest:
            formula = manifest_to_formula(manifest)
            formulas.append(formula)
            print(f"  {formula['owner']}/{formula['name']}@{formula['version']}")
        else:
            print(f"  {repo} — no stack.yaml, skipping")

    write_formulas(output_dir, formulas)
    print(f"\nWrote {len(formulas)} formula(s)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_sync_formulas.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_formulas.py tests/test_sync_formulas.py
git commit -m "feat: add sync script to generate formulas from org repos"
```

---

### Task 7: GitHub Action Workflow

Create the workflow file that will live in the registry repo. We build it here, then copy it when creating the registry repo.

**Files:**
- Create: `scripts/registry-repo/sync.yml`
- Create: `scripts/registry-repo/README.md`

- [ ] **Step 1: Create the GitHub Action workflow**

Create `scripts/registry-repo/.github/workflows/sync.yml`:

```yaml
name: Sync Formulas

on:
  schedule:
    - cron: '0 * * * *'  # hourly
  workflow_dispatch:

permissions:
  contents: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install pyyaml

      - name: Sync formulas
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/sync_formulas.py --org agentic-stacks --output .

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add stacks/
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "chore: sync formulas from org repos"
            git push
          fi
```

- [ ] **Step 2: Create registry repo README template**

Create `scripts/registry-repo/README.md`:

```markdown
# Agentic Stacks Registry

Formula index for [agentic stacks](https://github.com/agentic-stacks/agentic-stacks). Each formula points to a stack's source repo with metadata for discovery and installation.

## Structure

```
stacks/
└── <owner>/
    └── <stack-name>.yaml
```

## How It Works

The CLI caches this repo locally and reads formulas for `search` and `pull` operations:

```bash
agentic-stacks search openstack     # searches local formulas
agentic-stacks pull openstack-kolla # resolves repo URL from formula
```

## Auto-Sync

A GitHub Action runs hourly to scan repos in the `agentic-stacks` org for `stack.yaml` files and update formulas automatically.

## Adding a Third-Party Stack

Open a PR adding your formula to `stacks/<your-org>/<stack-name>.yaml`, or run:

```bash
cd your-stack/
agentic-stacks publish
```
```

- [ ] **Step 3: Commit**

```bash
git add scripts/registry-repo/
git commit -m "chore: add registry repo template (workflow + README)"
```

---

### Task 8: Create the Registry Repo on GitHub

Use the templates and sync script to create and populate the actual `agentic-stacks/registry` repo.

**Files:**
- External: `github.com/agentic-stacks/registry`

- [ ] **Step 1: Create the repo**

```bash
gh repo create agentic-stacks/registry --public --description "Formula index for agentic stacks"
```

- [ ] **Step 2: Clone and populate**

```bash
cd /tmp
git clone https://github.com/agentic-stacks/registry
cd registry
```

- [ ] **Step 3: Copy templates**

Copy `scripts/registry-repo/README.md` to the registry repo root.
Copy `scripts/registry-repo/.github/workflows/sync.yml` to `.github/workflows/sync.yml`.
Copy `scripts/sync_formulas.py` to `scripts/sync_formulas.py`.

- [ ] **Step 4: Run the sync script to populate initial formulas**

```bash
pip install pyyaml
python scripts/sync_formulas.py --org agentic-stacks --output .
```

Expected: Writes formulas for openstack-kolla, kubernetes-talos, dell-hardware to `stacks/agentic-stacks/`.

- [ ] **Step 5: Commit and push**

```bash
git add .
git commit -m "feat: initial registry with formulas for 3 stacks"
git push
```

- [ ] **Step 6: Verify the Action runs**

```bash
gh workflow run sync.yml --repo agentic-stacks/registry
gh run list --repo agentic-stacks/registry --limit 1
```

---

### Task 9: Integration Test — Full Flow

Verify the end-to-end flow works: search finds stacks from the registry, pull resolves from formulas.

**Files:**
- No new files — run existing tests + manual verification

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/pytest tests/ -v --tb=short
```

Expected: All tests pass (except pre-existing SOCKS proxy failures in test_api_client.py).

- [ ] **Step 2: Manual smoke test — search**

```bash
agentic-stacks search openstack
agentic-stacks search kubernetes
agentic-stacks search dell
agentic-stacks search RAID
```

Expected: Each returns the matching stack from the registry repo.

- [ ] **Step 3: Manual smoke test — pull**

```bash
mkdir /tmp/test-project && cd /tmp/test-project
agentic-stacks init agentic-stacks/openstack-kolla .
agentic-stacks pull
agentic-stacks pull dell-hardware
agentic-stacks list
```

Expected: Both stacks pulled, list shows 2 stacks.

- [ ] **Step 4: Final commit — spec and plan docs**

```bash
git add docs/superpowers/specs/2026-03-29-git-backed-registry-design.md
git add docs/superpowers/plans/2026-03-29-git-backed-registry.md
git commit -m "docs: add git-backed registry design spec and implementation plan"
```
