# Phase 2c: Website — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agentic-stacks.com website as server-rendered HTML pages served by the existing FastAPI app, with Jinja2 templates, htmx for interactivity, and Tailwind CSS for styling.

**Architecture:** Web routes are added to the existing FastAPI registry app. Templates live in `src/registry/templates/`. Static assets (CSS) live in `src/registry/static/`. The web routes query the same database as the API routes — no separate data layer. Tailwind is loaded via CDN (no build step). htmx is loaded via CDN.

**Tech Stack:** FastAPI, Jinja2, htmx (CDN), Tailwind CSS (CDN), mistune (markdown rendering)

---

## File Structure

```
src/registry/
├── app.py                      # (modify: mount templates and static files)
├── templates/
│   ├── base.html               # Base layout — head, nav, footer, htmx/tailwind CDN
│   ├── home.html               # Homepage — search, tagline, featured stacks
│   ├── stacks.html             # Browse/search stacks
│   ├── stack_detail.html       # Stack detail page with tabs
│   ├── namespace.html          # Publisher profile page
│   ├── _stack_card.html        # Partial: stack card for lists (htmx fragment)
│   └── _search_results.html    # Partial: search results (htmx fragment)
├── static/
│   └── style.css               # Minimal custom CSS beyond Tailwind
├── routes/
│   ├── stacks.py               # (existing API routes)
│   ├── namespaces.py           # (existing API routes)
│   └── web.py                  # Web page routes
└── markdown.py                 # Markdown rendering utility
tests/
├── test_web_pages.py
└── test_web_integration.py
```

---

### Task 1: Template Infrastructure

**Files:**
- Modify: `pyproject.toml` (add Jinja2, mistune)
- Modify: `src/registry/app.py` (mount templates and static)
- Create: `src/registry/templates/base.html`
- Create: `src/registry/static/style.css`
- Create: `src/registry/routes/web.py`
- Create: `tests/test_web_pages.py`

- [ ] **Step 1: Add dependencies**

Add `"jinja2>=3.1"` and `"mistune>=3.0"` to the `registry` optional deps in `pyproject.toml`. Run: `pip install -e ".[dev,registry]"`

- [ ] **Step 2: Write failing test**

```python
# tests/test_web_pages.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from registry.database import Base, get_db
from registry.app import create_app


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
```

- [ ] **Step 3: Create base template**

```html
<!-- src/registry/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Agentic Stacks{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex flex-col">
    <nav class="border-b border-gray-800 px-6 py-4">
        <div class="max-w-6xl mx-auto flex items-center justify-between">
            <a href="/" class="text-xl font-bold text-white">Agentic Stacks</a>
            <div class="flex items-center gap-6">
                <a href="/stacks" class="text-gray-400 hover:text-white transition">Browse</a>
                <a href="https://github.com/agentic-stacks" class="text-gray-400 hover:text-white transition">GitHub</a>
            </div>
        </div>
    </nav>

    <main class="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {% block content %}{% endblock %}
    </main>

    <footer class="border-t border-gray-800 px-6 py-6 text-center text-gray-500 text-sm">
        Agentic Stacks — composed domain expertise for AI agents and humans.
    </footer>
</body>
</html>
```

- [ ] **Step 4: Create minimal custom CSS**

```css
/* src/registry/static/style.css */
.stack-card {
    transition: border-color 0.2s;
}
.stack-card:hover {
    border-color: rgba(110, 231, 183, 0.4);
}
.tab-active {
    border-bottom: 2px solid #6ee7b7;
    color: #6ee7b7;
}
code {
    background: rgba(255, 255, 255, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
}
pre code {
    background: none;
    padding: 0;
}
```

- [ ] **Step 5: Create home template**

