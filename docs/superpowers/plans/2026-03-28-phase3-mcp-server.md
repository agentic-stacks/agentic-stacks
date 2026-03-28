# Phase 3: Agent Discovery Protocol (MCP Server) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MCP server that exposes the Agentic Stacks registry as tools any AI agent can call — enabling agents to search for, evaluate, and pull stacks at runtime.

**Architecture:** A Python MCP server using the `mcp` SDK. It wraps our existing `RegistryClient` (from Phase 2a) and `oci.py` module to provide four tools: `search_stacks`, `get_stack_info`, `get_skill`, and `pull_stack`. The server runs as a standalone process that agents connect to via stdio transport. It reads the same CLI config for registry URL and auth.

**Tech Stack:** Python 3.11+, mcp SDK (`mcp[cli]`), existing agentic_stacks + agentic_stacks_cli modules

---

## File Structure

```
src/agentic_stacks_mcp/
├── __init__.py              # Package marker
├── server.py                # MCP server with all four tools
└── config.py                # Server config (reuses CLI config)

tests/
├── test_mcp_server.py       # Unit tests for tool handlers
└── test_mcp_integration.py  # Integration test
```

---

### Task 1: MCP Server Setup and search_stacks Tool

**Files:**
- Modify: `pyproject.toml` (add mcp dependency, add entrypoint, add to hatch targets)
- Create: `src/agentic_stacks_mcp/__init__.py`
- Create: `src/agentic_stacks_mcp/server.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Add dependencies and entrypoint**

Add to `pyproject.toml` optional deps:
```toml
mcp = [
    "mcp[cli]>=1.0",
    "httpx>=0.27",
]
```

Update hatch targets:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/agentic_stacks", "src/agentic_stacks_cli", "src/registry", "src/agentic_stacks_mcp"]
```

Add entrypoint:
```toml
[project.scripts]
agentic-stacks = "agentic_stacks_cli:main"
agentic-stacks-mcp = "agentic_stacks_mcp.server:main"
```

Run: `pip install -e ".[dev,registry,mcp]"`

- [ ] **Step 2: Write failing tests**

```python
# tests/test_mcp_server.py
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from agentic_stacks_mcp.server import search_stacks_handler


@pytest.mark.asyncio
async def test_search_stacks_returns_results():
    mock_results = [
        {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
         "description": "OpenStack via kolla-ansible"},
        {"name": "kubernetes-talos", "namespace": "agentic-stacks", "version": "2.1.0",
         "description": "Kubernetes on Talos"},
    ]
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.search.return_value = mock_results
        mock_get.return_value = mock_client

        result = await search_stacks_handler(query="openstack")

    assert len(result) == 2
    assert result[0]["name"] == "openstack-kolla"


@pytest.mark.asyncio
async def test_search_stacks_empty():
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_get.return_value = mock_client

        result = await search_stacks_handler(query="nonexistent")

    assert result == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pip install pytest-asyncio && pytest tests/test_mcp_server.py -v`
Expected: FAIL with ImportError

- [ ] **Step 4: Create package and server**

```python
# src/agentic_stacks_mcp/__init__.py
"""Agentic Stacks MCP Server — agent discovery protocol."""
```

```python
# src/agentic_stacks_mcp/server.py
"""MCP server exposing Agentic Stacks registry as agent-callable tools."""

from mcp.server.fastmcp import FastMCP

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.api_client import RegistryClient

mcp = FastMCP("agentic-stacks")

_client_instance = None


def _get_client() -> RegistryClient:
    global _client_instance
    if _client_instance is None:
        cfg = load_config()
        _client_instance = RegistryClient(
            api_url=cfg.get("api_url", "https://agentic-stacks.com/api/v1"),
            token=cfg.get("token"),
        )
    return _client_instance


async def search_stacks_handler(query: str) -> list[dict]:
    """Search the registry and return matching stacks."""
    client = _get_client()
    return client.search(query)


@mcp.tool()
async def search_stacks(query: str) -> str:
    """Search for stacks in the Agentic Stacks registry.

    Use this when you need to find a stack that provides domain expertise.
    For example: "kubernetes deployment", "openstack", "ceph storage".

    Returns a list of matching stacks with name, namespace, version, and description.
    """
    results = await search_stacks_handler(query)
    if not results:
        return f"No stacks found for '{query}'."
    lines = [f"Found {len(results)} stack(s):\n"]
    for s in results:
        lines.append(f"  {s['namespace']}/{s['name']}@{s.get('version', 'latest')}")
        if s.get("description"):
            lines.append(f"    {s['description']}")
    return "\n".join(lines)


def main():
    mcp.run()
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_mcp_server.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/agentic_stacks_mcp/ tests/test_mcp_server.py
git commit -m "feat: MCP server with search_stacks tool"
```

