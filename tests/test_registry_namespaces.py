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
    app = create_app()
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def seeded_db(db_session):
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks", verified=True)
    db_session.add(ns)
    db_session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    db_session.add(stack)
    db_session.flush()
    sv = StackVersion(stack_id=stack.id, version="1.0.0", digest="sha256:abc",
                      registry_ref="ghcr.io/agentic-stacks/openstack:1.0.0")
    db_session.add(sv)
    db_session.commit()
    return db_session


def test_get_namespace(client, seeded_db):
    resp = client.get("/api/v1/namespaces/agentic-stacks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "agentic-stacks"
    assert data["verified"] is True
    assert len(data["stacks"]) == 1
    assert data["stacks"][0]["name"] == "openstack"


def test_get_namespace_not_found(client):
    resp = client.get("/api/v1/namespaces/nonexistent")
    assert resp.status_code == 404
