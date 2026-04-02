import pytest
from tests.helpers import create_test_client


def test_list_stacks_with_data():
    client = create_test_client()
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert any(s["name"] == "openstack-kolla" for s in data["stacks"])


def test_list_stacks_empty():
    client = create_test_client(formulas=[])
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_search_stacks():
    client = create_test_client()
    resp = client.get("/api/v1/stacks?q=kubernetes")
    assert resp.status_code == 200
    data = resp.json()
    assert any(s["name"] == "kubernetes-talos" for s in data["stacks"])


def test_get_stack_detail():
    client = create_test_client()
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "openstack-kolla"
    assert len(data["skills"]) == 2


def test_get_stack_not_found():
    client = create_test_client()
    resp = client.get("/api/v1/stacks/agentic-stacks/nonexistent")
    assert resp.status_code == 404


def test_get_stack_version():
    client = create_test_client()
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack-kolla/0.0.1")
    assert resp.status_code == 200
    assert resp.json()["version"] == "0.0.1"


def test_get_stack_version_not_found():
    client = create_test_client()
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack-kolla/9.9.9")
    assert resp.status_code == 404


def test_list_stacks_includes_owner():
    client = create_test_client()
    resp = client.get("/api/v1/stacks")
    data = resp.json()
    for s in data["stacks"]:
        assert s["owner"] == "agentic-stacks"


def test_list_stacks_filter_by_owner():
    client = create_test_client()
    resp = client.get("/api/v1/stacks?owner=agentic-stacks")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


def test_pagination():
    client = create_test_client()
    resp = client.get("/api/v1/stacks?per_page=1&page=1")
    data = resp.json()
    assert len(data["stacks"]) == 1
    assert data["total"] == 3
