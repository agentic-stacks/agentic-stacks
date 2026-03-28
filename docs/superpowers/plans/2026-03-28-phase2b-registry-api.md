# Phase 2b: Registry API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI registry service that indexes stack metadata, provides search, and authenticates publishers via GitHub tokens — the backend that the CLI and website both consume.

**Architecture:** A FastAPI app in `src/registry/` with SQLAlchemy models backed by SQLite. The API validates GitHub tokens by calling the GitHub API. Rate limiting via slowapi. The app is structured as a Python package that can be run with `uvicorn registry.app:app`.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, uvicorn, slowapi, httpx (GitHub API calls)

---

## File Structure

```
src/registry/
├── __init__.py
├── app.py                  # FastAPI app factory, middleware, lifespan
├── config.py               # Registry server config (DB URL, GitHub OAuth, rate limits)
├── models.py               # SQLAlchemy models: Stack, StackVersion, Namespace
├── database.py             # Engine, session factory, Base
├── schemas.py              # Pydantic request/response schemas
├── auth.py                 # GitHub token verification
├── routes/
│   ├── __init__.py
│   ├── stacks.py           # GET /stacks, GET /stacks/{ns}/{name}, POST /stacks
│   └── namespaces.py       # GET /namespaces/{namespace}
└── seed.py                 # Optional: seed DB with test data

tests/
├── test_registry_models.py
├── test_registry_auth.py
├── test_registry_stacks.py
├── test_registry_namespaces.py
└── test_registry_integration.py

alembic/
├── alembic.ini
├── env.py
└── versions/
```

---

### Task 1: Project Setup — Dependencies and Database

**Files:**
- Modify: `pyproject.toml` (add FastAPI deps)
- Create: `src/registry/__init__.py`
- Create: `src/registry/config.py`
- Create: `src/registry/database.py`
- Create: `src/registry/models.py`
- Create: `tests/test_registry_models.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add to `[project.optional-dependencies]`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]
registry = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "slowapi>=0.1.9",
    "httpx>=0.27",
]
```

Also add to hatch build targets:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/agentic_stacks", "src/agentic_stacks_cli", "src/registry"]
```

Run: `pip install -e ".[dev,registry]"`

- [ ] **Step 2: Write failing tests**

```python
# tests/test_registry_models.py
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from registry.database import Base
from registry.models import Namespace, Stack, StackVersion


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_namespace():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks", verified=True)
    session.add(ns)
    session.commit()
    loaded = session.query(Namespace).filter_by(name="agentic-stacks").first()
    assert loaded.name == "agentic-stacks"
    assert loaded.verified is True
    assert loaded.created_at is not None


def test_create_stack():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack deployment")
    session.add(stack)
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert loaded.name == "openstack"
    assert loaded.namespace_id == ns.id


def test_create_stack_version():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.flush()
    sv = StackVersion(
        stack_id=stack.id, version="1.3.0", target_software="openstack",
        target_versions='["2024.2", "2025.1"]',
        skills='[{"name": "deploy", "description": "Deploy"}]',
        profiles='{"categories": ["security"]}',
        depends_on="[]", deprecations="[]", requires='{"tools": ["kolla-ansible"]}',
        digest="sha256:abc123", registry_ref="ghcr.io/agentic-stacks/openstack:1.3.0",
    )
    session.add(sv)
    session.commit()
    loaded = session.query(StackVersion).filter_by(version="1.3.0").first()
    assert loaded.digest == "sha256:abc123"
    assert loaded.stack_id == stack.id


def test_stack_namespace_relationship():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert loaded.namespace.name == "agentic-stacks"


def test_stack_versions_relationship():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.flush()
    sv1 = StackVersion(stack_id=stack.id, version="1.0.0", digest="sha256:aaa",
                       registry_ref="ghcr.io/agentic-stacks/openstack:1.0.0")
    sv2 = StackVersion(stack_id=stack.id, version="1.1.0", digest="sha256:bbb",
                       registry_ref="ghcr.io/agentic-stacks/openstack:1.1.0")
    session.add_all([sv1, sv2])
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert len(loaded.versions) == 2
```

- [ ] **Step 3: Implement database.py**

```python
# src/registry/__init__.py
```

```python
# src/registry/config.py
"""Registry server configuration."""

