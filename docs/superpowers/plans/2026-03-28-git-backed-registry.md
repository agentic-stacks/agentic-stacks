# Git-Backed Registry (Homebrew-Style) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace OCI/ORAS distribution with a git-backed registry repo (like Homebrew taps). A central repo holds formula YAML files pointing to stack source repos. `pull` downloads from GitHub archives. `publish` adds a formula to the registry repo. `search` reads formulas from the registry repo.

**Architecture:** The registry repo (`github.com/agentic-stacks/registry`) contains one YAML formula per stack. Each formula has the stack's metadata + a `repository` URL + git tag. The CLI clones/fetches the registry repo locally (cached at `~/.config/agentic-stacks/registry/`), searches formulas locally, and downloads stack archives from GitHub. The D1 database and API stay for the website but become a read cache synced from the registry repo (separate plan). This plan focuses on the CLI side.

**Tech Stack:** Python, PyYAML, Click, httpx, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/agentic_stacks_cli/registry_repo.py` | Create | Clone/update registry repo, read/search/write formulas |
| `src/agentic_stacks_cli/github.py` | Create | Download GitHub archive (tarball) for a repo at a tag |
| `src/agentic_stacks_cli/commands/pull.py` | Rewrite | Pull from GitHub archive instead of ORAS |
| `src/agentic_stacks_cli/commands/publish.py` | Rewrite | Write formula + open PR instead of OCI push |
| `src/agentic_stacks_cli/commands/search.py` | Rewrite | Search local registry repo instead of API |
| `src/agentic_stacks_cli/config.py` | Modify | Update defaults (registry_repo URL replaces OCI registry) |
| `src/agentic_stacks/manifest.py` | Modify | Add `repository` field to manifest parsing |
| `tests/test_registry_repo.py` | Create | Tests for formula read/write/search |
| `tests/test_github_download.py` | Create | Tests for archive download |
| `tests/test_cli_pull.py` | Rewrite | Tests for new pull flow |
| `tests/test_cli_publish.py` | Rewrite | Tests for new publish flow |
| `tests/test_cli_search.py` | Rewrite | Tests for new search flow |
| `tests/test_config.py` | Modify | Update expected config defaults |
| `tests/fixtures/registry/` | Create | Fixture: a mock registry repo with formula files |

---

### Task 1: Formula Format and Registry Repo Reader

Create the registry repo module that reads formula YAML files from a local directory (the cloned registry repo).

**Files:**
- Create: `src/agentic_stacks_cli/registry_repo.py`
- Create: `tests/fixtures/registry/stacks/openstack-kolla.yaml`
- Create: `tests/fixtures/registry/stacks/kubernetes-talos.yaml`
- Create: `tests/fixtures/registry/stacks/base.yaml`
- Create: `tests/test_registry_repo.py`

- [ ] **Step 1: Create formula fixtures**

Create `tests/fixtures/registry/stacks/openstack-kolla.yaml`:

```yaml
name: openstack-kolla
namespace: agentic-stacks
version: "1.3.0"
repository: https://github.com/agentic-stacks/openstack-kolla
tag: v1.3.0
sha256: ""
description: "Agent-driven OpenStack deployment on kolla-ansible"
target:
  software: openstack
  versions: ["2024.2", "2025.1"]
skills:
  - name: deploy
    description: "Runs kolla-ansible deploy lifecycle"
  - name: health-check
    description: "Validates environment health"
  - name: config-build
    description: "Compiles environment.yml into kolla-ansible globals"
  - name: diagnose
    description: "Root cause analysis from symptoms"
project:
  environments: true
  per_environment:
    - config.yml
    - inventory/
    - files/
    - secrets/
depends_on:
  - name: base
    namespace: agentic-stacks
    version: "^1.0"
requires:
  tools: [kolla-ansible, openstack-cli]
  python: ">=3.11"
```

Create `tests/fixtures/registry/stacks/kubernetes-talos.yaml`:

```yaml
name: kubernetes-talos
namespace: agentic-stacks
version: "2.1.0"
repository: https://github.com/agentic-stacks/kubernetes-talos
tag: v2.1.0
sha256: ""
description: "Agent-driven Kubernetes on Talos Linux"
target:
  software: kubernetes
  versions: ["1.31", "1.32"]
