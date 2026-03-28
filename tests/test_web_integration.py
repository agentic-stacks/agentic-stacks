"""Integration: register a stack via API, then browse it on the website."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from registry.database import Base, get_db
from registry.app import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    app = create_app(rate_limit="1000/minute")
    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@patch("registry.routes.stacks.verify_github_token", return_value="testuser")
@patch("registry.routes.stacks.get_github_orgs", return_value=["agentic-stacks"])
def test_publish_then_browse(mock_orgs, mock_verify, client):
    # 1. Register via API
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "openstack-kolla", "version": "1.0.0",
        "description": "OpenStack deployment via kolla-ansible",
        "target": {"software": "openstack", "versions": ["2025.1"]},
        "skills": [{"name": "deploy", "description": "Deploy OpenStack"},
                   {"name": "health-check", "description": "Validate health"}],
        "profiles": {"categories": ["security", "networking", "storage"]},
        "depends_on": [{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}],
        "deprecations": [], "requires": {"tools": ["kolla-ansible"]},
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack-kolla:1.0.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 201

    # 2. Homepage shows the stack
    resp = client.get("/")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 3. Browse page lists it
    resp = client.get("/stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 4. Search finds it
    resp = client.get("/stacks?q=openstack")
    assert "openstack-kolla" in resp.text

    # 5. Detail page works
    resp = client.get("/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    assert "deploy" in resp.text.lower()
    assert "health-check" in resp.text.lower()
    assert "agentic-stacks pull" in resp.text
    assert "security" in resp.text
    assert "networking" in resp.text

    # 6. Namespace page works
    resp = client.get("/agentic-stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 7. htmx search fragment
    resp = client.get("/web/search?q=openstack")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text