---

### Task 2: get_stack_info Tool

**Files:**
- Modify: `src/agentic_stacks_mcp/server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_mcp_server.py`:

```python
from agentic_stacks_mcp.server import get_stack_info_handler


@pytest.mark.asyncio
async def test_get_stack_info():
    mock_data = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "OpenStack via kolla-ansible",
        "skills": [{"name": "deploy", "description": "Deploy OpenStack"}],
        "profiles": {"categories": ["security", "networking"]},
        "depends_on": [{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}],
        "deprecations": [],
        "requires": {"tools": ["kolla-ansible"]},
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack-kolla:1.0.0",
    }
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_stack.return_value = mock_data
        mock_get.return_value = mock_client

        result = await get_stack_info_handler(name="agentic-stacks/openstack-kolla")

    assert result["name"] == "openstack-kolla"
    assert len(result["skills"]) == 1


@pytest.mark.asyncio
async def test_get_stack_info_with_version():
    mock_data = {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "0.9.0"}
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_stack.return_value = mock_data
        mock_get.return_value = mock_client

        result = await get_stack_info_handler(name="agentic-stacks/openstack-kolla", version="0.9.0")

    assert result["version"] == "0.9.0"
    mock_client.get_stack.assert_called_with("agentic-stacks", "openstack-kolla", version="0.9.0")
```

- [ ] **Step 2: Implement handler and tool**

Add to `src/agentic_stacks_mcp/server.py`:

```python
import json


async def get_stack_info_handler(name: str, version: str | None = None) -> dict:
    """Get detailed info about a stack."""
    client = _get_client()
    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = name
    return client.get_stack(namespace, stack_name, version=version)


@mcp.tool()
async def get_stack_info(name: str, version: str | None = None) -> str:
    """Get detailed information about a specific stack.

    Args:
        name: Stack name in "namespace/name" format (e.g., "agentic-stacks/openstack-kolla").
        version: Optional specific version. If omitted, returns the latest version.

    Returns detailed information including skills, profiles, dependencies, and install command.
    """
    try:
        info = await get_stack_info_handler(name, version)
    except Exception as e:
        return f"Error: Could not get info for '{name}': {e}"

    lines = [f"Stack: {info.get('namespace', '')}/{info['name']}@{info['version']}"]
    lines.append(f"Description: {info.get('description', 'No description')}")

    skills = info.get("skills", [])
    if skills:
        lines.append(f"\nSkills ({len(skills)}):")
        for s in skills:
            desc = f" — {s['description']}" if s.get("description") else ""
            lines.append(f"  - {s['name']}{desc}")

    profiles = info.get("profiles", {})
    categories = profiles.get("categories", [])
    if categories:
        lines.append(f"\nProfile categories: {', '.join(categories)}")

    deps = info.get("depends_on", [])
    if deps:
        lines.append(f"\nDependencies:")
        for d in deps:
            lines.append(f"  - {d['namespace']}/{d['name']} {d['version']}")

    deprecations = info.get("deprecations", [])
    if deprecations:
        lines.append(f"\nDeprecations:")
        for d in deprecations:
            lines.append(f"  - {d['skill']}: use '{d['replacement']}' instead")

    requires = info.get("requires", {})
    tools = requires.get("tools", [])
    if tools:
        lines.append(f"\nRequired tools: {', '.join(tools)}")

    lines.append(f"\nInstall: agentic-stacks pull {info.get('namespace', '')}/{info['name']}@{info['version']}")

    return "\n".join(lines)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_mcp_server.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add src/agentic_stacks_mcp/server.py tests/test_mcp_server.py
git commit -m "feat: MCP get_stack_info tool"
```

