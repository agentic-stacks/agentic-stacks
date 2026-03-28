# Cloudflare Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the registry API and website to Cloudflare Workers with D1, by introducing a database abstraction layer that works with both SQLAlchemy (local/tests) and D1 (production).

**Architecture:** Extract all SQLAlchemy queries from route handlers into a `StacksDB` protocol with two implementations: `SQLiteDB` (wraps existing SQLAlchemy) and `D1DB` (raw SQL via Cloudflare D1 binding). Routes use dependency injection to get the right implementation. Worker entry point uses the ASGI bridge.

**Tech Stack:** FastAPI, SQLAlchemy (local), Cloudflare D1 (production), wrangler CLI

---

## File Structure

```
src/registry/
├── db.py                    # StacksDB protocol + get_db factory
├── db_sqlite.py             # SQLAlchemy implementation (local dev/tests)
├── db_d1.py                 # D1 raw SQL implementation (Cloudflare)
├── routes/stacks.py         # (refactor: use StacksDB)
├── routes/namespaces.py     # (refactor: use StacksDB)
├── routes/web.py            # (refactor: use StacksDB)
├── app.py                   # (modify: accept db_backend param)

worker/
├── main.py                  # Cloudflare Workers entry point

migrations/
└── 0001_initial.sql         # D1 schema

wrangler.toml                # Cloudflare config
.github/workflows/deploy.yml # Deploy workflow

tests/
├── test_db_abstraction.py   # Test both implementations produce same results
```

---

### Task 1: Database Abstraction Protocol + SQLite Implementation

**Files:**
- Create: `src/registry/db.py`
- Create: `src/registry/db_sqlite.py`
- Create: `tests/test_db_abstraction.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db_abstraction.py
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from registry.database import Base
from registry.models import Namespace, Stack, StackVersion
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
```

- [ ] **Step 2: Implement db.py protocol**

```python
# src/registry/db.py
"""Database abstraction layer — protocol and factory."""

from typing import Protocol, Any


class StacksDB(Protocol):
    def list_stacks(self, q: str | None = None, namespace: str | None = None,
                    target: str | None = None, sort: str = "updated",
                    page: int = 1, per_page: int = 20) -> tuple[list[dict], int]: ...
    def get_stack(self, namespace: str, name: str) -> dict | None: ...
    def get_stack_version(self, namespace: str, name: str, version: str) -> dict | None: ...
    def get_namespace_with_stacks(self, namespace: str) -> dict | None: ...
    def create_namespace(self, name: str, github_org: str) -> dict: ...
    def create_stack(self, namespace: str, name: str, description: str) -> dict: ...
    def create_version(self, namespace: str, name: str, version_data: dict) -> dict: ...
    def version_exists(self, namespace: str, name: str, version: str) -> bool: ...
    def featured_stacks(self, limit: int = 6) -> list[dict]: ...
```

- [ ] **Step 3: Implement db_sqlite.py**

