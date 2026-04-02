import pytest
from tests.helpers import create_test_client, SAMPLE_FORMULAS


def test_homepage():
    client = create_test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Agentic Stacks" in resp.text


def test_stacks_page():
    client = create_test_client()
    resp = client.get("/stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text


def test_stack_detail_page():
    client = create_test_client()
    resp = client.get("/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text
    assert "deploy" in resp.text.lower()


def test_stack_detail_not_found():
    client = create_test_client()
    resp = client.get("/stacks/agentic-stacks/nonexistent")
    assert resp.status_code == 404


def test_stack_version_page():
    client = create_test_client()
    resp = client.get("/stacks/agentic-stacks/openstack-kolla/0.0.1")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text


def test_homepage_with_stacks():
    client = create_test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text


def test_namespace_page():
    client = create_test_client()
    resp = client.get("/agentic-stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text


def test_namespace_page_not_found():
    client = create_test_client()
    resp = client.get("/nonexistent-org")
    assert resp.status_code == 404
