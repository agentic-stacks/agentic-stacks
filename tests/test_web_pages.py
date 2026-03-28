import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from registry.database import Base, get_db
from registry.app import create_app
from registry.models import Namespace, Stack, StackVersion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    app = create_app(rate_limit="1000/minute")
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_homepage(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Agentic Stacks" in resp.text
    assert "search" in resp.text.lower()


def test_stacks_page(client):
    resp = client.get("/stacks")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.fixture
def seeded_db(db_session):
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks", verified=True)
    db_session.add(ns)
    db_session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack deployment via kolla-ansible")
    db_session.add(stack)
    db_session.flush()
    sv = StackVersion(
        stack_id=stack.id, version="1.3.0", target_software="openstack",
        target_versions=json.dumps(["2024.2", "2025.1"]),
        skills=json.dumps([{"name": "deploy", "description": "Deploy OpenStack"},
                           {"name": "health-check", "description": "Check health"}]),
        profiles=json.dumps({"categories": ["security", "networking", "storage"]}),
        depends_on=json.dumps([{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}]),
        deprecations=json.dumps([{"skill": "old-deploy", "since": "1.2.0", "removal": "2.0.0",
                                   "replacement": "deploy", "reason": "Replaced"}]),
        requires=json.dumps({"tools": ["kolla-ansible"]}),
        digest="sha256:abc123",
        registry_ref="ghcr.io/agentic-stacks/openstack:1.3.0",
    )
    db_session.add(sv)
    db_session.commit()
    return db_session


def test_stack_detail_page(client, seeded_db):
    resp = client.get("/stacks/agentic-stacks/openstack")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "openstack" in resp.text.lower()
    assert "deploy" in resp.text.lower()
    assert "agentic-stacks pull" in resp.text


def test_stack_detail_not_found(client):
    resp = client.get("/stacks/agentic-stacks/nonexistent")
    assert resp.status_code == 404


def test_stack_version_page(client, seeded_db):
    resp = client.get("/stacks/agentic-stacks/openstack/1.3.0")
    assert resp.status_code == 200
    assert "1.3.0" in resp.text


def test_homepage_with_stacks(client, seeded_db):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "openstack" in resp.text.lower()


def test_namespace_page(client, seeded_db):
    resp = client.get("/agentic-stacks")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "agentic-stacks" in resp.text
    assert "openstack" in resp.text.lower()


def test_namespace_page_not_found(client):
    resp = client.get("/nonexistent-ns")
    assert resp.status_code == 404
