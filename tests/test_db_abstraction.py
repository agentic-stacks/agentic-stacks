import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from registry.database import Base
from registry.db_sqlite import SQLiteDB


@pytest.fixture
def sqlite_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    db = SQLiteDB(session)
    yield db
    session.close()


@pytest.fixture
def seeded_sqlite_db(sqlite_db):
    sqlite_db.create_namespace("agentic-stacks", "agentic-stacks")
    sqlite_db.create_stack("agentic-stacks", "openstack", "OpenStack deployment")
    sqlite_db.create_version("agentic-stacks", "openstack", {
        "version": "1.0.0", "target_software": "openstack",
        "target_versions": json.dumps(["2025.1"]),
        "skills": json.dumps([{"name": "deploy", "description": "Deploy"}]),
        "profiles": json.dumps({"categories": ["security"]}),
        "depends_on": json.dumps([]), "deprecations": json.dumps([]),
        "requires": json.dumps({"tools": ["kolla-ansible"]}),
        "digest": "sha256:abc", "registry_ref": "ghcr.io/agentic-stacks/openstack:1.0.0",
    })
    return sqlite_db


def test_list_stacks_empty(sqlite_db):
    stacks, total = sqlite_db.list_stacks()
    assert stacks == []
    assert total == 0


def test_list_stacks(seeded_sqlite_db):
    stacks, total = seeded_sqlite_db.list_stacks()
    assert total == 1
    assert stacks[0]["name"] == "openstack"
    assert stacks[0]["namespace"] == "agentic-stacks"


def test_search_stacks(seeded_sqlite_db):
    stacks, total = seeded_sqlite_db.list_stacks(q="openstack")
    assert total == 1
    stacks, total = seeded_sqlite_db.list_stacks(q="nonexistent")
    assert total == 0


def test_get_stack(seeded_sqlite_db):
    result = seeded_sqlite_db.get_stack("agentic-stacks", "openstack")
    assert result is not None
    assert result["name"] == "openstack"
    assert result["version"] == "1.0.0"


def test_get_stack_not_found(seeded_sqlite_db):
    result = seeded_sqlite_db.get_stack("agentic-stacks", "nonexistent")
    assert result is None


def test_get_stack_version(seeded_sqlite_db):
    result = seeded_sqlite_db.get_stack_version("agentic-stacks", "openstack", "1.0.0")
    assert result is not None
    assert result["version"] == "1.0.0"
    assert result["digest"] == "sha256:abc"


def test_get_namespace(seeded_sqlite_db):
    result = seeded_sqlite_db.get_namespace_with_stacks("agentic-stacks")
    assert result is not None
    assert result["name"] == "agentic-stacks"
    assert len(result["stacks"]) == 1


def test_get_namespace_not_found(seeded_sqlite_db):
    result = seeded_sqlite_db.get_namespace_with_stacks("nonexistent")
    assert result is None


def test_create_and_retrieve(sqlite_db):
    sqlite_db.create_namespace("test-ns", "test-ns")
    sqlite_db.create_stack("test-ns", "test-stack", "A test")
    sqlite_db.create_version("test-ns", "test-stack", {
        "version": "0.1.0", "digest": "sha256:test",
        "registry_ref": "ghcr.io/test/test:0.1.0",
    })
    result = sqlite_db.get_stack("test-ns", "test-stack")
    assert result["version"] == "0.1.0"


def test_version_exists(seeded_sqlite_db):
    assert seeded_sqlite_db.version_exists("agentic-stacks", "openstack", "1.0.0") is True
    assert seeded_sqlite_db.version_exists("agentic-stacks", "openstack", "9.9.9") is False


def test_featured_stacks(seeded_sqlite_db):
    stacks = seeded_sqlite_db.featured_stacks(limit=6)
    assert len(stacks) == 1
    assert stacks[0]["name"] == "openstack"


def test_all_versions(seeded_sqlite_db):
    versions = seeded_sqlite_db.all_versions("agentic-stacks", "openstack")
    assert len(versions) == 1
    assert versions[0]["version"] == "1.0.0"
