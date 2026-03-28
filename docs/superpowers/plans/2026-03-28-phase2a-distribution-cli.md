# Phase 2a: Distribution CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `publish`, `pull`, `search`, `upgrade`, and `login` commands to the `agentic-stacks` CLI, backed by OCI distribution (ORAS) and registry API calls.

**Architecture:** New CLI commands in `src/agentic_stacks_cli/commands/`. A shared config module handles CLI configuration (`~/.config/agentic-stacks/config.yaml`). An API client module talks to the registry. An OCI module wraps ORAS operations. A lock module handles `stacks.lock` reading/writing. Commands compose these building blocks.

**Tech Stack:** Python 3.11+, Click, httpx (API client), oras-py or subprocess oras CLI, PyYAML

---

## File Structure

```
src/agentic_stacks_cli/
├── __init__.py                    # (modify: register new commands)
├── config.py                      # CLI config loading/saving (~/.config/agentic-stacks/)
├── api_client.py                  # Registry API client (httpx)
├── oci.py                         # OCI packaging and push/pull (wraps oras CLI)
├── lock.py                        # stacks.lock reading/writing/resolution
├── commands/
│   ├── __init__.py
│   ├── init.py                    # (existing)
│   ├── doctor.py                  # (existing)
│   ├── validate.py                # (existing)
│   ├── login.py                   # agentic-stacks login
│   ├── publish.py                 # agentic-stacks publish
│   ├── pull.py                    # agentic-stacks pull
│   ├── search.py                  # agentic-stacks search
│   └── upgrade.py                 # agentic-stacks upgrade
tests/
├── test_config.py
├── test_api_client.py
├── test_oci.py
├── test_lock.py
├── test_cli_login.py
├── test_cli_publish.py
├── test_cli_pull.py
├── test_cli_search.py
└── test_cli_upgrade.py
```

---

### Task 1: CLI Config Module

**Files:**
- Create: `src/agentic_stacks_cli/config.py`
- Create: `tests/test_config.py`
- Modify: `pyproject.toml` (add httpx dependency)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import yaml
from agentic_stacks_cli.config import load_config, save_config, default_config, CONFIG_DEFAULTS


def test_default_config():
    cfg = default_config()
    assert cfg["registry"] == "ghcr.io"
    assert cfg["default_namespace"] == "agentic-stacks"
    assert cfg["api_url"] == "https://agentic-stacks.com/api/v1"
    assert cfg["token"] is None


def test_load_config_missing_file(tmp_path):
    cfg = load_config(tmp_path / "config.yaml")
    assert cfg["registry"] == "ghcr.io"
    assert cfg["token"] is None


def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    cfg = default_config()
    cfg["token"] = "ghp_test123"
    cfg["default_namespace"] = "myorg"
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded["token"] == "ghp_test123"
    assert loaded["default_namespace"] == "myorg"
    assert loaded["registry"] == "ghcr.io"


def test_load_config_merges_with_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "abc"}))
    loaded = load_config(config_path)
    assert loaded["token"] == "abc"
    assert loaded["registry"] == "ghcr.io"  # from defaults
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Add httpx to pyproject.toml dependencies**

Add `"httpx>=0.27"` to the dependencies list in `pyproject.toml`, then run: `pip install -e ".[dev]"`

- [ ] **Step 4: Implement config.py**

```python
# src/agentic_stacks_cli/config.py
"""CLI configuration loading and saving."""

import pathlib
from typing import Any

import yaml


CONFIG_DEFAULTS = {
    "registry": "ghcr.io",
    "default_namespace": "agentic-stacks",
    "api_url": "https://agentic-stacks.com/api/v1",
    "token": None,
}

DEFAULT_CONFIG_DIR = pathlib.Path.home() / ".config" / "agentic-stacks"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"


def default_config() -> dict[str, Any]:
    """Return a copy of the default configuration."""
    return dict(CONFIG_DEFAULTS)


def load_config(path: pathlib.Path | None = None) -> dict[str, Any]:
    """Load config from file, merged with defaults.

    Missing keys get default values. Missing file returns all defaults.
    """
    path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    cfg = default_config()
    if path.exists():
        with open(path) as f:
            user_cfg = yaml.safe_load(f)
        if isinstance(user_cfg, dict):
            cfg.update(user_cfg)
    return cfg


def save_config(config: dict[str, Any], path: pathlib.Path | None = None) -> None:
    """Save config to file."""
    path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/agentic_stacks_cli/config.py tests/test_config.py
git commit -m "feat: CLI config module with defaults and persistence"
```

---

### Task 2: Lock File Module