skills:
  - name: bootstrap
    description: "Bootstrap a Talos Linux Kubernetes cluster"
  - name: upgrade
    description: "Rolling upgrade of Talos nodes and Kubernetes version"
  - name: health-check
    description: "Cluster health check"
project:
  environments: true
  per_environment:
    - config.yml
    - machines/
depends_on: []
requires:
  tools: [talosctl, kubectl, helm]
  python: ">=3.11"
```

Create `tests/fixtures/registry/stacks/base.yaml`:

```yaml
name: base
namespace: agentic-stacks
version: "1.0.2"
repository: https://github.com/agentic-stacks/base
tag: v1.0.2
sha256: ""
description: "Shared foundation stack"
target:
  software: ""
  versions: []
skills:
  - name: profile-merge
    description: "Load and deep-merge YAML profiles"
  - name: approval-gates
    description: "Request approval before executing actions"
project: {}
depends_on: []
requires:
  python: ">=3.11"
```

- [ ] **Step 2: Write failing tests**

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
    FormulaError,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


def test_load_formula():
    formula = load_formula(FIXTURES / "stacks" / "openstack-kolla.yaml")
    assert formula["name"] == "openstack-kolla"
    assert formula["namespace"] == "agentic-stacks"
    assert formula["version"] == "1.3.0"
    assert formula["repository"] == "https://github.com/agentic-stacks/openstack-kolla"
    assert formula["tag"] == "v1.3.0"
    assert len(formula["skills"]) == 4


def test_load_formula_not_found():
    with pytest.raises(FormulaError, match="not found"):
        load_formula(pathlib.Path("/nonexistent.yaml"))


def test_list_formulas():
    formulas = list_formulas(FIXTURES / "stacks")
    names = [f["name"] for f in formulas]
    assert "openstack-kolla" in names
    assert "kubernetes-talos" in names
    assert "base" in names


def test_search_formulas_by_name():
    results = search_formulas(FIXTURES / "stacks", "openstack")
    assert len(results) == 1
    assert results[0]["name"] == "openstack-kolla"


def test_search_formulas_by_description():
    results = search_formulas(FIXTURES / "stacks", "kubernetes")
    assert len(results) >= 1
    assert any(r["name"] == "kubernetes-talos" for r in results)


def test_search_formulas_no_match():
    results = search_formulas(FIXTURES / "stacks", "nonexistent-thing-xyz")
    assert results == []


def test_search_formulas_by_target():
    results = search_formulas(FIXTURES / "stacks", "openstack")
    assert results[0]["target"]["software"] == "openstack"


def test_write_formula(tmp_path):
    stacks_dir = tmp_path / "stacks"
    stacks_dir.mkdir()
    formula = {
        "name": "my-stack",
        "namespace": "myorg",
        "version": "1.0.0",
        "repository": "https://github.com/myorg/my-stack",
        "tag": "v1.0.0",
        "sha256": "",
        "description": "My stack",
        "target": {"software": "test", "versions": []},
        "skills": [{"name": "deploy", "description": "Deploy"}],
        "project": {},
        "depends_on": [],
        "requires": {"python": ">=3.11"},
    }
    write_formula(stacks_dir, formula)
    assert (stacks_dir / "my-stack.yaml").exists()
    loaded = yaml.safe_load((stacks_dir / "my-stack.yaml").read_text())
    assert loaded["name"] == "my-stack"
    assert loaded["repository"] == "https://github.com/myorg/my-stack"


def test_write_formula_overwrites(tmp_path):
    stacks_dir = tmp_path / "stacks"
    stacks_dir.mkdir()
    formula = {
        "name": "my-stack", "namespace": "myorg", "version": "1.0.0",
        "repository": "https://github.com/myorg/my-stack", "tag": "v1.0.0",
        "sha256": "", "description": "v1",
        "target": {}, "skills": [], "project": {},
        "depends_on": [], "requires": {},
    }
    write_formula(stacks_dir, formula)
    formula["version"] = "2.0.0"
    formula["description"] = "v2"
    write_formula(stacks_dir, formula)
    loaded = yaml.safe_load((stacks_dir / "my-stack.yaml").read_text())
    assert loaded["version"] == "2.0.0"
    assert loaded["description"] == "v2"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_registry_repo.py -v`
Expected: ImportError — `registry_repo` module doesn't exist

- [ ] **Step 4: Implement registry_repo.py**

Create `src/agentic_stacks_cli/registry_repo.py`:

