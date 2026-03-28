import json
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
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    app = create_app(rate_limit="1000/minute", db_factory=lambda: SQLiteDB(db_session))
    return TestClient(app)


@pytest.fixture
def seeded_db(db_session):
    db = SQLiteDB(db_session)
    db.create_namespace("agentic-stacks", "agentic-stacks")
    # Set verified flag directly since abstraction doesn't expose it
    from registry.models import Namespace
    ns = db_session.query(Namespace).filter_by(name="agentic-stacks").first()
    ns.verified = True
    db_session.commit()
    db.create_stack("agentic-stacks", "openstack", "OpenStack deployment")
    db.create_version("agentic-stacks", "openstack", {
        "version": "1.3.0", "target_software": "openstack",
        "target_versions": json.dumps(["2024.2", "2025.1"]),
        "skills": json.dumps([{"name": "deploy", "description": "Deploy"}]),
        "profiles": json.dumps({"categories": ["security"]}),
        "depends_on": json.dumps([]), "deprecations": json.dumps([]),
        "requires": json.dumps({"tools": ["kolla-ansible"]}),
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0",
    })
    return db_session


def test_list_stacks_empty(client):
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stacks"] == []
    assert data["total"] == 0


def test_list_stacks_with_data(client, seeded_db):
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["stacks"][0]["name"] == "openstack"
    assert data["stacks"][0]["namespace"] == "agentic-stacks"


def test_search_stacks(client, seeded_db):
    resp = client.get("/api/v1/stacks", params={"q": "openstack"})
    assert resp.status_code == 200
    assert len(resp.json()["stacks"]) == 1
    resp = client.get("/api/v1/stacks", params={"q": "nonexistent"})
    assert len(resp.json()["stacks"]) == 0


def test_get_stack_detail(client, seeded_db):
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "openstack"
    assert data["version"] == "1.3.0"
    assert data["digest"] == "sha256:abc123"


def test_get_stack_not_found(client):
    resp = client.get("/api/v1/stacks/agentic-stacks/nonexistent")
    assert resp.status_code == 404


def test_get_stack_version(client, seeded_db):
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack/1.3.0")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.3.0"


def test_get_stack_version_not_found(client, seeded_db):
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack/9.9.9")
    assert resp.status_code == 404


@patch("registry.routes.stacks.verify_github_token", return_value="testuser")
@patch("registry.routes.stacks.get_github_orgs", return_value=["agentic-stacks"])
def test_register_stack(mock_orgs, mock_verify, client):
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "kubernetes", "version": "1.0.0",
        "description": "K8s deployment", "digest": "sha256:def456",
        "registry_ref": "ghcr.io/agentic-stacks/kubernetes:1.0.0",
        "target": {"software": "kubernetes", "versions": ["1.31"]},
        "skills": [{"name": "bootstrap", "description": "Bootstrap cluster"}],
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "kubernetes"
    assert data["version"] == "1.0.0"


@patch("registry.routes.stacks.verify_github_token", return_value="testuser")
@patch("registry.routes.stacks.get_github_orgs", return_value=["other-org"])
def test_register_stack_unauthorized_namespace(mock_orgs, mock_verify, client):
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "test", "version": "1.0.0",
        "description": "test", "digest": "sha256:abc",
        "registry_ref": "ghcr.io/agentic-stacks/test:1.0.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 403


def test_register_stack_no_auth(client):
    resp = client.post("/api/v1/stacks", json={
        "namespace": "test", "name": "test", "version": "1.0.0",
        "digest": "sha256:abc", "registry_ref": "ghcr.io/test/test:1.0.0",
    })
    assert resp.status_code == 401


def test_pagination(client, seeded_db):
    resp = client.get("/api/v1/stacks", params={"page": 1, "per_page": 10})
    data = resp.json()
    assert data["page"] == 1
    assert data["per_page"] == 10