**Files:**
- Create: `src/agentic_stacks_cli/lock.py`
- Create: `tests/test_lock.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lock.py
import yaml
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock, remove_from_lock


def test_read_lock_missing_file(tmp_path):
    lock = read_lock(tmp_path / "stacks.lock")
    assert lock == {"stacks": []}


def test_write_and_read_lock(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    lock_data = {
        "stacks": [
            {
                "name": "agentic-stacks/openstack",
                "version": "1.3.0",
                "digest": "sha256:abc123",
                "registry": "ghcr.io/agentic-stacks/openstack",
            }
        ]
    }
    write_lock(lock_data, lock_path)
    loaded = read_lock(lock_path)
    assert len(loaded["stacks"]) == 1
    assert loaded["stacks"][0]["name"] == "agentic-stacks/openstack"
    assert loaded["stacks"][0]["digest"] == "sha256:abc123"


def test_add_to_lock(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name="agentic-stacks/openstack", version="1.3.0",
                       digest="sha256:abc", registry="ghcr.io/agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1

    lock = add_to_lock(lock, name="agentic-stacks/base", version="1.0.0",
                       digest="sha256:def", registry="ghcr.io/agentic-stacks/base")
    assert len(lock["stacks"]) == 2


def test_add_to_lock_updates_existing(tmp_path):
    lock = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:old", "registry": "ghcr.io/agentic-stacks/openstack"}
    ]}
    lock = add_to_lock(lock, name="agentic-stacks/openstack", version="1.4.0",
                       digest="sha256:new", registry="ghcr.io/agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["version"] == "1.4.0"
    assert lock["stacks"][0]["digest"] == "sha256:new"


def test_remove_from_lock():
    lock = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack"},
        {"name": "agentic-stacks/base", "version": "1.0.0",
         "digest": "sha256:def", "registry": "ghcr.io/agentic-stacks/base"},
    ]}
    lock = remove_from_lock(lock, name="agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/base"


def test_lock_file_format(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    lock = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack"}
    ]}
    write_lock(lock, lock_path)
    content = lock_path.read_text()
    assert "stacks:" in content
    assert "sha256:abc" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lock.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement lock.py**

```python
# src/agentic_stacks_cli/lock.py
"""stacks.lock reading, writing, and manipulation."""

import pathlib

import yaml


def read_lock(path: pathlib.Path) -> dict:
    """Read a stacks.lock file. Returns empty structure if missing."""
    path = pathlib.Path(path)
    if not path.exists():
        return {"stacks": []}
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "stacks" not in data:
        return {"stacks": []}
    return data