```python
"""Registry repo — read, search, and write formula YAML files."""

import pathlib
from typing import Any

import yaml


class FormulaError(Exception):
    """Raised when a formula file is invalid or missing."""
    pass


def load_formula(path: pathlib.Path) -> dict:
    """Load a single formula YAML file."""
    path = pathlib.Path(path)
    if not path.exists():
        raise FormulaError(f"Formula not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise FormulaError(f"Formula must be a YAML mapping: {path}")
    return data


def list_formulas(stacks_dir: pathlib.Path) -> list[dict]:
    """List all formulas in a stacks directory."""
    stacks_dir = pathlib.Path(stacks_dir)
    if not stacks_dir.is_dir():
        return []
    formulas = []
    for path in sorted(stacks_dir.glob("*.yaml")):
        try:
            formulas.append(load_formula(path))
        except FormulaError:
            continue
    return formulas


def search_formulas(stacks_dir: pathlib.Path, query: str) -> list[dict]:
    """Search formulas by name, description, or target software."""
    query_lower = query.lower()
    results = []
    for formula in list_formulas(stacks_dir):
        name = formula.get("name", "").lower()
        desc = formula.get("description", "").lower()
        target_sw = formula.get("target", {}).get("software", "").lower()
        skills_text = " ".join(
            s.get("name", "") + " " + s.get("description", "")
            for s in formula.get("skills", [])
        ).lower()
        if (query_lower in name or query_lower in desc
                or query_lower in target_sw or query_lower in skills_text):
            results.append(formula)
    return results


def write_formula(stacks_dir: pathlib.Path, formula: dict) -> pathlib.Path:
    """Write a formula to the stacks directory."""
    stacks_dir = pathlib.Path(stacks_dir)
    stacks_dir.mkdir(parents=True, exist_ok=True)
    name = formula["name"]
    path = stacks_dir / f"{name}.yaml"
    with open(path, "w") as f:
        yaml.dump(formula, f, default_flow_style=False, sort_keys=False)
    return path
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_registry_repo.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/registry_repo.py tests/test_registry_repo.py \
  tests/fixtures/registry/
git commit -m "feat: add registry_repo module — formula read/write/search"
```

---

### Task 2: GitHub Archive Download

Create a module that downloads a GitHub repo archive at a specific tag and extracts it.

**Files:**
- Create: `src/agentic_stacks_cli/github.py`
- Create: `tests/test_github_download.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_github_download.py`:

```python
import pathlib
import tarfile
import io
import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_cli.github import download_stack, archive_url, DownloadError


def test_archive_url():
    url = archive_url("https://github.com/agentic-stacks/openstack-kolla", "v1.3.0")
    assert url == "https://github.com/agentic-stacks/openstack-kolla/archive/refs/tags/v1.3.0.tar.gz"


def test_archive_url_strips_trailing_slash():
    url = archive_url("https://github.com/agentic-stacks/openstack-kolla/", "v1.3.0")
    assert url == "https://github.com/agentic-stacks/openstack-kolla/archive/refs/tags/v1.3.0.tar.gz"


def _make_tarball(files: dict[str, str]) -> bytes:
    """Create a tar.gz in memory with given files. Keys are paths, values are content."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


@patch("agentic_stacks_cli.github.httpx.stream")
def test_download_stack_extracts_to_dir(mock_stream, tmp_path):
    tarball = _make_tarball({
        "openstack-kolla-1.3.0/stack.yaml": "name: openstack-kolla\n",
        "openstack-kolla-1.3.0/skills/deploy/README.md": "# Deploy\n",
    })

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_bytes.return_value = [tarball]
    mock_response.raise_for_status = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_stream.return_value = mock_response

    output = tmp_path / "output"
    download_stack("https://github.com/agentic-stacks/openstack-kolla", "v1.3.0", output)

    assert (output / "stack.yaml").exists()
    assert (output / "skills" / "deploy" / "README.md").exists()


@patch("agentic_stacks_cli.github.httpx.stream")
def test_download_stack_404_raises(mock_stream, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = Exception("404")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_stream.return_value = mock_response

    with pytest.raises(DownloadError, match="download"):
        download_stack("https://github.com/agentic-stacks/nonexistent", "v1.0.0",
                       tmp_path / "out")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_github_download.py -v`
Expected: ImportError — `github` module doesn't exist

