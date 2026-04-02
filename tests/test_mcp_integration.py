"""Integration: test the full MCP tool suite with mocked registry."""
import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_mcp.server import (
    search_stacks, get_stack_info, get_skill, pull_stack,
    search_stacks_handler, get_stack_info_handler,
    get_skill_handler, pull_stack_handler,
)

MOCK_FORMULA = {
    "name": "openstack-kolla", "owner": "agentic-stacks", "version": "1.0.0",
    "repository": "https://github.com/agentic-stacks/openstack-kolla",
    "description": "OpenStack deployment via kolla-ansible",
    "skills": [
        {"name": "deploy", "description": "Deploy OpenStack using kolla-ansible"},
        {"name": "health-check", "description": "Validate cluster health"},
    ],
    "depends_on": [{"name": "openstack-core", "owner": "agentic-stacks", "version": "^1.0"}],
    "requires": {"tools": ["kolla-ansible"]},
    "target": {"software": "openstack", "versions": ["2025.1"]},
}


@pytest.mark.asyncio
async def test_agent_discovery_workflow(tmp_path):
    """Simulate the full 'I know kung fu' flow."""
    with patch("agentic_stacks_mcp.server._get_registry_path") as mock_path, \
         patch("agentic_stacks_mcp.server.search_formulas") as mock_search, \
         patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_path.return_value = "/tmp/registry"
        mock_search.return_value = [MOCK_FORMULA]
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA

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
    with patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load, \
         patch("agentic_stacks_mcp.server.subprocess") as mock_sub:
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = str(tmp_path / "registry")
        mock_load.return_value = MOCK_FORMULA
        mock_sub.run.return_value = MagicMock(returncode=0)

        result = await pull_stack_handler(
            name="agentic-stacks/openstack-kolla", version="1.0.0", path=str(tmp_path / "workspace")
        )
        assert "openstack-kolla" in result["path"]


@pytest.mark.asyncio
async def test_mcp_tool_output_format():
    """Verify the MCP tools return human-readable strings."""
    with patch("agentic_stacks_mcp.server._get_registry_path") as mock_path, \
         patch("agentic_stacks_mcp.server.search_formulas") as mock_search, \
         patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_path.return_value = "/tmp/registry"
        mock_search.return_value = [MOCK_FORMULA]
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA

        output = await search_stacks(query="openstack")
        assert "openstack-kolla" in output
        assert "Found" in output

        output = await get_stack_info(name="agentic-stacks/openstack-kolla")
        assert "deploy" in output
        assert "Install:" in output

        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
        assert "deploy" in output.lower()

        mock_load.return_value = MOCK_FORMULA
        output = await get_skill(stack="agentic-stacks/openstack-kolla", skill_name="nope")
        assert "not found" in output.lower()