```html
<!-- src/registry/templates/home.html -->
{% extends "base.html" %}
{% block title %}Agentic Stacks — Composed Domain Expertise{% endblock %}
{% block content %}
<div class="text-center py-16">
    <h1 class="text-5xl font-bold mb-4">Agentic Stacks</h1>
    <p class="text-xl text-gray-400 mb-8">Composed domain expertise for AI agents and humans.</p>

    <div class="max-w-xl mx-auto mb-12">
        <input type="text" name="q" placeholder="Search stacks..."
               class="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
               hx-get="/web/search" hx-trigger="keyup changed delay:300ms" hx-target="#search-results">
        <div id="search-results" class="mt-4 text-left"></div>
    </div>

    <div class="max-w-xl mx-auto text-left">
        <p class="text-sm text-gray-500 mb-2">Get started:</p>
        <pre class="bg-gray-900 border border-gray-800 rounded-lg p-4 text-sm"><code>pip install agentic-stacks-cli
agentic-stacks search "kubernetes"
agentic-stacks pull agentic-stacks/kubernetes-talos@1.0</code></pre>
    </div>
</div>

{% if featured_stacks %}
<div class="mt-8">
    <h2 class="text-2xl font-semibold mb-4">Featured Stacks</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% for stack in featured_stacks %}
        {% include "_stack_card.html" %}
        {% endfor %}
    </div>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: Create stack card partial**

```html
<!-- src/registry/templates/_stack_card.html -->
<a href="/stacks/{{ stack.namespace }}/{{ stack.name }}" class="stack-card block bg-gray-900 border border-gray-800 rounded-lg p-4 hover:no-underline">
    <div class="flex items-start justify-between mb-2">
        <h3 class="font-semibold text-white">{{ stack.namespace }}/{{ stack.name }}</h3>
        <span class="text-xs bg-gray-800 text-gray-400 px-2 py-1 rounded">v{{ stack.version }}</span>
    </div>
    <p class="text-sm text-gray-400">{{ stack.description }}</p>
</a>
```

- [ ] **Step 7: Create search results partial**

```html
<!-- src/registry/templates/_search_results.html -->
{% if stacks %}
<div class="space-y-2">
    {% for stack in stacks %}
    {% include "_stack_card.html" %}
    {% endfor %}
</div>
{% elif query %}
<p class="text-gray-500">No stacks found for "{{ query }}".</p>
{% endif %}
```

- [ ] **Step 8: Create web routes**

```python
# src/registry/routes/web.py
"""Web page routes — server-rendered HTML."""

import json
import pathlib

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db)):
    stacks = db.query(Stack).join(Namespace).order_by(Stack.updated_at.desc()).limit(6).all()
    featured = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            featured.append({
                "namespace": stack.namespace.name,
                "name": stack.name,
                "version": latest.version,
                "description": stack.description,
            })
    return templates.TemplateResponse("home.html", {
        "request": request, "featured_stacks": featured,
    })


@router.get("/stacks", response_class=HTMLResponse)
def stacks_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Stack).join(Namespace)
    if q:
        query = query.filter(Stack.name.contains(q) | Stack.description.contains(q))
    stacks_list = query.order_by(Stack.updated_at.desc()).limit(50).all()
    items = []
    for stack in stacks_list:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": stack.namespace.name,
                "name": stack.name,
                "version": latest.version,
                "description": stack.description,
            })
    return templates.TemplateResponse("stacks.html", {
        "request": request, "stacks": items, "query": q,
    })


@router.get("/web/search", response_class=HTMLResponse)
def search_fragment(request: Request, q: str = "", db: Session = Depends(get_db)):
    """htmx endpoint returning search results as HTML fragment."""
    if not q:
        return HTMLResponse("")
    query = db.query(Stack).join(Namespace).filter(
        Stack.name.contains(q) | Stack.description.contains(q)
    )
    stacks_list = query.order_by(Stack.updated_at.desc()).limit(10).all()
    items = []
    for stack in stacks_list:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": stack.namespace.name,
                "name": stack.name,
                "version": latest.version,
                "description": stack.description,
            })
    return templates.TemplateResponse("_search_results.html", {
        "request": request, "stacks": items, "query": q,
    })
```

- [ ] **Step 9: Create stacks browse template**

```html
<!-- src/registry/templates/stacks.html -->
{% extends "base.html" %}
{% block title %}Browse Stacks — Agentic Stacks{% endblock %}
{% block content %}
<h1 class="text-3xl font-bold mb-6">Browse Stacks</h1>

<div class="mb-6">
    <input type="text" name="q" value="{{ query }}" placeholder="Search stacks..."
           class="w-full max-w-md px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
           hx-get="/stacks" hx-trigger="keyup changed delay:300ms" hx-target="#stacks-list"
           hx-push-url="true" hx-include="this">
</div>

