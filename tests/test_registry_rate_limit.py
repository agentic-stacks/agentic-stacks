import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from registry.database import Base, get_db
from registry.app import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    app = create_app(rate_limit="5/minute")

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_rate_limit_allows_normal_usage(client):
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200


def test_rate_limit_exceeded(client):
    for _ in range(6):
        resp = client.get("/api/v1/stacks")
    assert resp.status_code == 429