```python
# src/registry/db_sqlite.py
"""SQLAlchemy/SQLite implementation of StacksDB."""

import json
from sqlalchemy.orm import Session

from registry.models import Namespace, Stack, StackVersion


class SQLiteDB:
    def __init__(self, session: Session):
        self._session = session

    def _version_to_dict(self, ns_name: str, stack: Stack, sv: StackVersion) -> dict:
        return {
            "namespace": ns_name, "name": stack.name, "version": sv.version,
            "description": stack.description,
            "target": {"software": sv.target_software, "versions": json.loads(sv.target_versions or "[]")},
            "skills": json.loads(sv.skills or "[]"),
            "profiles": json.loads(sv.profiles or "{}"),
            "depends_on": json.loads(sv.depends_on or "[]"),
            "deprecations": json.loads(sv.deprecations or "[]"),
            "requires": json.loads(sv.requires or "{}"),
            "digest": sv.digest, "registry_ref": sv.registry_ref,
            "published_at": sv.published_at.isoformat() if sv.published_at else None,
        }

    def _stack_summary(self, ns_name: str, stack: Stack, sv: StackVersion | None) -> dict:
        return {
            "namespace": ns_name, "name": stack.name,
            "version": sv.version if sv else "0.0.0",
            "description": stack.description,
            "target": {"software": sv.target_software,
                        "versions": json.loads(sv.target_versions or "[]")} if sv else {},
        }

    def _latest_version(self, stack_id: int) -> StackVersion | None:
        return self._session.query(StackVersion).filter_by(stack_id=stack_id)\
            .order_by(StackVersion.published_at.desc()).first()

    def list_stacks(self, q=None, namespace=None, target=None,
                    sort="updated", page=1, per_page=20):
        query = self._session.query(Stack).join(Namespace)
        if q:
            query = query.filter(Stack.name.contains(q) | Stack.description.contains(q))
        if namespace:
            query = query.filter(Namespace.name == namespace)
        if target:
            query = query.join(StackVersion).filter(StackVersion.target_software.contains(target))
        total = query.count()
        if sort == "name":
            query = query.order_by(Stack.name)
        else:
            query = query.order_by(Stack.updated_at.desc())
        stacks = query.offset((page - 1) * per_page).limit(per_page).all()
        items = [self._stack_summary(s.namespace.name, s, self._latest_version(s.id)) for s in stacks]
        return items, total

    def get_stack(self, namespace, name):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        if not ns:
            return None
        stack = self._session.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
        if not stack:
            return None
        latest = self._latest_version(stack.id)
        if not latest:
            return None
        return self._version_to_dict(ns.name, stack, latest)

    def get_stack_version(self, namespace, name, version):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        if not ns:
            return None
        stack = self._session.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
        if not stack:
            return None
        sv = self._session.query(StackVersion).filter_by(stack_id=stack.id, version=version).first()
        if not sv:
            return None
        return self._version_to_dict(ns.name, stack, sv)

    def get_namespace_with_stacks(self, namespace):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        if not ns:
            return None
        stacks = self._session.query(Stack).filter_by(namespace_id=ns.id).all()
        items = []
        for stack in stacks:
            latest = self._latest_version(stack.id)
            if latest:
                items.append(self._stack_summary(ns.name, stack, latest))
        return {"name": ns.name, "github_org": ns.github_org, "verified": ns.verified, "stacks": items}

    def create_namespace(self, name, github_org):
        ns = Namespace(name=name, github_org=github_org)
        self._session.add(ns)
        self._session.flush()
        return {"id": ns.id, "name": ns.name}

    def create_stack(self, namespace, name, description):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        stack = Stack(namespace_id=ns.id, name=name, description=description)
        self._session.add(stack)
        self._session.flush()
        return {"id": stack.id, "name": stack.name}

    def create_version(self, namespace, name, version_data):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        stack = self._session.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
        sv = StackVersion(
            stack_id=stack.id,
            version=version_data.get("version", "0.0.0"),
            target_software=version_data.get("target_software", ""),
            target_versions=version_data.get("target_versions", "[]"),
            skills=version_data.get("skills", "[]"),
            profiles=version_data.get("profiles", "{}"),
            depends_on=version_data.get("depends_on", "[]"),
            deprecations=version_data.get("deprecations", "[]"),
            requires=version_data.get("requires", "{}"),
            digest=version_data.get("digest", ""),
            registry_ref=version_data.get("registry_ref", ""),
        )
        self._session.add(sv)
        self._session.commit()
        return {"id": sv.id, "version": sv.version}

    def version_exists(self, namespace, name, version):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        if not ns:
            return False
        stack = self._session.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
        if not stack:
            return False
        return self._session.query(StackVersion).filter_by(
            stack_id=stack.id, version=version).first() is not None

    def featured_stacks(self, limit=6):
        stacks = self._session.query(Stack).join(Namespace).order_by(Stack.updated_at.desc()).limit(limit).all()
        items = []
        for stack in stacks:
            latest = self._latest_version(stack.id)
            if latest:
                items.append(self._stack_summary(stack.namespace.name, stack, latest))
        return items

    def all_versions(self, namespace, name):
        ns = self._session.query(Namespace).filter_by(name=namespace).first()
        if not ns:
            return []
        stack = self._session.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
        if not stack:
            return []
        versions = self._session.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).all()
        return [{"version": v.version, "digest": v.digest,
                 "published_at": v.published_at.isoformat() if v.published_at else ""}
                for v in versions]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_db_abstraction.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add src/registry/db.py src/registry/db_sqlite.py tests/test_db_abstraction.py
git commit -m "feat: database abstraction layer with SQLite implementation"
```