def write_lock(lock: dict, path: pathlib.Path) -> None:
    """Write a stacks.lock file."""
    path = pathlib.Path(path)
    with open(path, "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)


def add_to_lock(lock: dict, name: str, version: str, digest: str, registry: str) -> dict:
    """Add or update a stack entry in the lock. Returns updated lock."""
    stacks = lock.get("stacks", [])
    for i, entry in enumerate(stacks):
        if entry["name"] == name:
            stacks[i] = {"name": name, "version": version, "digest": digest, "registry": registry}
            return {"stacks": stacks}
    stacks.append({"name": name, "version": version, "digest": digest, "registry": registry})
    return {"stacks": stacks}


def remove_from_lock(lock: dict, name: str) -> dict:
    """Remove a stack entry from the lock. Returns updated lock."""
    stacks = [s for s in lock.get("stacks", []) if s["name"] != name]
    return {"stacks": stacks}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_lock.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/lock.py tests/test_lock.py
git commit -m "feat: stacks.lock read/write/manipulation"
```

---

### Task 3: OCI Module (ORAS wrapper)

**Files:**
- Create: `src/agentic_stacks_cli/oci.py`
- Create: `tests/test_oci.py`

- [ ] **Step 1: Write failing tests**

These tests mock subprocess calls since we can't hit a real OCI registry in unit tests.

```python
# tests/test_oci.py
import json
import tarfile
import subprocess
from unittest.mock import patch, MagicMock
from agentic_stacks_cli.oci import package_stack, push_stack, pull_stack, EXCLUDE_PATTERNS


def test_package_stack_creates_tarball(tmp_path):
    # Create a minimal stack directory
    stack_dir = tmp_path / "my-stack"
    stack_dir.mkdir()
    (stack_dir / "stack.yaml").write_text("name: test\n")
    (stack_dir / "skills").mkdir()
    (stack_dir / "skills" / "deploy.md").write_text("# Deploy\n")
    # Create excluded dirs
    (stack_dir / ".git").mkdir()
    (stack_dir / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (stack_dir / ".venv").mkdir()
    (stack_dir / "__pycache__").mkdir()

    output = tmp_path / "output"
    output.mkdir()
    tarball_path = package_stack(stack_dir, output)

    assert tarball_path.exists()
    assert tarball_path.suffix == ".gz"

    # Verify contents
    with tarfile.open(tarball_path, "r:gz") as tar:
        names = tar.getnames()
        assert "stack.yaml" in names
        assert "skills/deploy.md" in names
        # Excluded dirs should not be present
        assert not any(".git" in n for n in names)
        assert not any(".venv" in n for n in names)
        assert not any("__pycache__" in n for n in names)


def test_push_stack_calls_oras(tmp_path):
    tarball = tmp_path / "test-1.0.0.tar.gz"
    tarball.write_bytes(b"fake tarball")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Digest: sha256:abc123\n")
        ref, digest = push_stack(
            tarball_path=tarball,
            registry="ghcr.io",
            namespace="agentic-stacks",
            name="test",
            version="1.0.0",
            annotations={"dev.agentic-stacks.name": "test"},
        )

    assert ref == "ghcr.io/agentic-stacks/test:1.0.0"
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "oras" in cmd[0]
    assert "push" in cmd
    assert "ghcr.io/agentic-stacks/test:1.0.0" in cmd


def test_pull_stack_calls_oras(tmp_path):
    output_dir = tmp_path / "output"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Digest: sha256:def456\n")
        pull_stack(
            registry="ghcr.io",
            namespace="agentic-stacks",
            name="test",
            version="1.0.0",
            output_dir=output_dir,
        )

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "oras" in cmd[0]
    assert "pull" in cmd
    assert "ghcr.io/agentic-stacks/test:1.0.0" in cmd


def test_exclude_patterns():
    assert ".git" in EXCLUDE_PATTERNS
    assert ".venv" in EXCLUDE_PATTERNS
    assert "__pycache__" in EXCLUDE_PATTERNS
    assert "state" in EXCLUDE_PATTERNS
    assert ".superpowers" in EXCLUDE_PATTERNS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_oci.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement oci.py**

```python
# src/agentic_stacks_cli/oci.py
"""OCI packaging and push/pull via oras CLI."""

import pathlib
import subprocess
import tarfile

EXCLUDE_PATTERNS = {
    ".git", ".venv", "__pycache__", "state", ".superpowers",
    ".pytest_cache", "dist", "*.egg-info", ".coverage",
}

MEDIA_TYPE = "application/vnd.agentic-stacks.stack.v1+tar+gzip"


def _should_exclude(path: pathlib.Path) -> bool:
    """Check if a path should be excluded from packaging."""
    parts = path.parts
    for part in parts:
        if part in EXCLUDE_PATTERNS:
            return True
        if part.endswith(".egg-info"):
            return True
        if part.endswith(".pyc"):
            return True
    return False


def package_stack(stack_dir: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    """Package a stack directory into a tarball.

    Args:
        stack_dir: Path to the stack directory.
        output_dir: Where to write the tarball.

    Returns:
        Path to the created tarball.
    """
    stack_dir = pathlib.Path(stack_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tarball_name = f"{stack_dir.name}.tar.gz"
    tarball_path = output_dir / tarball_name

    with tarfile.open(tarball_path, "w:gz") as tar:
        for item in sorted(stack_dir.rglob("*")):
            rel = item.relative_to(stack_dir)
            if _should_exclude(rel):
                continue
            tar.add(item, arcname=str(rel))

    return tarball_path


def push_stack(
    tarball_path: pathlib.Path,
    registry: str,
    namespace: str,
    name: str,
    version: str,
    annotations: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Push a stack tarball to an OCI registry via oras.

    Args:
        tarball_path: Path to the tarball.
        registry: OCI registry hostname.
        namespace: Stack namespace.
        name: Stack name.
        version: Stack version.
        annotations: OCI annotations to attach.

    Returns:
        Tuple of (reference, digest).
    """
    ref = f"{registry}/{namespace}/{name}:{version}"

    cmd = ["oras", "push", ref, str(tarball_path), "--artifact-type", MEDIA_TYPE]

    if annotations:
        for key, value in annotations.items():
            cmd.extend(["--annotation", f"{key}={value}"])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise RuntimeError(f"oras push failed: {result.stderr}")

    digest = ""
    for line in result.stdout.splitlines():
        if line.startswith("Digest:"):
            digest = line.split(":", 1)[1].strip()
            break

    return ref, digest


def pull_stack(
    registry: str,
    namespace: str,
    name: str,
    version: str,
    output_dir: pathlib.Path,
) -> str:
    """Pull a stack from an OCI registry via oras.

    Args:
        registry: OCI registry hostname.
        namespace: Stack namespace.
        name: Stack name.
        version: Stack version.
        output_dir: Where to extract the stack.

    Returns:
        The digest of the pulled artifact.
    """
    ref = f"{registry}/{namespace}/{name}:{version}"
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["oras", "pull", ref, "--output", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise RuntimeError(f"oras pull failed: {result.stderr}")

    digest = ""
    for line in result.stdout.splitlines():
        if line.startswith("Digest:"):
            digest = line.split(":", 1)[1].strip()
            break

    return digest
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_oci.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/oci.py tests/test_oci.py
git commit -m "feat: OCI packaging and push/pull via oras"
```

---

### Task 4: API Client Module

**Files:**
- Create: `src/agentic_stacks_cli/api_client.py`
- Create: `tests/test_api_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api_client.py
import json
from unittest.mock import patch, MagicMock
from agentic_stacks_cli.api_client import RegistryClient


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_search_stacks():
    client = RegistryClient(api_url="https://example.com/api/v1")
    mock_data = {
        "stacks": [
            {"name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
             "description": "OpenStack deployment"}
        ]
    }
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)) as mock_get:
        results = client.search("openstack")
    assert len(results) == 1
    assert results[0]["name"] == "openstack"


def test_get_stack():
    client = RegistryClient(api_url="https://example.com/api/v1")
    mock_data = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "description": "OpenStack", "skills": [], "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
    }
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)):
        stack = client.get_stack("agentic-stacks", "openstack")
    assert stack["name"] == "openstack"
    assert stack["version"] == "1.3.0"


def test_get_stack_version():
    client = RegistryClient(api_url="https://example.com/api/v1")
    mock_data = {"name": "openstack", "namespace": "agentic-stacks", "version": "1.2.0"}
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)):
        stack = client.get_stack("agentic-stacks", "openstack", version="1.2.0")
    assert stack["version"] == "1.2.0"


def test_register_stack():
    client = RegistryClient(api_url="https://example.com/api/v1", token="ghp_test")
    mock_data = {"status": "registered"}
    with patch("httpx.Client.post", return_value=_mock_response(json_data=mock_data)):
        result = client.register_stack({
            "namespace": "agentic-stacks", "name": "openstack", "version": "1.3.0",
            "description": "test", "digest": "sha256:abc", "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
        })
    assert result["status"] == "registered"


def test_register_stack_no_token_raises():
    client = RegistryClient(api_url="https://example.com/api/v1")
    with patch("httpx.Client.post") as mock_post:
        try:
            client.register_stack({"name": "test"})
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "token" in str(e).lower() or "auth" in str(e).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_client.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement api_client.py**

```python
# src/agentic_stacks_cli/api_client.py
"""Registry API client."""

import httpx


class RegistryClient:
    """Client for the Agentic Stacks registry API."""

    def __init__(self, api_url: str, token: str | None = None):
        self._api_url = api_url.rstrip("/")
        self._token = token
        headers = {"User-Agent": "agentic-stacks-cli"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(headers=headers, timeout=30.0)

    def search(self, query: str) -> list[dict]:
        """Search for stacks by query string."""
        resp = self._client.get(f"{self._api_url}/stacks", params={"q": query})
        resp.raise_for_status()
        data = resp.json()
        return data.get("stacks", [])

    def get_stack(self, namespace: str, name: str, version: str | None = None) -> dict:
        """Get stack detail. If version is None, returns latest."""
        if version:
            url = f"{self._api_url}/stacks/{namespace}/{name}/{version}"
        else:
            url = f"{self._api_url}/stacks/{namespace}/{name}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    def register_stack(self, metadata: dict) -> dict:
        """Register or update a stack in the registry. Requires auth token."""
        if not self._token:
            raise RuntimeError("Authentication required. Run 'agentic-stacks login' first.")
        resp = self._client.post(f"{self._api_url}/stacks", json=metadata)
        resp.raise_for_status()
        return resp.json()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_api_client.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/agentic_stacks_cli/api_client.py tests/test_api_client.py
git commit -m "feat: registry API client"
```

---

### Task 5: `agentic-stacks login` Command

**Files:**
- Create: `src/agentic_stacks_cli/commands/login.py`
- Create: `tests/test_cli_login.py`
- Modify: `src/agentic_stacks_cli/__init__.py` (register command)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_login.py
import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def test_login_saves_token(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--token", "ghp_test123", "--config", str(config_path)])
    assert result.exit_code == 0
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["token"] == "ghp_test123"


def test_login_shows_success_message(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--token", "ghp_test", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "logged in" in result.output.lower() or "saved" in result.output.lower()


def test_login_no_token_prompts(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--config", str(config_path)], input="ghp_from_prompt\n")
    assert result.exit_code == 0
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["token"] == "ghp_from_prompt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_login.py -v`
Expected: FAIL

- [ ] **Step 3: Implement login command**

```python
# src/agentic_stacks_cli/commands/login.py
"""agentic-stacks login — authenticate with the registry."""

import click

from agentic_stacks_cli.config import load_config, save_config


@click.command()
@click.option("--token", default=None, help="GitHub personal access token")
@click.option("--config", "config_path", default=None, type=click.Path(),
              help="Config file path (default: ~/.config/agentic-stacks/config.yaml)")
def login(token: str | None, config_path: str | None):
    """Authenticate with the Agentic Stacks registry."""
    from pathlib import Path
    cfg_path = Path(config_path) if config_path else None

    if not token:
        token = click.prompt("GitHub personal access token", hide_input=True)

    cfg = load_config(cfg_path)
    cfg["token"] = token
    save_config(cfg, cfg_path)

    click.echo("Logged in. Token saved.")
```

- [ ] **Step 4: Register command**

Add to `src/agentic_stacks_cli/__init__.py`:

```python
from agentic_stacks_cli.commands.login import login
```

And: `cli.add_command(login)`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_login.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/login.py src/agentic_stacks_cli/__init__.py tests/test_cli_login.py
git commit -m "feat: agentic-stacks login command"
```

---

### Task 6: `agentic-stacks publish` Command

**Files:**
- Create: `src/agentic_stacks_cli/commands/publish.py`
- Create: `tests/test_cli_publish.py`
- Modify: `src/agentic_stacks_cli/__init__.py` (register command)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_publish.py
import yaml
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_publishable_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "A test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [], "deprecations": [],
        "requires": {"tools": ["test-tool"], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object"}))


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
def test_publish_success(mock_client_cls, mock_push, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test", "registry": "ghcr.io",
                                       "default_namespace": "agentic-stacks",
                                       "api_url": "https://example.com/api/v1"}))

    mock_push.return_value = ("ghcr.io/agentic-stacks/test-stack:1.0.0", "sha256:abc123")
    mock_client = MagicMock()
    mock_client.register_stack.return_value = {"status": "registered"}
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code == 0
    assert "published" in result.output.lower() or "ghcr.io" in result.output
    mock_push.assert_called_once()
    mock_client.register_stack.assert_called_once()


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
def test_publish_no_token_fails(mock_client_cls, mock_push, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
    assert "login" in result.output.lower() or "token" in result.output.lower()


def test_publish_invalid_stack_fails(tmp_path):
    (tmp_path / "stack").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_publish.py -v`

- [ ] **Step 3: Implement publish command**

```python
# src/agentic_stacks_cli/commands/publish.py
"""agentic-stacks publish — package and push a stack to the registry."""

import pathlib
import tempfile

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.oci import package_stack, push_stack
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--config", "config_path", default=None, type=click.Path(),
              help="Config file path")
def publish(path: str, config_path: str | None):
    """Package and publish a stack to the registry."""
    stack_dir = pathlib.Path(path)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)

    # Check auth
    token = cfg.get("token")
    if not token:
        raise click.ClickException("Not authenticated. Run 'agentic-stacks login' first.")

    # Load and validate manifest
    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Invalid stack: {e}")

    name = manifest["name"]
    namespace = manifest["namespace"]
    version = manifest["version"]
    registry = cfg.get("registry", "ghcr.io")

    click.echo(f"Publishing {namespace}/{name}@{version}...")

    # Package
    with tempfile.TemporaryDirectory() as tmp:
        click.echo("  Packaging...")
        tarball = package_stack(stack_dir, pathlib.Path(tmp))

        # Build annotations
        annotations = {
            "dev.agentic-stacks.name": name,
            "dev.agentic-stacks.namespace": namespace,
            "dev.agentic-stacks.version": version,
            "dev.agentic-stacks.description": manifest.get("description", ""),
        }
        skills = manifest.get("skills", [])
        if skills:
            annotations["dev.agentic-stacks.skills"] = ",".join(s["name"] for s in skills)
        target = manifest.get("target", {})
        if target.get("software"):
            annotations["dev.agentic-stacks.target-software"] = target["software"]
        if target.get("versions"):
            annotations["dev.agentic-stacks.target-versions"] = ",".join(str(v) for v in target["versions"])

        # Push to OCI
        click.echo(f"  Pushing to {registry}/{namespace}/{name}:{version}...")
        ref, digest = push_stack(
            tarball_path=tarball,
            registry=registry,
            namespace=namespace,
            name=name,
            version=version,
            annotations=annotations,
        )

    click.echo(f"  Pushed: {ref}")
    click.echo(f"  Digest: {digest}")

    # Register with API
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    client = RegistryClient(api_url=api_url, token=token)
    try:
        client.register_stack({
            "namespace": namespace,
            "name": name,
            "version": version,
            "description": manifest.get("description", ""),
            "target": manifest.get("target", {}),
            "skills": manifest.get("skills", []),
            "profiles": manifest.get("profiles", {}),
            "depends_on": manifest.get("depends_on", []),
            "deprecations": manifest.get("deprecations", []),
            "requires": manifest.get("requires", {}),
            "digest": digest,
            "registry_ref": ref,
        })
        click.echo("  Registered with registry.")
    except Exception as e:
        click.echo(f"  Warning: Could not register with registry: {e}")
        click.echo("  Stack was pushed to OCI but not indexed. Register manually later.")

    click.echo(f"\nPublished {namespace}/{name}@{version}")
```

- [ ] **Step 4: Register command**

Add to `src/agentic_stacks_cli/__init__.py`:

```python
from agentic_stacks_cli.commands.publish import publish
```

And: `cli.add_command(publish)`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_publish.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/publish.py src/agentic_stacks_cli/__init__.py tests/test_cli_publish.py
git commit -m "feat: agentic-stacks publish command"
```

---

### Task 7: `agentic-stacks pull` Command

**Files:**
- Create: `src/agentic_stacks_cli/commands/pull.py`
- Create: `tests/test_cli_pull.py`
- Modify: `src/agentic_stacks_cli/__init__.py` (register command)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_pull.py
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
def test_pull_by_name_and_version(mock_client_cls, mock_pull, tmp_path):
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:abc123"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["pull", "agentic-stacks/openstack@1.3.0",
                                  "--dir", str(tmp_path),
                                  "--config", str(config_path)])
    assert result.exit_code == 0
    mock_pull.assert_called_once()


@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
def test_pull_creates_lock_entry(mock_client_cls, mock_pull, tmp_path):
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:abc123"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    runner.invoke(cli, ["pull", "agentic-stacks/openstack@1.3.0",
                         "--dir", str(tmp_path),
                         "--config", str(config_path)])

    lock_path = tmp_path / "stacks.lock"
    assert lock_path.exists()
    lock = yaml.safe_load(lock_path.read_text())
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack"
    assert lock["stacks"][0]["digest"] == "sha256:abc123"


def test_pull_invalid_reference(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["pull", "invalid-ref",
                                  "--config", str(config_path)])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_pull.py -v`

- [ ] **Step 3: Implement pull command**

```python
# src/agentic_stacks_cli/commands/pull.py
"""agentic-stacks pull — download a stack from the registry."""

import pathlib
import re

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.oci import pull_stack
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.api_client import RegistryClient


def _parse_ref(ref: str) -> tuple[str, str, str | None]:
    """Parse 'namespace/name@version' into (namespace, name, version).

    Version is optional. Raises ValueError on invalid format.
    """
    match = re.match(r"^([^/]+)/([^@]+)(?:@(.+))?$", ref)
    if not match:
        raise ValueError(
            f"Invalid reference: '{ref}'. Expected format: namespace/name or namespace/name@version"
        )
    return match.group(1), match.group(2), match.group(3)


@click.command()
@click.argument("reference", required=False)
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def pull(reference: str | None, target_dir: str, config_path: str | None):
    """Pull a stack from the registry.

    REFERENCE is namespace/name@version (e.g., agentic-stacks/openstack@1.3.0).
    If no reference given, re-pulls everything in stacks.lock.
    """
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    registry = cfg.get("registry", "ghcr.io")

    lock_path = target / "stacks.lock"

    if not reference:
        # Re-pull from lock file
        lock = read_lock(lock_path)
        if not lock["stacks"]:
            raise click.ClickException("No stacks.lock found or it's empty. Specify a stack to pull.")
        for entry in lock["stacks"]:
            ns, name = entry["name"].split("/", 1)
            version = entry["version"]
            stacks_dir = target / ".stacks" / ns / name / version
            click.echo(f"Pulling {entry['name']}@{version}...")
            pull_stack(registry=registry, namespace=ns, name=name,
                       version=version, output_dir=stacks_dir)
            click.echo(f"  Extracted to {stacks_dir}")
        click.echo("All stacks restored from lock file.")
        return

    # Parse reference
    try:
        namespace, name, version = _parse_ref(reference)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Resolve version from API if needed
    client = RegistryClient(api_url=api_url, token=cfg.get("token"))
    try:
        stack_info = client.get_stack(namespace, name, version=version)
        version = stack_info.get("version", version)
        registry_ref = stack_info.get("registry_ref", f"{registry}/{namespace}/{name}:{version}")
    except Exception:
        # If API is unavailable, construct reference directly
        if not version:
            raise click.ClickException("Version required when registry API is unavailable.")
        registry_ref = f"{registry}/{namespace}/{name}:{version}"

    # Pull from OCI
    stacks_dir = target / ".stacks" / namespace / name / version
    click.echo(f"Pulling {namespace}/{name}@{version}...")
    digest = pull_stack(registry=registry, namespace=namespace, name=name,
                        version=version, output_dir=stacks_dir)
    click.echo(f"  Extracted to {stacks_dir}")

    # Update lock file
    lock = read_lock(lock_path)
    lock = add_to_lock(lock, name=f"{namespace}/{name}", version=version,
                       digest=digest, registry=registry_ref)
    write_lock(lock, lock_path)
    click.echo(f"  Updated stacks.lock")

    click.echo(f"\nPulled {namespace}/{name}@{version}")
```

- [ ] **Step 4: Register command**

Add to `src/agentic_stacks_cli/__init__.py`:

```python
from agentic_stacks_cli.commands.pull import pull
```

And: `cli.add_command(pull)`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_pull.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/pull.py src/agentic_stacks_cli/__init__.py tests/test_cli_pull.py
git commit -m "feat: agentic-stacks pull command with lock file"
```

---

### Task 8: `agentic-stacks search` Command

**Files:**
- Create: `src/agentic_stacks_cli/commands/search.py`
- Create: `tests/test_cli_search.py`
- Modify: `src/agentic_stacks_cli/__init__.py` (register command)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_search.py
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_search_shows_results(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.search.return_value = [
        {"name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
         "description": "OpenStack deployment"},
        {"name": "kubernetes", "namespace": "agentic-stacks", "version": "2.1.0",
         "description": "Kubernetes on Talos"},
    ]
    mock_client_cls.return_value = mock_client

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "stack", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "openstack" in result.output
    assert "kubernetes" in result.output


@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_search_no_results(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.search.return_value = []
    mock_client_cls.return_value = mock_client

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "nonexistent", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "no stacks found" in result.output.lower() or "0" in result.output


def test_search_no_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_search.py -v`

- [ ] **Step 3: Implement search command**

```python
# src/agentic_stacks_cli/commands/search.py
"""agentic-stacks search — find stacks in the registry."""

import pathlib

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.argument("query")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def search(query: str, config_path: str | None):
    """Search for stacks in the registry."""
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")

    client = RegistryClient(api_url=api_url, token=cfg.get("token"))

    try:
        results = client.search(query)
    except Exception as e:
        raise click.ClickException(f"Search failed: {e}")

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

- [ ] **Step 4: Register command**

Add to `src/agentic_stacks_cli/__init__.py`:

```python
from agentic_stacks_cli.commands.search import search
```

And: `cli.add_command(search)`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_search.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/search.py src/agentic_stacks_cli/__init__.py tests/test_cli_search.py
git commit -m "feat: agentic-stacks search command"
```

---

### Task 9: `agentic-stacks upgrade` Command

**Files:**
- Create: `src/agentic_stacks_cli/commands/upgrade.py`
- Create: `tests/test_cli_upgrade.py`
- Modify: `src/agentic_stacks_cli/__init__.py` (register command)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_upgrade.py
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli
from agentic_stacks_cli.lock import write_lock


@patch("agentic_stacks_cli.commands.upgrade.pull_stack")
@patch("agentic_stacks_cli.commands.upgrade.RegistryClient")
def test_upgrade_finds_newer_version(mock_client_cls, mock_pull, tmp_path):
    # Write existing lock
    lock_path = tmp_path / "stacks.lock"
    write_lock({"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.2.0",
         "digest": "sha256:old", "registry": "ghcr.io/agentic-stacks/openstack:1.2.0"}
    ]}, lock_path)

    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0",
        "deprecations": [],
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:new123"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack",
                                  "--dir", str(tmp_path),
                                  "--config", str(config_path)])
    assert result.exit_code == 0
    assert "1.3.0" in result.output

    # Check lock was updated
    lock = yaml.safe_load(lock_path.read_text())
    assert lock["stacks"][0]["version"] == "1.3.0"