import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./agentic_stacks_registry.db")
GITHUB_API_URL = "https://api.github.com"
RATE_LIMIT = os.environ.get("RATE_LIMIT", "60/minute")
```

```python
# src/registry/database.py
"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from registry.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Implement models.py**

```python
# src/registry/models.py
"""SQLAlchemy models for the registry."""

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from registry.database import Base


class Namespace(Base):
    __tablename__ = "namespaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    github_org = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    stacks = relationship("Stack", back_populates="namespace")


class Stack(Base):
    __tablename__ = "stacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    namespace_id = Column(Integer, ForeignKey("namespaces.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    namespace = relationship("Namespace", back_populates="stacks")
    versions = relationship("StackVersion", back_populates="stack", order_by="StackVersion.published_at")


class StackVersion(Base):
    __tablename__ = "stack_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stack_id = Column(Integer, ForeignKey("stacks.id"), nullable=False)
    version = Column(String, nullable=False)
    target_software = Column(String, default="")
    target_versions = Column(Text, default="[]")
    skills = Column(Text, default="[]")
    profiles = Column(Text, default="{}")
    depends_on = Column(Text, default="[]")
    deprecations = Column(Text, default="[]")
    requires = Column(Text, default="{}")
    digest = Column(String, nullable=False)
    registry_ref = Column(String, nullable=False)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

    stack = relationship("Stack", back_populates="versions")
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_registry_models.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/registry/ tests/test_registry_models.py
git commit -m "feat: registry database models — Namespace, Stack, StackVersion"
```

---

### Task 2: Pydantic Schemas

**Files:**
- Create: `src/registry/schemas.py`

- [ ] **Step 1: Implement schemas**

```python
# src/registry/schemas.py
"""Pydantic request/response schemas."""

from pydantic import BaseModel


class SkillInfo(BaseModel):
    name: str
    description: str = ""


class DependencyInfo(BaseModel):
    name: str
    namespace: str
    version: str


class DeprecationInfo(BaseModel):
    skill: str
    since: str
    removal: str
    replacement: str
    reason: str = ""


class StackRegisterRequest(BaseModel):
    namespace: str
    name: str
    version: str
    description: str = ""
    target: dict = {}
    skills: list[SkillInfo] = []
    profiles: dict = {}
    depends_on: list[DependencyInfo] = []
    deprecations: list[DeprecationInfo] = []
    requires: dict = {}
    digest: str
    registry_ref: str


class StackVersionResponse(BaseModel):
    namespace: str
    name: str
    version: str
    description: str = ""
    target: dict = {}
    skills: list[dict] = []
    profiles: dict = {}
    depends_on: list[dict] = []
    deprecations: list[dict] = []
    requires: dict = {}
    digest: str
    registry_ref: str
    published_at: str | None = None


class StackListItem(BaseModel):
    namespace: str
    name: str
    version: str
    description: str = ""
    target: dict = {}


class StackListResponse(BaseModel):
    stacks: list[StackListItem]
    total: int
    page: int
    per_page: int


class NamespaceResponse(BaseModel):
    name: str
    github_org: str | None = None
    verified: bool = False
    stacks: list[StackListItem] = []
```

- [ ] **Step 2: Commit**

```bash
git add src/registry/schemas.py
git commit -m "feat: Pydantic request/response schemas"
```

---

### Task 3: GitHub Auth Module