- [ ] **Step 3: Implement github.py**

Create `src/agentic_stacks_cli/github.py`:

```python
"""Download stack archives from GitHub."""

import io
import pathlib
import tarfile

import httpx


class DownloadError(Exception):
    """Raised when a download fails."""
    pass


def archive_url(repository: str, tag: str) -> str:
    """Build the GitHub archive download URL for a tag."""
    repo = repository.rstrip("/")
    return f"{repo}/archive/refs/tags/{tag}.tar.gz"


def download_stack(repository: str, tag: str, output_dir: pathlib.Path) -> None:
    """Download and extract a stack from a GitHub repo at a specific tag.

    GitHub archives contain a top-level directory like 'repo-name-tag/'.
    We strip that prefix so files extract directly into output_dir.
    """
    url = archive_url(repository, tag)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            data = b"".join(response.iter_bytes())
    except Exception as e:
        raise DownloadError(f"Failed to download {url}: {e}")

    buf = io.BytesIO(data)
    try:
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            # Find the common prefix (GitHub adds 'repo-tag/' prefix)
            members = tar.getmembers()
            if not members:
                raise DownloadError(f"Empty archive from {url}")

            prefix = members[0].name.split("/")[0] + "/"

            for member in members:
                if not member.name.startswith(prefix):
                    continue
                # Strip the prefix
                member.name = member.name[len(prefix):]
                if not member.name:
                    continue
                tar.extract(member, output_dir, filter="data")
    except tarfile.TarError as e:
        raise DownloadError(f"Failed to extract archive: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_github_download.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/github.py tests/test_github_download.py
git commit -m "feat: add github module — download and extract stack archives from GitHub"
```

---

### Task 3: Rewrite `pull` to Use GitHub Archives

Replace the ORAS-based pull with GitHub archive download, reading from the local registry repo.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/pull.py`
- Rewrite: `tests/test_cli_pull.py`

- [ ] **Step 1: Write new tests**

Replace `tests/test_cli_pull.py`:

```python
import pathlib
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