@patch("agentic_stacks_cli.commands.upgrade.RegistryClient")
def test_upgrade_already_latest(mock_client_cls, tmp_path):
    lock_path = tmp_path / "stacks.lock"
    write_lock({"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack:1.3.0"}
    ]}, lock_path)

    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0"
    }
    mock_client_cls.return_value = mock_client

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack",
                                  "--dir", str(tmp_path),
                                  "--config", str(config_path)])
    assert result.exit_code == 0
    assert "already" in result.output.lower() or "latest" in result.output.lower() or "up to date" in result.output.lower()


def test_upgrade_not_in_lock(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    write_lock({"stacks": []}, lock_path)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))

    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack",
                                  "--dir", str(tmp_path),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "lock" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_upgrade.py -v`

- [ ] **Step 3: Implement upgrade command**

```python
# src/agentic_stacks_cli/commands/upgrade.py
"""agentic-stacks upgrade — upgrade a stack to the latest version."""

import pathlib

import click

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock
from agentic_stacks_cli.oci import pull_stack
from agentic_stacks_cli.api_client import RegistryClient


@click.command()
@click.argument("name")
@click.option("--dir", "target_dir", default=".", type=click.Path(), help="Project directory")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path")
def upgrade(name: str, target_dir: str, config_path: str | None):
    """Upgrade a stack to the latest version."""
    target = pathlib.Path(target_dir)
    cfg_path = pathlib.Path(config_path) if config_path else None
    cfg = load_config(cfg_path)
    api_url = cfg.get("api_url", "https://agentic-stacks.com/api/v1")
    registry = cfg.get("registry", "ghcr.io")

    lock_path = target / "stacks.lock"
    lock = read_lock(lock_path)

    # Find current entry in lock
    current = None
    for entry in lock["stacks"]:
        entry_name = entry["name"].split("/")[-1]
        if entry_name == name or entry["name"] == name:
            current = entry
            break

    if not current:
        raise click.ClickException(
            f"Stack '{name}' not found in stacks.lock. Pull it first with 'agentic-stacks pull'."
        )

    full_name = current["name"]
    namespace, stack_name = full_name.split("/", 1)
    current_version = current["version"]

    click.echo(f"Checking for updates to {full_name} (current: {current_version})...")

    # Query API for latest
    client = RegistryClient(api_url=api_url, token=cfg.get("token"))
    try:
        latest = client.get_stack(namespace, stack_name)
    except Exception as e:
        raise click.ClickException(f"Could not check for updates: {e}")

    latest_version = latest.get("version", current_version)

    if latest_version == current_version:
        click.echo(f"Already up to date ({current_version}).")
        return

    click.echo(f"  New version available: {current_version} → {latest_version}")

    # Show deprecations
    deprecations = latest.get("deprecations", [])
    if deprecations:
        click.echo(f"\n  Deprecations in {latest_version}:")
        for dep in deprecations:
            click.echo(f"    - {dep['skill']}: use '{dep['replacement']}' instead ({dep['reason']})")

    # Pull new version
    stacks_dir = target / ".stacks" / namespace / stack_name / latest_version
    click.echo(f"\n  Pulling {full_name}@{latest_version}...")
    digest = pull_stack(registry=registry, namespace=namespace, name=stack_name,
                        version=latest_version, output_dir=stacks_dir)

    # Update lock
    registry_ref = latest.get("registry_ref", f"{registry}/{namespace}/{stack_name}:{latest_version}")
    lock = add_to_lock(lock, name=full_name, version=latest_version,
                       digest=digest, registry=registry_ref)
    write_lock(lock, lock_path)

    click.echo(f"\nUpgraded {full_name}: {current_version} → {latest_version}")
