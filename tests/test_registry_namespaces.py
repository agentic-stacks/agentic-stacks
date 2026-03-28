import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
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
    from registry.models import Namespace
    ns = db_session.query(Namespace).filter_by(name="agentic-stacks").first()
    ns.verified = True
    db_session.commit()
    db.create_stack("agentic-stacks", "openstack", "OpenStack")
    db.create_version("agentic-stacks", "openstack", {
        "version": "1.0.0", "digest": "sha256:abc",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.0.0",
    })
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
