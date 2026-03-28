"""End-to-end: register a stack, search for it, get detail, check namespace."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from registry.database import Base
from registry.app import create_app
from registry.db_sqlite import SQLiteDB


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def factory():
        return SQLiteDB(TestSession())

    app = create_app(rate_limit="1000/minute", db_factory=factory)
    return TestClient(app)


@patch("registry.routes.stacks.verify_github_token", return_value="testuser")
@patch("registry.routes.stacks.get_github_orgs", return_value=["agentic-stacks"])
def test_full_registry_workflow(mock_orgs, mock_verify, client):
    # 1. Register a stack
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "openstack", "version": "1.0.0",
        "description": "OpenStack via kolla-ansible",
        "target": {"software": "openstack", "versions": ["2025.1"]},
        "skills": [{"name": "deploy", "description": "Deploy OpenStack"}],
        "profiles": {"categories": ["security", "networking"]},
        "depends_on": [], "deprecations": [],
        "requires": {"tools": ["kolla-ansible"]},
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.0.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 201

    # 2. Register a second version
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "openstack", "version": "1.1.0",
        "description": "OpenStack via kolla-ansible",
        "target": {"software": "openstack", "versions": ["2025.1"]},
        "skills": [{"name": "deploy", "description": "Deploy"}, {"name": "health-check", "description": "Check health"}],
        "digest": "sha256:def456",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.1.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 201

    # 3. Search
    resp = client.get("/api/v1/stacks", params={"q": "openstack"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["stacks"][0]["name"] == "openstack"

    # 4. Get latest version
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.1.0"

    # 5. Get specific version
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack/1.0.0")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"

    # 6. Check namespace
    resp = client.get("/api/v1/namespaces/agentic-stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "agentic-stacks"
    assert len(data["stacks"]) == 1

    # 7. Duplicate version fails
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "openstack", "version": "1.0.0",
        "description": "dupe", "digest": "sha256:xxx",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.0.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 409