```

- [ ] **Step 4: Register command**

Add to `src/agentic_stacks_cli/__init__.py`:

```python
from agentic_stacks_cli.commands.upgrade import upgrade
```

And: `cli.add_command(upgrade)`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cli_upgrade.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agentic_stacks_cli/commands/upgrade.py src/agentic_stacks_cli/__init__.py tests/test_cli_upgrade.py
git commit -m "feat: agentic-stacks upgrade command"
```

---

### Task 10: Final Integration and Verification

**Files:**
- Create: `tests/test_cli_distribution_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_cli_distribution_integration.py
"""Integration test: full publish/pull/search/upgrade CLI workflow with mocks."""
import yaml
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "integration-test", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "Integration test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [], "deprecations": [],
        "requires": {"tools": [], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object"}))


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_publish_search_pull_workflow(
    mock_search_client_cls, mock_pull_client_cls, mock_pull_oci,
    mock_pub_client_cls, mock_push, tmp_path
):
    runner = CliRunner()
    stack_dir = tmp_path / "my-stack"
    _create_stack(stack_dir)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "token": "ghp_test", "registry": "ghcr.io",
        "default_namespace": "agentic-stacks",
        "api_url": "https://example.com/api/v1",
    }))

    # 1. Publish
    mock_push.return_value = ("ghcr.io/agentic-stacks/integration-test:1.0.0", "sha256:abc")
    mock_pub_client = MagicMock()
    mock_pub_client.register_stack.return_value = {"status": "ok"}
    mock_pub_client_cls.return_value = mock_pub_client

    result = runner.invoke(cli, ["publish", "--path", str(stack_dir), "--config", str(config_path)])
    assert result.exit_code == 0

    # 2. Search
    mock_search = MagicMock()
    mock_search.search.return_value = [
        {"name": "integration-test", "namespace": "agentic-stacks",
         "version": "1.0.0", "description": "Integration test stack"}
    ]
    mock_search_client_cls.return_value = mock_search

    result = runner.invoke(cli, ["search", "integration", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "integration-test" in result.output

    # 3. Pull
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    mock_pull_client = MagicMock()
    mock_pull_client.get_stack.return_value = {
        "name": "integration-test", "namespace": "agentic-stacks", "version": "1.0.0",
        "registry_ref": "ghcr.io/agentic-stacks/integration-test:1.0.0"
    }
    mock_pull_client_cls.return_value = mock_pull_client
    mock_pull_oci.return_value = "sha256:abc"

    result = runner.invoke(cli, ["pull", "agentic-stacks/integration-test@1.0.0",
                                  "--dir", str(project_dir), "--config", str(config_path)])
    assert result.exit_code == 0

    # 4. Verify lock file
    lock = yaml.safe_load((project_dir / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/integration-test"
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: All tests pass (62 existing + ~31 new distribution tests)

- [ ] **Step 3: Verify CLI help shows all commands**

Run: `agentic-stacks --help`
Expected: Shows init, doctor, validate, login, publish, pull, search, upgrade

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_distribution_integration.py
git commit -m "feat: distribution CLI integration test"
```