**Files:**
- Create: `src/registry/auth.py`
- Create: `tests/test_registry_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_registry_auth.py
import pytest
from unittest.mock import patch, MagicMock
from registry.auth import verify_github_token, get_github_orgs, AuthError


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_verify_valid_token():
    with patch("httpx.get", return_value=_mock_response(json_data={"login": "testuser"})):
        user = verify_github_token("ghp_valid")
    assert user == "testuser"


def test_verify_invalid_token():
    with patch("httpx.get", return_value=_mock_response(status_code=401)):
        with pytest.raises(AuthError, match="invalid"):
            verify_github_token("ghp_bad")


def test_get_github_orgs():
    orgs = [{"login": "agentic-stacks"}, {"login": "other-org"}]
    with patch("httpx.get", return_value=_mock_response(json_data=orgs)):
        result = get_github_orgs("ghp_valid")
    assert "agentic-stacks" in result
    assert "other-org" in result


def test_get_github_orgs_includes_user():
    """User's own login counts as a namespace they own."""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(json_data={"login": "myuser"}),  # /user call
            _mock_response(json_data=[{"login": "myorg"}]),  # /user/orgs call
        ]
        result = get_github_orgs("ghp_valid", include_user=True)
    assert "myuser" in result
    assert "myorg" in result
```

- [ ] **Step 2: Implement auth.py**

```python
# src/registry/auth.py
"""GitHub token verification."""

import httpx
from registry.config import GITHUB_API_URL


class AuthError(Exception):
    pass


def verify_github_token(token: str) -> str:
    """Verify a GitHub token and return the username.

    Raises AuthError if the token is invalid.
    """
    resp = httpx.get(
        f"{GITHUB_API_URL}/user",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    if resp.status_code == 401:
        raise AuthError("Token is invalid or expired.")
    resp.raise_for_status()
    return resp.json()["login"]


def get_github_orgs(token: str, include_user: bool = False) -> list[str]:
    """Get the list of GitHub orgs the token owner belongs to.

    If include_user is True, also includes the user's own login as a namespace.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    orgs = []

    if include_user:
        user_resp = httpx.get(f"{GITHUB_API_URL}/user", headers=headers)
        user_resp.raise_for_status()
        orgs.append(user_resp.json()["login"])

    orgs_resp = httpx.get(f"{GITHUB_API_URL}/user/orgs", headers=headers)
    orgs_resp.raise_for_status()
    orgs.extend(org["login"] for org in orgs_resp.json())

    return orgs
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_registry_auth.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add src/registry/auth.py tests/test_registry_auth.py
git commit -m "feat: GitHub token verification for registry auth"
```

---

### Task 4: Stacks API Routes

**Files:**
- Create: `src/registry/routes/__init__.py`
- Create: `src/registry/routes/stacks.py`
- Create: `src/registry/app.py`
- Create: `tests/test_registry_stacks.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_registry_stacks.py
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import patch

from registry.database import Base, get_db
from registry.app import create_app
from registry.models import Namespace, Stack, StackVersion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
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
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack deployment")
    db_session.add(stack)
    db_session.flush()
    sv = StackVersion(
        stack_id=stack.id, version="1.3.0", target_software="openstack",
        target_versions=json.dumps(["2024.2", "2025.1"]),
        skills=json.dumps([{"name": "deploy", "description": "Deploy"}]),
        profiles=json.dumps({"categories": ["security"]}),
        depends_on=json.dumps([]), deprecations=json.dumps([]),
        requires=json.dumps({"tools": ["kolla-ansible"]}),
        digest="sha256:abc123",
        registry_ref="ghcr.io/agentic-stacks/openstack:1.3.0",
    )
    db_session.add(sv)
    db_session.commit()
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
```

- [ ] **Step 2: Implement routes and app**

```python
# src/registry/routes/__init__.py
```

