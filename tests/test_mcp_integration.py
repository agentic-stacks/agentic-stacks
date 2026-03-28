"""Integration: test the full MCP tool suite with mocked registry."""
import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_mcp.server import (
    search_stacks, get_stack_info, get_skill, pull_stack,
    search_stacks_handler, get_stack_info_handler,
    get_skill_handler, pull_stack_handler,
)


def _mock_client_with_data():
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

        output = await search_stacks(query="openstack")
        assert "openstack-kolla" in output
        assert "Found" in output

        output = await get_stack_info(name="agentic-stacks/openstack-kolla")
        assert "deploy" in output
        assert "Install:" in output

        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
        assert "deploy" in output.lower()

        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="nope")
        assert "not found" in output.lower()
