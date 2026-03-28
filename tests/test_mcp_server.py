import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_mcp.server import (
    search_stacks_handler,
    get_stack_info_handler,
    get_skill_handler,
    pull_stack_handler,
)


@pytest.mark.asyncio
async def test_search_stacks_returns_results():
    mock_results = [
        {"name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
         "description": "OpenStack via kolla-ansible"},
    ]
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.search.return_value = mock_results
        mock_get.return_value = mock_client
        result = await search_stacks_handler(query="openstack")
    assert len(result) == 1
    assert result[0]["name"] == "openstack-kolla"


@pytest.mark.asyncio
async def test_search_stacks_empty():
    with patch("agentic_stacks_mcp.server._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_get.return_value = mock_client
        result = await search_stacks_handler(query="nonexistent")
    assert result == []


@pytest.mark.asyncio
async def test_get_stack_info():
    mock_data = {
        "name": "openstack-kolla", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "OpenStack via kolla-ansible",
        "skills": [{"name": "deploy", "description": "Deploy OpenStack"}],
        "profiles": {"categories": ["security", "networking"]},
        "depends_on": [{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}],
        "deprecations": [], "requires": {"tools": ["kolla-ansible"]},
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


@pytest.mark.asyncio
async def test_get_skill():
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
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
    assert result is not None
    assert result["name"] == "deploy"
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
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_pull_stack():
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