```python
# src/registry/routes/stacks.py
"""Stack API routes."""

import json

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion
from registry.schemas import (
    StackRegisterRequest, StackVersionResponse, StackListItem, StackListResponse,
)
from registry.auth import verify_github_token, get_github_orgs, AuthError

router = APIRouter(prefix="/api/v1")


@router.get("/stacks", response_model=StackListResponse)
def list_stacks(
    q: str | None = None,
    target: str | None = None,
    namespace: str | None = None,
    sort: str = "updated",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Stack).join(Namespace)

    if q:
        query = query.filter(
            Stack.name.contains(q) | Stack.description.contains(q)
        )
    if namespace:
        query = query.filter(Namespace.name == namespace)

    # Filter by target software requires joining versions
    if target:
        query = query.join(StackVersion).filter(
            StackVersion.target_software.contains(target)
        )

    total = query.count()

    if sort == "name":
        query = query.order_by(Stack.name)
    else:
        query = query.order_by(Stack.updated_at.desc())

    stacks = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        items.append(StackListItem(
            namespace=stack.namespace.name,
            name=stack.name,
            version=latest.version if latest else "0.0.0",
            description=stack.description,
            target=json.loads(latest.target_versions) if latest else {},
        ))

    return StackListResponse(stacks=items, total=total, page=page, per_page=per_page)


@router.get("/stacks/{namespace}/{name}", response_model=StackVersionResponse)
def get_stack(namespace: str, name: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).first()
    if not latest:
        raise HTTPException(404, f"No versions published for '{namespace}/{name}'")
    return _version_response(ns.name, stack, latest)


@router.get("/stacks/{namespace}/{name}/{version}", response_model=StackVersionResponse)
def get_stack_version(namespace: str, name: str, version: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    sv = db.query(StackVersion).filter_by(stack_id=stack.id, version=version).first()
    if not sv:
        raise HTTPException(404, f"Version '{version}' not found for '{namespace}/{name}'")
    return _version_response(ns.name, stack, sv)


@router.post("/stacks", response_model=StackVersionResponse, status_code=201)
def register_stack(
    body: StackRegisterRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header required")
    token = authorization.split(" ", 1)[1]

    try:
        username = verify_github_token(token)
    except AuthError:
        raise HTTPException(401, "Invalid GitHub token")

    user_orgs = get_github_orgs(token, include_user=True)
    if body.namespace not in user_orgs:
        raise HTTPException(403, f"You don't have access to namespace '{body.namespace}'")

    # Get or create namespace
    ns = db.query(Namespace).filter_by(name=body.namespace).first()
    if not ns:
        ns = Namespace(name=body.namespace, github_org=body.namespace)
        db.add(ns)
        db.flush()

    # Get or create stack
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=body.name).first()
    if not stack:
        stack = Stack(namespace_id=ns.id, name=body.name, description=body.description)
        db.add(stack)
        db.flush()
    else:
        stack.description = body.description

    # Check if version already exists
    existing = db.query(StackVersion).filter_by(stack_id=stack.id, version=body.version).first()
    if existing:
        raise HTTPException(409, f"Version '{body.version}' already exists for '{body.namespace}/{body.name}'")

    sv = StackVersion(
        stack_id=stack.id,
        version=body.version,
        target_software=body.target.get("software", ""),
        target_versions=json.dumps(body.target.get("versions", [])),
        skills=json.dumps([s.model_dump() for s in body.skills]),
        profiles=json.dumps(body.profiles),
        depends_on=json.dumps([d.model_dump() for d in body.depends_on]),
        deprecations=json.dumps([d.model_dump() for d in body.deprecations]),
        requires=json.dumps(body.requires),
        digest=body.digest,
        registry_ref=body.registry_ref,
    )
    db.add(sv)
    db.commit()

    return _version_response(ns.name, stack, sv)


def _version_response(namespace: str, stack: Stack, sv: StackVersion) -> StackVersionResponse:
    return StackVersionResponse(
        namespace=namespace,
        name=stack.name,
        version=sv.version,
        description=stack.description,
        target={"software": sv.target_software, "versions": json.loads(sv.target_versions)},
        skills=json.loads(sv.skills),
        profiles=json.loads(sv.profiles),
        depends_on=json.loads(sv.depends_on),
        deprecations=json.loads(sv.deprecations),
        requires=json.loads(sv.requires),
        digest=sv.digest,
        registry_ref=sv.registry_ref,
        published_at=sv.published_at.isoformat() if sv.published_at else None,
    )
```

```python
# src/registry/app.py
"""FastAPI application factory."""

from fastapi import FastAPI

from registry.routes.stacks import router as stacks_router


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")
    app.include_router(stacks_router)
    return app


app = create_app()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_registry_stacks.py -v`
Expected: 12 passed