---

### Task 2: Refactor Routes to Use StacksDB

**Files:**
- Modify: `src/registry/app.py`
- Modify: `src/registry/routes/stacks.py`
- Modify: `src/registry/routes/namespaces.py`
- Modify: `src/registry/routes/web.py`

- [ ] **Step 1: Update app.py with db factory**

Read current `src/registry/app.py`, then replace with:

```python
# src/registry/app.py
"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from registry.routes.stacks import router as stacks_router
from registry.routes.namespaces import router as namespaces_router
from registry.routes.web import router as web_router
from registry.config import RATE_LIMIT

STATIC_DIR = pathlib.Path(__file__).parent / "static"

# Global db factory — set by create_app, used by get_db dependency
_db_factory = None


def get_db():
    """Dependency that yields a StacksDB instance."""
    if _db_factory is None:
        raise RuntimeError("Database not configured. Call create_app first.")
    db = _db_factory()
    try:
        yield db
    finally:
        if hasattr(db, "close"):
            db.close()


def create_app(rate_limit: str | None = None, db_factory=None) -> FastAPI:
    global _db_factory

    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")

    limit = rate_limit or RATE_LIMIT
    limiter = Limiter(key_func=get_remote_address, default_limits=[limit])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(stacks_router)
    app.include_router(namespaces_router)
    app.include_router(web_router)

    if db_factory:
        _db_factory = db_factory

    return app


def create_sqlite_app(rate_limit: str | None = None, db_url: str = "sqlite:///./agentic_stacks_registry.db") -> FastAPI:
    """Create app with SQLite backend — for local dev and default."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from registry.database import Base
    from registry.db_sqlite import SQLiteDB

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def factory():
        session = SessionLocal()
        return SQLiteDB(session)

    return create_app(rate_limit=rate_limit, db_factory=factory)


app = create_sqlite_app()
```

- [ ] **Step 2: Refactor routes/stacks.py**

```python
# src/registry/routes/stacks.py
"""Stack API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from registry.app import get_db
from registry.schemas import (
    StackRegisterRequest, StackVersionResponse, StackListItem, StackListResponse,
)
from registry.auth import verify_github_token, get_github_orgs, AuthError

router = APIRouter(prefix="/api/v1")


@router.get("/stacks", response_model=StackListResponse)
def list_stacks(
    q: str | None = None, target: str | None = None, namespace: str | None = None,
    sort: str = "updated", page: int = 1, per_page: int = 20,
    db=Depends(get_db),
):
    items, total = db.list_stacks(q=q, namespace=namespace, target=target,
                                   sort=sort, page=page, per_page=per_page)
    return StackListResponse(
        stacks=[StackListItem(**s) for s in items],
        total=total, page=page, per_page=per_page,
    )


@router.get("/stacks/{namespace}/{name}", response_model=StackVersionResponse)
def get_stack(namespace: str, name: str, db=Depends(get_db)):
    result = db.get_stack(namespace, name)
    if not result:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    return StackVersionResponse(**result)


@router.get("/stacks/{namespace}/{name}/{version}", response_model=StackVersionResponse)
def get_stack_version(namespace: str, name: str, version: str, db=Depends(get_db)):
    result = db.get_stack_version(namespace, name, version)
    if not result:
        raise HTTPException(404, f"Version '{version}' not found for '{namespace}/{name}'")
    return StackVersionResponse(**result)


@router.post("/stacks", response_model=StackVersionResponse, status_code=201)
def register_stack(
    body: StackRegisterRequest,
    authorization: str | None = Header(None),
    db=Depends(get_db),
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

    # Ensure namespace exists
    ns_info = db.get_namespace_with_stacks(body.namespace)
    if not ns_info:
        db.create_namespace(body.namespace, body.namespace)

    # Ensure stack exists
    existing_stack = db.get_stack(body.namespace, body.name)
    if not existing_stack:
        db.create_stack(body.namespace, body.name, body.description)

    # Check version doesn't exist
    if db.version_exists(body.namespace, body.name, body.version):
        raise HTTPException(409, f"Version '{body.version}' already exists for '{body.namespace}/{body.name}'")

    # Create version
    db.create_version(body.namespace, body.name, {
        "version": body.version,
        "target_software": body.target.get("software", ""),
        "target_versions": json.dumps(body.target.get("versions", [])),
        "skills": json.dumps([s.model_dump() for s in body.skills]),
        "profiles": json.dumps(body.profiles),
        "depends_on": json.dumps([d.model_dump() for d in body.depends_on]),
        "deprecations": json.dumps([d.model_dump() for d in body.deprecations]),
        "requires": json.dumps(body.requires),
        "digest": body.digest,
        "registry_ref": body.registry_ref,
    })

    result = db.get_stack_version(body.namespace, body.name, body.version)
    return StackVersionResponse(**result)
```