<div id="stacks-list">
    {% if stacks %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% for stack in stacks %}
        {% include "_stack_card.html" %}
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500">No stacks found{% if query %} for "{{ query }}"{% endif %}.</p>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 10: Update app.py to mount web routes and static files**

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


def create_app(rate_limit: str | None = None) -> FastAPI:
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

    return app


app = create_app()
```

- [ ] **Step 11: Run tests**

Run: `pytest tests/test_web_pages.py -v`
Expected: 2 passed

- [ ] **Step 12: Commit**

```bash
git add pyproject.toml src/registry/templates/ src/registry/static/ src/registry/routes/web.py src/registry/app.py tests/test_web_pages.py
git commit -m "feat: website infrastructure — base template, homepage, browse page, htmx search"
```

---

### Task 2: Stack Detail Page

**Files:**
- Create: `src/registry/templates/stack_detail.html`
- Create: `src/registry/markdown.py`
- Modify: `src/registry/routes/web.py` (add stack detail route)
- Modify: `tests/test_web_pages.py` (add tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_web_pages.py`:

```python
import json
from registry.models import Namespace, Stack, StackVersion


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
```

- [ ] **Step 2: Create markdown utility**

```python
# src/registry/markdown.py
"""Markdown rendering utility."""

import mistune


_renderer = mistune.create_markdown(escape=False)


def render_markdown(text: str) -> str:
    """Render markdown text to HTML."""
    if not text:
        return ""
    return _renderer(text)
```

- [ ] **Step 3: Create stack detail template**

```html
<!-- src/registry/templates/stack_detail.html -->
{% extends "base.html" %}
{% block title %}{{ namespace }}/{{ stack.name }} — Agentic Stacks{% endblock %}
{% block content %}
<div class="mb-8">
    <div class="flex items-center gap-3 mb-2">
        <a href="/{{ namespace }}" class="text-gray-400 hover:text-emerald-400">{{ namespace }}</a>
        <span class="text-gray-600">/</span>
        <h1 class="text-3xl font-bold">{{ stack.name }}</h1>
        <span class="bg-emerald-900 text-emerald-300 text-sm px-2 py-1 rounded">v{{ version.version }}</span>
    </div>
    <p class="text-gray-400">{{ stack.description }}</p>
</div>

<div class="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-8">
    <p class="text-sm text-gray-500 mb-1">Install:</p>
    <code class="text-emerald-400">agentic-stacks pull {{ namespace }}/{{ stack.name }}@{{ version.version }}</code>
</div>

<!-- Tabs -->
<div class="border-b border-gray-800 mb-6 flex gap-6">
    <button class="tab-active pb-2 text-sm font-medium" onclick="showTab('skills')">Skills</button>
    <button class="pb-2 text-sm font-medium text-gray-500 hover:text-white" onclick="showTab('profiles')">Profiles</button>
    <button class="pb-2 text-sm font-medium text-gray-500 hover:text-white" onclick="showTab('versions')">Versions</button>
    <button class="pb-2 text-sm font-medium text-gray-500 hover:text-white" onclick="showTab('dependencies')">Dependencies</button>
</div>

<!-- Skills Tab -->
<div id="tab-skills" class="tab-content">
    {% if skills %}
    <div class="space-y-3">
        {% for skill in skills %}
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 class="font-semibold text-white">{{ skill.name }}</h3>
            <p class="text-sm text-gray-400">{{ skill.description }}</p>
            {% if skill.name in deprecated_skills %}
            <p class="text-sm text-yellow-500 mt-1">Deprecated — use "{{ deprecated_skills[skill.name] }}" instead</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500">No skills defined.</p>
    {% endif %}
</div>

<!-- Profiles Tab -->
<div id="tab-profiles" class="tab-content hidden">
    {% if profiles.get("categories") %}
    <div class="space-y-2">
        {% for category in profiles.categories %}
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-3">
            <span class="text-white font-medium">{{ category }}</span>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500">No profiles defined.</p>
    {% endif %}
</div>

<!-- Versions Tab -->
<div id="tab-versions" class="tab-content hidden">
    {% for v in all_versions %}
    <div class="bg-gray-900 border border-gray-800 rounded-lg p-3 mb-2 flex justify-between items-center">
        <div>
            <a href="/stacks/{{ namespace }}/{{ stack.name }}/{{ v.version }}" class="text-emerald-400 hover:underline">v{{ v.version }}</a>
            <span class="text-gray-500 text-sm ml-2">{{ v.published_at[:10] if v.published_at else "" }}</span>
        </div>
        <code class="text-xs text-gray-500">{{ v.digest[:20] }}...</code>
    </div>
    {% endfor %}
</div>

<!-- Dependencies Tab -->
<div id="tab-dependencies" class="tab-content hidden">
    {% if depends_on %}
    <div class="space-y-2">
        {% for dep in depends_on %}
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-3">
            <span class="text-white">{{ dep.namespace }}/{{ dep.name }}</span>
            <span class="text-gray-500 text-sm ml-2">{{ dep.version }}</span>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500">No dependencies.</p>
    {% endif %}

    {% if deprecations %}
    <h3 class="text-lg font-semibold mt-6 mb-3 text-yellow-500">Deprecations</h3>
    <div class="space-y-2">
        {% for dep in deprecations %}
        <div class="bg-gray-900 border border-yellow-900 rounded-lg p-3">
            <span class="text-yellow-400">{{ dep.skill }}</span>
            <span class="text-gray-500 text-sm"> — use "{{ dep.replacement }}" instead</span>
            <p class="text-xs text-gray-500 mt-1">Since {{ dep.since }}, removal in {{ dep.removal }}</p>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>

<script>
function showTab(name) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById('tab-' + name).classList.remove('hidden');
    document.querySelectorAll('[onclick^="showTab"]').forEach(el => {
        el.classList.remove('tab-active');
        el.classList.add('text-gray-500');
    });
    event.target.classList.add('tab-active');
    event.target.classList.remove('text-gray-500');
}
</script>
{% endblock %}
```