@patch("agentic_stacks_cli.commands.pull.download_stack")
def test_pull_by_reference(mock_download, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "agentic-stacks/openstack-kolla@1.3.0",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_download.assert_called_once_with(
        "https://github.com/agentic-stacks/openstack-kolla",
        "v1.3.0",
        tmp_path / ".stacks" / "agentic-stacks" / "openstack-kolla" / "1.3.0",
    )


@patch("agentic_stacks_cli.commands.pull.download_stack")
def test_pull_creates_lock_entry(mock_download, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    runner = CliRunner()
    runner.invoke(cli, [
        "pull", "agentic-stacks/openstack-kolla@1.3.0",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    lock = yaml.safe_load((tmp_path / "stacks.lock").read_text())
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["version"] == "1.3.0"
    assert "github.com" in lock["stacks"][0]["repository"]


@patch("agentic_stacks_cli.commands.pull.download_stack")
def test_pull_latest_version(mock_download, tmp_path):
    """Pull without version gets latest from formula."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "agentic-stacks/openstack-kolla",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_download.assert_called_once()
    call_args = mock_download.call_args[0]
    assert call_args[1] == "v1.3.0"


def test_pull_not_found(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "agentic-stacks/nonexistent@1.0.0",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code != 0


def test_pull_invalid_reference(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "invalid-ref",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code != 0


@patch("agentic_stacks_cli.commands.pull.download_stack")
def test_pull_from_lock(mock_download, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "registry_repo": str(FIXTURES),
    }))
    lock = {
        "stacks": [{
            "name": "agentic-stacks/openstack-kolla",
            "version": "1.3.0",
            "repository": "https://github.com/agentic-stacks/openstack-kolla",
            "tag": "v1.3.0",
        }]
    }
    (tmp_path / "stacks.lock").write_text(yaml.dump(lock))

    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_download.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_pull.py -v`
Expected: Tests fail — pull still uses old ORAS flow

- [ ] **Step 3: Rewrite pull.py**

Replace `src/agentic_stacks_cli/commands/pull.py`:

```python
"""agentic-stacks pull — download a stack from the registry."""

import pathlib
import re

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.github import download_stack, DownloadError
from agentic_stacks_cli.registry_repo import load_formula, search_formulas, FormulaError
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock


def _parse_ref(ref: str) -> tuple[str, str, str | None]:
    match = re.match(r"^([^/]+)/([^@]+)(?:@(.+))?$", ref)
    if not match:
        raise ValueError(f"Invalid reference: '{ref}'. Expected format: namespace/name or namespace/name@version")
    return match.group(1), match.group(2), match.group(3)


def _find_formula(registry_path: pathlib.Path, namespace: str, name: str) -> dict:
    """Find a formula by name in the registry repo."""
    formula_path = registry_path / "stacks" / f"{name}.yaml"
    if formula_path.exists():
        formula = load_formula(formula_path)
        if formula.get("namespace") == namespace:
            return formula
    # Fallback: search all formulas
    for formula in search_formulas(registry_path / "stacks", name):
        if formula.get("namespace") == namespace and formula.get("name") == name:
            return formula
    raise FormulaError(f"Stack '{namespace}/{name}' not found in registry.")


@click.command()
@click.argument("reference", required=False)
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def pull(reference: str | None, target_dir: str, config_path: str | None):
    """Pull a stack from the registry."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    registry_path = pathlib.Path(cfg.get("registry_repo", ""))
    lock_path = target / "stacks.lock"

    if not reference:
        # Pull all stacks from lock file
        lock = read_lock(lock_path)
        if not lock["stacks"]:
            raise click.ClickException("No stacks.lock found or it's empty.")
        for entry in lock["stacks"]:
            ns, name = entry["name"].split("/", 1)
            version = entry["version"]
            repo_url = entry.get("repository", "")
            tag = entry.get("tag", f"v{version}")
            stacks_dir = target / ".stacks" / ns / name / version
            click.echo(f"Pulling {entry['name']}@{version}...")
            try:
                download_stack(repo_url, tag, stacks_dir)
                click.echo(f"  Extracted to {stacks_dir}")
            except DownloadError as e:
                click.echo(f"  Error: {e}")
        click.echo("All stacks restored from lock file.")
        return

    try:
        namespace, name, version = _parse_ref(reference)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Look up formula in registry
    try:
        formula = _find_formula(registry_path, namespace, name)
    except FormulaError as e:
        raise click.ClickException(str(e))

    if not version:
        version = formula["version"]

    repo_url = formula["repository"]
    tag = formula.get("tag", f"v{version}")

    stacks_dir = target / ".stacks" / namespace / name / version
    click.echo(f"Pulling {namespace}/{name}@{version}...")
    try:
        download_stack(repo_url, tag, stacks_dir)
    except DownloadError as e:
        raise click.ClickException(str(e))

    click.echo(f"  Extracted to {stacks_dir}")

    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=f"{namespace}/{name}", version=version,
                       digest="", registry=repo_url)
    # Add repository and tag to lock entry
    for entry in lock["stacks"]:
        if entry["name"] == f"{namespace}/{name}":
            entry["repository"] = repo_url
            entry["tag"] = tag
    write_lock(lock, lock_path)
    click.echo(f"  Updated stacks.lock")

    click.echo(f"\nPulled {namespace}/{name}@{version}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_pull.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/pull.py tests/test_cli_pull.py
git commit -m "feat: rewrite pull — download from GitHub archives via registry formulas"
```

---

### Task 4: Rewrite `search` to Use Local Registry Repo

Search reads formulas from the local registry repo directory instead of calling the API.

**Files:**
- Modify: `src/agentic_stacks_cli/commands/search.py`
- Rewrite: `tests/test_cli_search.py`

- [ ] **Step 1: Write new tests**

Replace `tests/test_cli_search.py`:

```python
import pathlib
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


def test_search_shows_results(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry_repo": str(FIXTURES)}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "openstack", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "openstack-kolla" in result.output
    assert "1.3.0" in result.output


def test_search_finds_by_description(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry_repo": str(FIXTURES)}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "kubernetes", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "kubernetes-talos" in result.output


def test_search_no_results(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry_repo": str(FIXTURES)}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "nonexistent-xyz", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "no stacks found" in result.output.lower()


def test_search_no_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_search.py -v`
Expected: Tests fail — search still uses API client

- [ ] **Step 3: Rewrite search.py**

Replace `src/agentic_stacks_cli/commands/search.py`:

```python
"""agentic-stacks search — find stacks in the registry."""

import pathlib

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import search_formulas


@click.command()
@click.argument("query")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def search(query: str, config_path: str | None):
    """Search for stacks in the registry."""
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    registry_path = pathlib.Path(cfg.get("registry_repo", ""))
    stacks_dir = registry_path / "stacks"

    if not stacks_dir.is_dir():
        raise click.ClickException(
            f"Registry not found at {registry_path}. "
            "Run 'agentic-stacks update' to fetch the registry."
        )

    results = search_formulas(stacks_dir, query)

    if not results:
        click.echo(f"No stacks found for '{query}'.")
        return

    click.echo(f"Found {len(results)} stack(s):\n")
    for stack in results:
        ns = stack.get("namespace", "")
        name = stack.get("name", "")
        version = stack.get("version", "")
        desc = stack.get("description", "")
        click.echo(f"  {ns}/{name}@{version}")
        if desc:
            click.echo(f"    {desc}")
        click.echo()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_search.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/commands/search.py tests/test_cli_search.py
git commit -m "feat: rewrite search — read from local registry repo formulas"
```

---

### Task 5: Rewrite `publish` to Write Formula

Publishing now writes a formula YAML file. For now it writes to the local registry repo clone. (Opening a GitHub PR is a future enhancement.)

**Files:**
- Modify: `src/agentic_stacks_cli/commands/publish.py`
- Rewrite: `tests/test_cli_publish.py`
- Modify: `src/agentic_stacks/manifest.py`

- [ ] **Step 1: Add `repository` field to manifest.py**

In `src/agentic_stacks/manifest.py`, after the existing `setdefault` calls, add:

```python
    manifest.setdefault("repository", "")
```

- [ ] **Step 2: Write new publish tests**

Replace `tests/test_cli_publish.py`:

```python
import json
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli


def _create_publishable_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "A test stack",
        "repository": "https://github.com/agentic-stacks/test-stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "project": {"environments": True, "per_environment": ["config.yml"]},
        "depends_on": [], "deprecations": [],
        "requires": {"tools": ["test-tool"], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir(); (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir(); (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object"}))


def test_publish_writes_formula(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    registry_dir = tmp_path / "registry"
    (registry_dir / "stacks").mkdir(parents=True)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "token": "ghp_test",
        "registry_repo": str(registry_dir),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "publish", "--path", str(tmp_path / "stack"), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    assert "published" in result.output.lower() or "formula" in result.output.lower()

    formula_path = registry_dir / "stacks" / "test-stack.yaml"
    assert formula_path.exists()
    formula = yaml.safe_load(formula_path.read_text())
    assert formula["name"] == "test-stack"
    assert formula["namespace"] == "agentic-stacks"
    assert formula["version"] == "1.0.0"
    assert formula["repository"] == "https://github.com/agentic-stacks/test-stack"
    assert formula["tag"] == "v1.0.0"
    assert len(formula["skills"]) == 1


def test_publish_no_token_fails(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry_repo": str(tmp_path)}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "publish", "--path", str(tmp_path / "stack"), "--config", str(config_path),
    ])
    assert result.exit_code != 0
    assert "login" in result.output.lower() or "token" in result.output.lower()


def test_publish_no_repository_fails(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    # Remove the repository field
    manifest = yaml.safe_load((tmp_path / "stack" / "stack.yaml").read_text())
    manifest.pop("repository")
    (tmp_path / "stack" / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))

    registry_dir = tmp_path / "registry"
    (registry_dir / "stacks").mkdir(parents=True)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "token": "ghp_test",
        "registry_repo": str(registry_dir),
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "publish", "--path", str(tmp_path / "stack"), "--config", str(config_path),
    ])
    assert result.exit_code != 0
    assert "repository" in result.output.lower()


def test_publish_invalid_stack_fails(tmp_path):
    (tmp_path / "stack").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test", "registry_repo": str(tmp_path)}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "publish", "--path", str(tmp_path / "stack"), "--config", str(config_path),
    ])
    assert result.exit_code != 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli_publish.py -v`
Expected: Tests fail — publish still uses OCI

- [ ] **Step 4: Rewrite publish.py**

Replace `src/agentic_stacks_cli/commands/publish.py`:

```python
"""agentic-stacks publish — register a stack in the registry."""

import pathlib

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import write_formula


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def publish(path: str, config_path: str | None):
    """Publish a stack to the registry."""
    stack_dir = pathlib.Path(path)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)

    token = cfg.get("token")
    if not token:
        raise click.ClickException("Not authenticated. Run 'agentic-stacks login' first.")

    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Invalid stack: {e}")

    name = manifest["name"]
    namespace = manifest["namespace"]
    version = manifest["version"]
    repository = manifest.get("repository", "")

    if not repository:
        raise click.ClickException(
            "stack.yaml must include a 'repository' field "
            "(e.g., https://github.com/your-org/your-stack)"
        )

    registry_path = pathlib.Path(cfg.get("registry_repo", ""))
    stacks_dir = registry_path / "stacks"

    if not stacks_dir.is_dir():
        raise click.ClickException(
            f"Registry repo not found at {registry_path}. "
            "Clone it first or set registry_repo in config."
        )

    formula = {
        "name": name,
        "namespace": namespace,
        "version": version,
        "repository": repository,
        "tag": f"v{version}",
        "sha256": "",
        "description": manifest.get("description", ""),
        "target": manifest.get("target", {}),
        "skills": manifest.get("skills", []),
        "project": manifest.get("project", {}),
        "depends_on": manifest.get("depends_on", []),
        "requires": manifest.get("requires", {}),
    }

    click.echo(f"Publishing {namespace}/{name}@{version}...")
    formula_path = write_formula(stacks_dir, formula)
    click.echo(f"  Formula written to {formula_path}")
    click.echo(f"\nPublished {namespace}/{name}@{version}")
    click.echo(f"  Commit and push the registry repo to make it available.")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_publish.py tests/test_manifest.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks/manifest.py src/agentic_stacks_cli/commands/publish.py \
  tests/test_cli_publish.py
git commit -m "feat: rewrite publish — write formula to local registry repo"
```

---

### Task 6: Update Config Defaults and Clean Up OCI

Update config to use `registry_repo` instead of OCI settings. Remove ORAS dependency from the core flow (keep `oci.py` for now but it's no longer imported by pull/publish).

**Files:**
- Modify: `src/agentic_stacks_cli/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write updated config test**

Replace the relevant assertion in `tests/test_config.py`:

```python
def test_default_config():
    cfg = default_config()
    assert cfg["registry_repo"] == "https://github.com/agentic-stacks/registry"
    assert cfg["default_namespace"] == "agentic-stacks"
    assert cfg["token"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_config.py::test_default_config -v`
Expected: Fails — `registry_repo` key doesn't exist

- [ ] **Step 3: Update config.py**

Replace `CONFIG_DEFAULTS` in `src/agentic_stacks_cli/config.py`:

```python
CONFIG_DEFAULTS = {
    "registry_repo": "https://github.com/agentic-stacks/registry",
    "default_namespace": "agentic-stacks",
    "api_url": "https://agentic-stacks.ajmesserli.workers.dev/api/v1",
    "token": None,
}
```

- [ ] **Step 4: Run all config tests**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/config.py tests/test_config.py
git commit -m "feat: update config defaults — registry_repo replaces OCI registry"
```

---

### Task 7: Full Test Suite + Manual Verification

Run complete test suite, manually test the new flow, update docs.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Manual test — search**

```bash
.venv/bin/agentic-stacks search openstack --config <(echo "registry_repo: tests/fixtures/registry")
```

Expected: Shows openstack-kolla@1.3.0

- [ ] **Step 3: Manual test — publish**

```bash
mkdir -p /tmp/test-registry/stacks
.venv/bin/agentic-stacks publish --path tests/fixtures/parent-stack \
  --config <(echo -e "token: fake\nregistry_repo: /tmp/test-registry")
cat /tmp/test-registry/stacks/openstack-kolla.yaml
rm -rf /tmp/test-registry
```

- [ ] **Step 4: Update CLAUDE.md**

Add to `CLAUDE.md` after the Operator Projects section:

```markdown
## Distribution Model

Homebrew-style git-backed registry. The registry repo (`github.com/agentic-stacks/registry`) contains one YAML formula per stack in `stacks/`. Each formula has metadata + a `repository` URL + git tag.

- `search` reads formulas from the local registry repo clone
- `pull` looks up the formula, downloads the GitHub archive at the tag
- `publish` writes a formula to the local registry repo clone (commit + push to share)

Config key `registry_repo` points to the local clone (or fixture path for testing). The D1 database and website API remain for web browse/search but the CLI is git-backed.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with git-backed distribution model"
```