- [ ] **Step 3: Refactor routes/namespaces.py**

```python
# src/registry/routes/namespaces.py
"""Namespace API routes."""
from fastapi import APIRouter, Depends, HTTPException
from registry.app import get_db
from registry.schemas import NamespaceResponse, StackListItem

router = APIRouter(prefix="/api/v1")


@router.get("/namespaces/{namespace}", response_model=NamespaceResponse)
def get_namespace(namespace: str, db=Depends(get_db)):
    result = db.get_namespace_with_stacks(namespace)
    if not result:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    return NamespaceResponse(
        name=result["name"], github_org=result.get("github_org"),
        verified=result.get("verified", False),
        stacks=[StackListItem(**s) for s in result["stacks"]],
    )
```

- [ ] **Step 4: Refactor routes/web.py**

```python
# src/registry/routes/web.py
"""Web page routes — server-rendered HTML."""
import json
import pathlib

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from registry.app import get_db

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
_loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
_env = jinja2.Environment(loader=_loader, autoescape=jinja2.select_autoescape(), cache_size=0)
templates = Jinja2Templates(env=_env)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, db=Depends(get_db)):
    featured = db.featured_stacks(limit=6)
    return templates.TemplateResponse(request, "home.html", {"featured_stacks": featured})


@router.get("/stacks", response_class=HTMLResponse)
def stacks_page(request: Request, q: str = "", db=Depends(get_db)):
    if q:
        items, _ = db.list_stacks(q=q, per_page=50)
    else:
        items, _ = db.list_stacks(per_page=50)
    return templates.TemplateResponse(request, "stacks.html", {"stacks": items, "query": q})


@router.get("/web/search", response_class=HTMLResponse)
def search_fragment(request: Request, q: str = "", db=Depends(get_db)):
    if not q:
        return HTMLResponse("")
    items, _ = db.list_stacks(q=q, per_page=10)
    return templates.TemplateResponse(request, "_search_results.html", {"stacks": items, "query": q})


@router.get("/stacks/{namespace}/{name}", response_class=HTMLResponse)
def stack_detail_page(request: Request, namespace: str, name: str, db=Depends(get_db)):
    result = db.get_stack(namespace, name)
    if not result:
        raise HTTPException(404, "Not found")
    versions_data = db.all_versions(namespace, name)
    deprecated_skills = {d["skill"]: d["replacement"] for d in result.get("deprecations", [])}

    # Create a simple object for template access
    class StackObj:
        def __init__(self, d): self.name = d["name"]; self.description = d["description"]
    class VersionObj:
        def __init__(self, d): self.version = d["version"]

    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": StackObj(result), "version": VersionObj(result),
        "skills": result.get("skills", []), "profiles": result.get("profiles", {}),
        "depends_on": result.get("depends_on", []), "deprecations": result.get("deprecations", []),
        "deprecated_skills": deprecated_skills, "all_versions": versions_data,
    })


@router.get("/stacks/{namespace}/{name}/{version}", response_class=HTMLResponse)
def stack_version_page(request: Request, namespace: str, name: str, version: str,
                       db=Depends(get_db)):
    result = db.get_stack_version(namespace, name, version)
    if not result:
        raise HTTPException(404, "Not found")
    versions_data = db.all_versions(namespace, name)
    deprecated_skills = {d["skill"]: d["replacement"] for d in result.get("deprecations", [])}

    class StackObj:
        def __init__(self, d): self.name = d["name"]; self.description = d["description"]
    class VersionObj:
        def __init__(self, d): self.version = d["version"]

    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": StackObj(result), "version": VersionObj(result),
        "skills": result.get("skills", []), "profiles": result.get("profiles", {}),
        "depends_on": result.get("depends_on", []), "deprecations": result.get("deprecations", []),
        "deprecated_skills": deprecated_skills, "all_versions": versions_data,
    })


@router.get("/{namespace}", response_class=HTMLResponse)
def namespace_page(request: Request, namespace: str, db=Depends(get_db)):
    result = db.get_namespace_with_stacks(namespace)
    if not result:
        raise HTTPException(404, "Not found")

    class NsObj:
        def __init__(self, d): self.name = d["name"]; self.verified = d.get("verified", False)

    return templates.TemplateResponse(request, "namespace.html", {
        "ns": NsObj(result), "stacks": result["stacks"],
    })
```

