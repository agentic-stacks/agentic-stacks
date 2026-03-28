# Cloudflare Deployment — Design Specification

**Date:** 2026-03-28
**Status:** Draft
**Author:** Operator + Claude

## Overview

Deploy the Agentic Stacks registry API and website to Cloudflare Workers with D1 as the database. The existing FastAPI app runs on Cloudflare's Python Workers runtime via the ASGI bridge. A database abstraction layer lets the same routes work with both SQLAlchemy (local dev/tests) and D1 (production).

## Architecture

```
Local Dev / Tests              Cloudflare Production
─────────────────              ─────────────────────
FastAPI app                    FastAPI app (same code)
    │                              │
StacksDB interface             StacksDB interface
    │                              │
SQLiteDB (SQLAlchemy)          D1DB (raw SQL via env.DB)
    │                              │
SQLite in-memory/file          Cloudflare D1
```

## What Changes

### Database Abstraction Layer

A `StacksDB` protocol that both implementations satisfy:

```python
class StacksDB:
    async def list_stacks(self, q, namespace, target, sort, page, per_page) -> tuple[list[dict], int]
    async def get_stack(self, namespace, name) -> dict | None
    async def get_stack_version(self, namespace, name, version) -> dict | None
    async def get_latest_version(self, stack_id) -> dict | None
    async def create_namespace(self, name, github_org) -> dict
    async def get_namespace(self, name) -> dict | None
    async def get_namespace_with_stacks(self, name) -> dict | None
    async def create_stack(self, namespace_id, name, description) -> dict
    async def create_stack_version(self, stack_id, version_data) -> dict
    async def get_stack_by_name(self, namespace_id, name) -> dict | None
    async def version_exists(self, stack_id, version) -> bool
```

**`SQLiteDB`** — wraps the existing SQLAlchemy models and sessions. Used for local dev (`uvicorn registry.app:app`) and all tests. No changes to existing test infrastructure.

**`D1DB`** — uses raw SQL via the D1 binding (`env.DB.prepare(...).bind(...).all()`). Used in Cloudflare production. The D1 binding is accessed from `request.scope["env"]` which the ASGI bridge injects.

### Route Refactoring

Routes change from:
```python
def list_stacks(db: Session = Depends(get_db)):
    query = db.query(Stack).join(Namespace)...
```

To:
```python
def list_stacks(db: StacksDB = Depends(get_db)):
    stacks, total = await db.list_stacks(q=q, namespace=namespace, ...)
```

The dependency injection (`get_db`) returns the appropriate implementation based on environment.

### Worker Entry Point

```python
# worker/main.py
from asgi import asgi
from registry.app import create_app

app = create_app(use_d1=True)

async def on_fetch(request, env):
    return await asgi(app, request, env)
```

### D1 Schema

Same tables as the SQLAlchemy models, as raw SQL:

```sql
CREATE TABLE namespaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    github_org TEXT,
    verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE stacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace_id INTEGER NOT NULL REFERENCES namespaces(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE stack_versions (
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

CREATE INDEX idx_namespaces_name ON namespaces(name);
CREATE INDEX idx_stacks_name ON stacks(name);
CREATE INDEX idx_stacks_namespace ON stacks(namespace_id);
CREATE INDEX idx_versions_stack ON stack_versions(stack_id);
```

### Wrangler Configuration

```toml
name = "agentic-stacks"
main = "worker/main.py"
compatibility_date = "2025-12-01"
compatibility_flags = ["python_workers"]

[vars]
ENVIRONMENT = "production"
GITHUB_API_URL = "https://api.github.com"

[[d1_databases]]
binding = "DB"
database_name = "agentic-stacks-registry"
database_id = "<created at deploy time>"
```

### Deploy Workflow

GitHub Actions workflow that deploys on push to main:

```yaml
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          command: deploy
```

## What Stays the Same

- FastAPI app structure and all route logic
- Pydantic schemas (`registry/schemas.py`)
- GitHub auth module (`registry/auth.py`)
- Jinja2 templates (all HTML files)
- Rate limiting (slowapi)
- MCP server (unchanged — connects to the deployed API)
- CLI (unchanged — talks to the API URL)
- All existing tests (use SQLiteDB implementation)

## File Structure

```
src/registry/
├── db.py                    # StacksDB protocol + get_db dependency
├── db_sqlite.py             # SQLAlchemy implementation
├── db_d1.py                 # D1 implementation
├── database.py              # (keep for backwards compat, imports from db_sqlite)
├── models.py                # (keep — used by db_sqlite)
├── routes/
│   ├── stacks.py            # (refactor: use StacksDB instead of raw SQLAlchemy)
│   ├── namespaces.py        # (refactor: use StacksDB)
│   └── web.py               # (refactor: use StacksDB)
├── app.py                   # (modify: accept use_d1 flag)
└── ...                      # (schemas, auth, templates, static — unchanged)

worker/
├── main.py                  # Cloudflare Workers entry point
└── requirements.txt         # Worker-specific deps

migrations/
└── 0001_initial.sql         # D1 schema migration

wrangler.toml                # Cloudflare config

.github/workflows/
├── ci.yml                   # (existing — runs tests)
└── deploy.yml               # Deploy to Cloudflare on push to main
```

## Testing Strategy

- All existing tests continue to work using `SQLiteDB` (the SQLAlchemy implementation)
- New tests for `D1DB` mock the D1 binding
- Integration tests verify both implementations produce the same results