---

### Task 3: get_skill and pull_stack Tools

**Files:**
- Modify: `src/agentic_stacks_mcp/server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_mcp_server.py`:

```python
from agentic_stacks_mcp.server import pull_stack_handler


@pytest.mark.asyncio
async def test_get_skill_tool():
    """Test get_skill returns formatted skill content."""
    mock_data = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
        "skills": [
            {"name": "deploy", "description": "Deploy OpenStack using kolla-ansible"},
            {"name": "health-check", "description": "Validate cluster health"},
        ],
    }
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_stack.return_value = mock_data
        mock_get.return_value = mock_client

        from agentic_stacks_mcp.server import get_skill_handler
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="deploy")

    assert result is not None
    assert "deploy" in result["name"].lower()
    assert "Deploy OpenStack" in result["description"]


@pytest.mark.asyncio
async def test_get_skill_not_found():
    mock_data = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
        "skills": [{"name": "deploy", "description": "Deploy"}],
    }
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_stack.return_value = mock_data
        mock_get.return_value = mock_client

        from agentic_stacks_mcp.server import get_skill_handler
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_pull_stack_handler():
    with patch("agentic_stacks_mcp.server._get_client") as mock_get, \
         patch("agentic_stacks_mcp.server.oci_pull_stack") as mock_pull:
        mock_client = MagicMock()
        mock_client.get_stack.return_value = {
            "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
            "registry_ref": "ghcr.io/agentic-stacks/openstack-kolla:1.0.0",
        }
        mock_get.return_value = mock_client
        mock_pull.return_value = "sha256:abc123"

        result = await pull_stack_handler(
            name="agentic-stacks/openstack-kolla", version="1.0.0", path="/tmp/test"
        )

    assert result["digest"] == "sha256:abc123"
    assert "openstack-kolla" in result["path"]
    mock_pull.assert_called_once()
```

- [ ] **Step 2: Implement handlers and tools**

Add to `src/agentic_stacks_mcp/server.py`:

```python
from agentic_stacks_cli.oci import pull_stack as oci_pull_stack
import pathlib


async def get_skill_handler(stack: str, skill_name: str) -> dict | None:
    """Get info about a specific skill in a stack."""
    client = _get_client()
    if "/" in stack:
        namespace, stack_name = stack.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = stack
    info = client.get_stack(namespace, stack_name)
    for skill in info.get("skills", []):
        if skill["name"] == skill_name:
            return skill
    return None


@mcp.tool()
async def get_skill(stack: str, skill_name: str) -> str:
    """Get information about a specific skill in a stack.

    Args:
        stack: Stack name in "namespace/name" format.
        skill_name: Name of the skill to look up.

    Returns the skill description and metadata.
    """
    result = await get_skill_handler(stack, skill_name)
    if not result:
        return f"Skill '{skill_name}' not found in stack '{stack}'."
    lines = [f"Skill: {result['name']}"]
    if result.get("description"):
        lines.append(f"Description: {result['description']}")
    return "\n".join(lines)


async def pull_stack_handler(name: str, version: str, path: str) -> dict:
    """Pull a stack to a local directory."""
    client = _get_client()
    cfg = load_config()
    registry = cfg.get("registry", "ghcr.io")

    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = name

    info = client.get_stack(namespace, stack_name, version=version)
    actual_version = info.get("version", version)

    output_dir = pathlib.Path(path) / ".stacks" / namespace / stack_name / actual_version
    digest = oci_pull_stack(
        registry=registry, namespace=namespace, name=stack_name,
        version=actual_version, output_dir=output_dir,
    )
    return {"path": str(output_dir), "digest": digest, "version": actual_version}


@mcp.tool()
async def pull_stack(name: str, version: str, path: str = ".") -> str:
    """Pull a stack from the registry to a local directory.

    This downloads the stack so its skills and profiles can be loaded into context.

    Args:
        name: Stack name in "namespace/name" format (e.g., "agentic-stacks/openstack-kolla").
        version: Version to pull (e.g., "1.0.0").
        path: Local directory to pull into. Defaults to current directory.

    Returns the path where the stack was extracted.
    """
    try:
        result = await pull_stack_handler(name, version, path)
        return (
            f"Pulled {name}@{result['version']} to {result['path']}\n"
            f"Digest: {result['digest']}\n\n"
            f"The stack's skills are now available at {result['path']}/skills/"
        )
    except Exception as e:
        return f"Error pulling stack: {e}"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_mcp_server.py -v`
Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
git add src/agentic_stacks_mcp/server.py tests/test_mcp_server.py
git commit -m "feat: MCP get_skill and pull_stack tools"
```

---

### Task 4: MCP Integration Test

**Files:**
- Create: `tests/test_mcp_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_mcp_integration.py
"""Integration: test the full MCP tool suite with mocked registry."""
import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_mcp.server import (
    search_stacks, get_stack_info, get_skill, pull_stack,
    search_stacks_handler, get_stack_info_handler,
    get_skill_handler, pull_stack_handler,
)


