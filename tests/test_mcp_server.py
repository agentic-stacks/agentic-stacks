import pytest
from unittest.mock import patch, MagicMock

from agentic_stacks_mcp.server import (
    search_stacks_handler,
    get_stack_info_handler,
    get_skill_handler,
    pull_stack_handler,
)

MOCK_FORMULA = {
    "name": "openstack-kolla", "owner": "agentic-stacks", "version": "1.0.0",
    "repository": "https://github.com/agentic-stacks/openstack-kolla",
    "description": "OpenStack via kolla-ansible",
    "skills": [
        {"name": "deploy", "description": "Deploy OpenStack"},
        {"name": "health-check", "description": "Validate cluster health"},
    ],
    "depends_on": [],
    "requires": {"tools": ["kolla-ansible"]},
    "target": {"software": "openstack", "versions": ["2025.1"]},
}


@pytest.mark.asyncio
async def test_search_stacks_returns_results():
    with patch("agentic_stacks_mcp.server._get_registry_path") as mock_path, \
         patch("agentic_stacks_mcp.server.search_formulas") as mock_search:
        mock_path.return_value = "/tmp/registry"
        mock_search.return_value = [MOCK_FORMULA]
        result = await search_stacks_handler(query="openstack")
    assert len(result) == 1
    assert result[0]["name"] == "openstack-kolla"


@pytest.mark.asyncio
async def test_search_stacks_empty():
    with patch("agentic_stacks_mcp.server._get_registry_path") as mock_path, \
         patch("agentic_stacks_mcp.server.search_formulas") as mock_search:
        mock_path.return_value = "/tmp/registry"
        mock_search.return_value = []
        result = await search_stacks_handler(query="nonexistent")
    assert result == []


@pytest.mark.asyncio
async def test_get_stack_info():
    with patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA
        result = await get_stack_info_handler(name="agentic-stacks/openstack-kolla")
    assert result["name"] == "openstack-kolla"
    assert len(result["skills"]) == 2


@pytest.mark.asyncio
async def test_get_stack_info_with_version():
    with patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA
        result = await get_stack_info_handler(name="agentic-stacks/openstack-kolla", version="0.9.0")
    assert result["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_skill():
    with patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="deploy")
    assert result is not None
    assert result["name"] == "deploy"


@pytest.mark.asyncio
async def test_get_skill_not_found():
    with patch("agentic_stacks_mcp.server.load_config") as mock_cfg, \
         patch("agentic_stacks_mcp.server.ensure_registry") as mock_ensure, \
         patch("agentic_stacks_mcp.server.load_formula") as mock_load:
        mock_cfg.return_value = {"default_namespace": "agentic-stacks"}
        mock_ensure.return_value = "/tmp/registry"
        mock_load.return_value = MOCK_FORMULA
        result = await get_skill_handler(stack="agentic-stacks/openstack-kolla", skill_name="nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_pull_stack(tmp_path):
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
    assert result["version"] == "1.0.0"