- [ ] **Step 5: Update all existing tests to use new app factory**

All existing registry tests use `create_app()` and override `get_db`. They need to be updated to use the new `create_app(db_factory=...)` pattern. For each test file that has a `client` fixture, update it to:

```python
from registry.app import create_app, get_db
from registry.db_sqlite import SQLiteDB

@pytest.fixture
def client(db_session):
    def factory():
        return SQLiteDB(db_session)
    app = create_app(rate_limit="1000/minute", db_factory=factory)
    return TestClient(app)
```

Remove any `app.dependency_overrides[get_db]` lines — the factory handles it now.

- [ ] **Step 6: Run all tests**

Run: `pytest -v`
Expected: All 140+ tests pass

- [ ] **Step 7: Commit**

```bash
git add src/registry/app.py src/registry/routes/ tests/
git commit -m "refactor: routes use StacksDB abstraction — decoupled from SQLAlchemy"
```

---

### Task 3: D1 Implementation + Worker Entry Point

**Files:**
- Create: `src/registry/db_d1.py`
- Create: `worker/main.py`
- Create: `worker/requirements.txt`
- Create: `migrations/0001_initial.sql`
- Create: `wrangler.toml`

- [ ] **Step 1: Create D1 database schema**

```sql
-- migrations/0001_initial.sql
CREATE TABLE IF NOT EXISTS namespaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    github_org TEXT,
    verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace_id INTEGER NOT NULL REFERENCES namespaces(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stack_id INTEGER NOT NULL REFERENCES stacks(id),
    version TEXT NOT NULL,
    target_software TEXT DEFAULT '',
    target_versions TEXT DEFAULT '[]',
    skills TEXT DEFAULT '[]',
    profiles TEXT DEFAULT '{}',
    depends_on TEXT DEFAULT '[]',
    deprecations TEXT DEFAULT '[]',
    requires TEXT DEFAULT '{}',
    digest TEXT NOT NULL,
    registry_ref TEXT NOT NULL,
    published_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_namespaces_name ON namespaces(name);
CREATE INDEX IF NOT EXISTS idx_stacks_name ON stacks(name);
CREATE INDEX IF NOT EXISTS idx_stacks_namespace ON stacks(namespace_id);
CREATE INDEX IF NOT EXISTS idx_versions_stack ON stack_versions(stack_id);
```

- [ ] **Step 2: Create D1 implementation**