def _mock_client_with_data():
    """Create a mock registry client with realistic test data."""
    mock_client = MagicMock()
    mock_client.search.return_value = [
        {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
         "description": "OpenStack deployment via kolla-ansible"},
    ]
    mock_client.get_stack.return_value = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "OpenStack deployment via kolla-ansible",
        "skills": [
            {"name": "deploy", "description": "Deploy OpenStack using kolla-ansible"},
            {"name": "health-check", "description": "Validate cluster health"},
        ],
        "profiles": {"categories": ["security", "networking", "storage"]},
        "depends_on": [{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}],
        "deprecations": [],
        "requires": {"tools": ["kolla-ansible"]},
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack-kolla:1.0.0",
    }
    return mock_client


@pytest.mark.asyncio
async def test_agent_discovery_workflow():
    """Simulate the full 'I know kung fu' flow."""
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = _mock_client_with_data()
        mock_get.return_value = mock_client

        # 1. Agent searches for what it needs
        results = await search_stacks_handler(query="openstack")
        assert len(results) == 1
        assert results[0]["name"] == "openstack-kolla"

        # 2. Agent evaluates the stack
        info = await get_stack_info_handler(name="agentic-stacks/openstack-kolla")
        assert info["name"] == "openstack-kolla"
        assert len(info["skills"]) == 2

        # 3. Agent looks at a specific skill
        skill = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
        assert skill is not None
        assert skill["name"] == "deploy"

    # 4. Agent pulls the stack
    with patch("agentic_stacks_mcp.server._get_client") as mock_get, \
         patch("agentic_stacks_mcp.server.oci_pull_stack") as mock_pull:
        mock_client = _mock_client_with_data()
        mock_get.return_value = mock_client
        mock_pull.return_value = "sha256:abc123"

        result = await pull_stack_handler(
            name="agentic-stacks/openstack-kolla", version="1.0.0", path="/tmp/agent-workspace"
        )
        assert "openstack-kolla" in result["path"]
        assert result["digest"] == "sha256:abc123"


@pytest.mark.asyncio
async def test_mcp_tool_output_format():
    """Verify the MCP tools return human-readable strings."""
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = _mock_client_with_data()
        mock_get.return_value = mock_client

        # search_stacks returns formatted text
        output = await search_stacks(query="openstack")
        assert "openstack-kolla" in output
        assert "Found" in output

        # get_stack_info returns formatted text
        output = await get_stack_info(name="agentic-stacks/openstack-kolla")
        assert "deploy" in output
        assert "Install:" in output

        # get_skill returns formatted text
        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
        assert "deploy" in output.lower()

        # get_skill with nonexistent skill
        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="nope")
        assert "not found" in output.lower()
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: All pass (~140 total)

- [ ] **Step 3: Commit and push**

```bash
git add tests/test_mcp_integration.py
git commit -m "feat: MCP server integration test — full agent discovery workflow"
git push origin main
```
