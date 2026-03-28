import pytest
from unittest.mock import patch, MagicMock
from registry.auth import verify_github_token, get_github_orgs, AuthError

def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp

def test_verify_valid_token():
    with patch("httpx.get", return_value=_mock_response(json_data={"login": "testuser"})):
        user = verify_github_token("ghp_valid")
    assert user == "testuser"

def test_verify_invalid_token():
    with patch("httpx.get", return_value=_mock_response(status_code=401)):
        with pytest.raises(AuthError, match="invalid"):
            verify_github_token("ghp_bad")

def test_get_github_orgs():
    orgs = [{"login": "agentic-stacks"}, {"login": "other-org"}]
    with patch("httpx.get", return_value=_mock_response(json_data=orgs)):
        result = get_github_orgs("ghp_valid")
    assert "agentic-stacks" in result

def test_get_github_orgs_includes_user():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(json_data={"login": "myuser"}),
            _mock_response(json_data=[{"login": "myorg"}]),
        ]
        result = get_github_orgs("ghp_valid", include_user=True)
    assert "myuser" in result
    assert "myorg" in result