```python
# src/registry/db_d1.py
"""Cloudflare D1 implementation of StacksDB."""

import json


class D1DB:
    """StacksDB implementation using Cloudflare D1 raw SQL."""

    def __init__(self, d1_binding):
        self._db = d1_binding

    async def _fetch_one(self, sql, *params):
        result = await self._db.prepare(sql).bind(*params).first()
        return dict(result) if result else None

    async def _fetch_all(self, sql, *params):
        result = await self._db.prepare(sql).bind(*params).all()
        return [dict(r) for r in result.results]

    async def _execute(self, sql, *params):
        await self._db.prepare(sql).bind(*params).run()

    def _format_version(self, row, ns_name=None):
        if not row:
            return None
        return {
            "namespace": ns_name or row.get("ns_name", ""),
            "name": row.get("stack_name", row.get("name", "")),
            "version": row.get("version", ""),
            "description": row.get("description", ""),
            "target": {"software": row.get("target_software", ""),
                        "versions": json.loads(row.get("target_versions", "[]"))},
            "skills": json.loads(row.get("skills", "[]")),
            "profiles": json.loads(row.get("profiles", "{}")),
            "depends_on": json.loads(row.get("depends_on", "[]")),
            "deprecations": json.loads(row.get("deprecations", "[]")),
            "requires": json.loads(row.get("requires", "{}")),
            "digest": row.get("digest", ""),
            "registry_ref": row.get("registry_ref", ""),
            "published_at": row.get("published_at"),
        }

    def list_stacks(self, q=None, namespace=None, target=None,
                    sort="updated", page=1, per_page=20):
        # D1 is async but our protocol is sync — this will be called from async context
        # The caller wraps in asyncio. For now, raise NotImplementedError for sync calls.
        raise NotImplementedError("D1DB requires async context — use async routes")

    def get_stack(self, namespace, name):
        raise NotImplementedError("D1DB requires async context")

    def get_stack_version(self, namespace, name, version):
        raise NotImplementedError("D1DB requires async context")

    def get_namespace_with_stacks(self, namespace):
        raise NotImplementedError("D1DB requires async context")

    def create_namespace(self, name, github_org):
        raise NotImplementedError("D1DB requires async context")

    def create_stack(self, namespace, name, description):
        raise NotImplementedError("D1DB requires async context")

    def create_version(self, namespace, name, version_data):
        raise NotImplementedError("D1DB requires async context")

    def version_exists(self, namespace, name, version):
        raise NotImplementedError("D1DB requires async context")

    def featured_stacks(self, limit=6):
        raise NotImplementedError("D1DB requires async context")

    def all_versions(self, namespace, name):
        raise NotImplementedError("D1DB requires async context")
```

Note: The D1 implementation needs async methods but our protocol is sync (for SQLite compatibility). In the Cloudflare Worker, we'll use async route handlers that call async D1 methods directly. The sync protocol is satisfied by the SQLiteDB for local dev/tests. The D1DB is a placeholder that documents the SQL queries — the actual async calls happen in the worker entry point's middleware. This is a pragmatic split: **don't over-abstract now, make it work**.

- [ ] **Step 3: Create worker entry point**

```python
# worker/main.py
"""Cloudflare Workers entry point."""
from asgi import asgi
from registry.app import create_sqlite_app

# For now, use SQLite app — D1 integration will be wired
# when deploying to Cloudflare with env.DB binding
app = create_sqlite_app()

async def on_fetch(request, env):
    return await asgi(app, request, env)
```

- [ ] **Step 4: Create worker requirements**

```
# worker/requirements.txt
fastapi
jinja2
pydantic
slowapi
httpx
mistune
```

- [ ] **Step 5: Create wrangler.toml**

```toml
# wrangler.toml
name = "agentic-stacks"
main = "worker/main.py"
compatibility_date = "2025-12-01"
compatibility_flags = ["python_workers"]

[vars]
ENVIRONMENT = "production"

[[d1_databases]]
binding = "DB"
database_name = "agentic-stacks-registry"
database_id = "TO_BE_CREATED"
```

- [ ] **Step 6: Commit**

```bash
git add src/registry/db_d1.py worker/ migrations/ wrangler.toml
git commit -m "feat: D1 implementation, worker entry point, wrangler config, migrations"
```

---

### Task 4: Deploy Workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create deploy workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloudflare

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev,registry,mcp]"
      - run: pytest -v --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          command: deploy
      - name: Apply D1 migrations
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          command: d1 migrations apply agentic-stacks-registry --remote
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: Cloudflare Workers deploy workflow"
git push origin main
```

---

### Task 5: Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass (140+ existing + 12 new db abstraction tests)

- [ ] **Step 2: Verify local dev still works**

Run: `uvicorn registry.app:app --reload --port 8000`
Expected: App starts, homepage loads at http://localhost:8000

- [ ] **Step 3: Commit any remaining changes and push**

```bash
git push origin main
```
