from tests.helpers import create_test_client


def test_get_namespace():
    client = create_test_client()
    resp = client.get("/api/v1/namespaces/agentic-stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "agentic-stacks"
    assert len(data["stacks"]) == 3


def test_get_namespace_not_found():
    client = create_test_client()
    resp = client.get("/api/v1/namespaces/nonexistent")
    assert resp.status_code == 404
