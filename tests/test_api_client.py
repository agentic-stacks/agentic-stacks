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
    mock_data = {"stacks": [{"name": "openstack", "namespace": "agentic-stacks",
                              "version": "1.3.0", "description": "OpenStack deployment"}]}
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)):
        results = client.search("openstack")
    assert len(results) == 1
    assert results[0]["name"] == "openstack"


def test_get_stack():
    client = RegistryClient(api_url="https://example.com/api/v1")
    mock_data = {"name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
                 "description": "OpenStack", "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"}
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)):
        stack = client.get_stack("agentic-stacks", "openstack")
    assert stack["name"] == "openstack"


def test_get_stack_version():
    client = RegistryClient(api_url="https://example.com/api/v1")
    mock_data = {"name": "openstack", "namespace": "agentic-stacks", "version": "1.2.0"}
    with patch("httpx.Client.get", return_value=_mock_response(json_data=mock_data)):
        stack = client.get_stack("agentic-stacks", "openstack", version="1.2.0")
    assert stack["version"] == "1.2.0"


def test_register_stack():
    client = RegistryClient(api_url="https://example.com/api/v1", token="ghp_test")
    with patch("httpx.Client.post", return_value=_mock_response(json_data={"status": "registered"})):
        result = client.register_stack({"namespace": "agentic-stacks", "name": "openstack"})
    assert result["status"] == "registered"


def test_register_stack_no_token_raises():
    client = RegistryClient(api_url="https://example.com/api/v1")
    try:
        client.register_stack({"name": "test"})
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "auth" in str(e).lower() or "login" in str(e).lower()
