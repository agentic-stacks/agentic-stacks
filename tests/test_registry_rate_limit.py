import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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

    app = create_app(rate_limit="5/minute", db_factory=factory)
    return TestClient(app)


def test_rate_limit_allows_normal_usage(client):
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200


def test_rate_limit_exceeded(client):
    for _ in range(6):
        resp = client.get("/api/v1/stacks")
    assert resp.status_code == 429