- [ ] **Step 4: Add stack detail routes to web.py**

Add these routes to `src/registry/routes/web.py`:

```python
from fastapi import HTTPException
from registry.markdown import render_markdown


@router.get("/stacks/{namespace}/{name}", response_class=HTMLResponse)
def stack_detail_page(request: Request, namespace: str, name: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, "Not found")
    latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).first()
    if not latest:
        raise HTTPException(404, "Not found")
    all_versions = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).all()

    skills = json.loads(latest.skills)
    profiles = json.loads(latest.profiles)
    depends_on = json.loads(latest.depends_on)
    deprecations = json.loads(latest.deprecations)
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}

    versions_data = [{"version": v.version, "digest": v.digest,
                       "published_at": v.published_at.isoformat() if v.published_at else ""}
                      for v in all_versions]

    return templates.TemplateResponse("stack_detail.html", {
        "request": request, "namespace": namespace, "stack": stack,
        "version": latest, "skills": skills, "profiles": profiles,
        "depends_on": depends_on, "deprecations": deprecations,
        "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })


@router.get("/stacks/{namespace}/{name}/{version}", response_class=HTMLResponse)
def stack_version_page(request: Request, namespace: str, name: str, version: str,
                       db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, "Not found")
    sv = db.query(StackVersion).filter_by(stack_id=stack.id, version=version).first()
    if not sv:
        raise HTTPException(404, "Not found")
    all_versions = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).all()

    skills = json.loads(sv.skills)
    profiles = json.loads(sv.profiles)
    depends_on = json.loads(sv.depends_on)
    deprecations = json.loads(sv.deprecations)
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}

    versions_data = [{"version": v.version, "digest": v.digest,
                       "published_at": v.published_at.isoformat() if v.published_at else ""}
                      for v in all_versions]

    return templates.TemplateResponse("stack_detail.html", {
        "request": request, "namespace": namespace, "stack": stack,
        "version": sv, "skills": skills, "profiles": profiles,
        "depends_on": depends_on, "deprecations": deprecations,
        "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })
```

Don't forget to add the import at the top of web.py: `import json`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_web_pages.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/registry/markdown.py src/registry/templates/stack_detail.html src/registry/routes/web.py tests/test_web_pages.py
git commit -m "feat: stack detail page with tabs — skills, profiles, versions, dependencies"
```

---

### Task 3: Namespace Page

**Files:**
- Create: `src/registry/templates/namespace.html`
- Modify: `src/registry/routes/web.py` (add namespace route)
- Modify: `tests/test_web_pages.py` (add tests)

- [ ] **Step 1: Write failing test**

Add to `tests/test_web_pages.py`:

```python
def test_namespace_page(client, seeded_db):
    resp = client.get("/agentic-stacks")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "agentic-stacks" in resp.text
    assert "openstack" in resp.text.lower()