- [ ] **Step 4: Commit**

```bash
git add src/registry/routes/ src/registry/app.py src/registry/schemas.py tests/test_registry_stacks.py
git commit -m "feat: stacks API routes — list, search, detail, register"
```

---

### Task 5: Namespaces Route

**Files:**
- Create: `src/registry/routes/namespaces.py`
- Modify: `src/registry/app.py` (register router)
- Create: `tests/test_registry_namespaces.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_registry_namespaces.py
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from registry.database import Base, get_db
from registry.app import create_app
from registry.models import Namespace, Stack, StackVersion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
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
```

- [ ] **Step 2: Implement namespaces route**

```python
# src/registry/routes/namespaces.py
"""Namespace API routes."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion
from registry.schemas import NamespaceResponse, StackListItem

router = APIRouter(prefix="/api/v1")


@router.get("/namespaces/{namespace}", response_model=NamespaceResponse)
def get_namespace(namespace: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")

    stacks = db.query(Stack).filter_by(namespace_id=ns.id).all()
    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append(StackListItem(
                namespace=ns.name,
                name=stack.name,
                version=latest.version,
                description=stack.description,
                target={"software": latest.target_software,
                        "versions": json.loads(latest.target_versions)},
            ))

    return NamespaceResponse(
        name=ns.name,
        github_org=ns.github_org,
        verified=ns.verified,
        stacks=items,
    )
```

- [ ] **Step 3: Register router in app.py**

Update `src/registry/app.py`:

```python
# src/registry/app.py
"""FastAPI application factory."""

from fastapi import FastAPI

from registry.routes.stacks import router as stacks_router
from registry.routes.namespaces import router as namespaces_router


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")
    app.include_router(stacks_router)
    app.include_router(namespaces_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_registry_namespaces.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/registry/routes/namespaces.py src/registry/app.py tests/test_registry_namespaces.py
git commit -m "feat: namespaces API route"
```

---

### Task 6: Rate Limiting

**Files:**
- Modify: `src/registry/app.py` (add rate limiting middleware)
- Create: `tests/test_registry_rate_limit.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_registry_rate_limit.py
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from registry.database import Base, get_db
from registry.app import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:")
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


def test_rate_limit_headers(client):
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    # slowapi adds rate limit headers
    assert "x-ratelimit-limit" in resp.headers or resp.status_code == 200


def test_rate_limit_exceeded(client):
    for _ in range(6):
        resp = client.get("/api/v1/stacks")
    assert resp.status_code == 429
```

- [ ] **Step 2: Update app.py with rate limiting**

```python
# src/registry/app.py
"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from registry.routes.stacks import router as stacks_router
from registry.routes.namespaces import router as namespaces_router
from registry.config import RATE_LIMIT


def create_app(rate_limit: str | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")

    limit = rate_limit or RATE_LIMIT
    limiter = Limiter(key_func=get_remote_address, default_limits=[limit])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(stacks_router)
    app.include_router(namespaces_router)

    return app


app = create_app()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_registry_rate_limit.py -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add src/registry/app.py tests/test_registry_rate_limit.py
git commit -m "feat: rate limiting via slowapi"
```

---

### Task 7: Registry Integration Test

**Files:**
- Create: `tests/test_registry_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_registry_integration.py
"""End-to-end: register a stack, search for it, get detail, check namespace."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from registry.database import Base, get_db
from registry.app import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:")
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
    assert data["version"] == "1.1.0"  # latest

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
```

- [ ] **Step 2: Run all registry tests**

Run: `pytest tests/test_registry_*.py -v`
Expected: All pass (~26 registry tests)

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: All tests pass (~123 total)

- [ ] **Step 4: Verify server starts**

Run: `uvicorn registry.app:app --port 8000 &` then `curl http://localhost:8000/api/v1/stacks` then kill the server.
Expected: Returns `{"stacks":[],"total":0,"page":1,"per_page":20}`

- [ ] **Step 5: Commit**

```bash
git add tests/test_registry_integration.py
git commit -m "feat: registry integration test — full workflow"
```