def test_namespace_page_not_found(client):
    resp = client.get("/nonexistent-ns")
    assert resp.status_code == 404
```

- [ ] **Step 2: Create namespace template**

```html
<!-- src/registry/templates/namespace.html -->
{% extends "base.html" %}
{% block title %}{{ ns.name }} — Agentic Stacks{% endblock %}
{% block content %}
<div class="mb-8">
    <div class="flex items-center gap-3 mb-2">
        <h1 class="text-3xl font-bold">{{ ns.name }}</h1>
        {% if ns.verified %}
        <span class="bg-emerald-900 text-emerald-300 text-xs px-2 py-1 rounded">Verified</span>
        {% endif %}
    </div>
</div>

{% if stacks %}
<h2 class="text-xl font-semibold mb-4">Stacks ({{ stacks|length }})</h2>
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {% for stack in stacks %}
    {% include "_stack_card.html" %}
    {% endfor %}
</div>
{% else %}
<p class="text-gray-500">No stacks published yet.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Add namespace route to web.py**

Add to `src/registry/routes/web.py`:

```python
@router.get("/{namespace}", response_class=HTMLResponse)
def namespace_page(request: Request, namespace: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stacks = db.query(Stack).filter_by(namespace_id=ns.id).all()
    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": ns.name,
                "name": stack.name,
                "version": latest.version,
                "description": stack.description,
            })
    return templates.TemplateResponse("namespace.html", {
        "request": request, "ns": ns, "stacks": items,
    })
```

IMPORTANT: This catch-all `/{namespace}` route MUST be the last route registered in web.py to avoid conflicts with other routes like `/stacks`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_web_pages.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/registry/templates/namespace.html src/registry/routes/web.py tests/test_web_pages.py
git commit -m "feat: namespace/publisher page"
```

---

### Task 4: Website Integration Test and Verification

**Files:**
- Create: `tests/test_web_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_web_integration.py
"""Integration: register a stack via API, then browse it on the website."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from registry.database import Base, get_db
from registry.app import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
def test_publish_then_browse(mock_orgs, mock_verify, client):
    # 1. Register via API
    resp = client.post("/api/v1/stacks", json={
        "namespace": "agentic-stacks", "name": "openstack-kolla", "version": "1.0.0",
        "description": "OpenStack deployment via kolla-ansible",
        "target": {"software": "openstack", "versions": ["2025.1"]},
        "skills": [{"name": "deploy", "description": "Deploy OpenStack"},
                   {"name": "health-check", "description": "Validate health"}],
        "profiles": {"categories": ["security", "networking", "storage"]},
        "depends_on": [{"name": "openstack-core", "namespace": "agentic-stacks", "version": "^1.0"}],
        "deprecations": [], "requires": {"tools": ["kolla-ansible"]},
        "digest": "sha256:abc123",
        "registry_ref": "ghcr.io/agentic-stacks/openstack-kolla:1.0.0",
    }, headers={"Authorization": "Bearer ghp_test"})
    assert resp.status_code == 201

    # 2. Homepage shows the stack
    resp = client.get("/")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 3. Browse page lists it
    resp = client.get("/stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 4. Search finds it
    resp = client.get("/stacks?q=openstack")
    assert "openstack-kolla" in resp.text

    # 5. Detail page works
    resp = client.get("/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    assert "deploy" in resp.text.lower()
    assert "health-check" in resp.text.lower()
    assert "agentic-stacks pull" in resp.text
    assert "security" in resp.text
    assert "networking" in resp.text

    # 6. Namespace page works
    resp = client.get("/agentic-stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text

    # 7. htmx search fragment
    resp = client.get("/web/search?q=openstack")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: All pass (~130+ total)

- [ ] **Step 3: Manual verification — start server and browse**

Run: `uvicorn registry.app:app --reload --port 8000`
Then open http://localhost:8000 in a browser. Verify:
- Homepage loads with search bar
- `/stacks` shows browse page
- Search works with htmx (live results as you type)

- [ ] **Step 4: Commit**

```bash
git add tests/test_web_integration.py
git commit -m "feat: website integration test — publish then browse"
```
