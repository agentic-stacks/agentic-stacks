# Phase 2: Registry & Website — Design Specification

**Date:** 2026-03-28
**Status:** Draft
**Author:** Operator + Claude

## Overview

Phase 2 adds distribution, a registry API, and a website to the Agentic Stacks platform. Stacks are published as OCI artifacts to GHCR, metadata is indexed by a FastAPI service, and agentic-stacks.com provides both a browsable frontend and API for the CLI and future agent protocol.

Three subsystems, shipped in order:
1. **Distribution** — CLI commands (`publish`, `pull`, `search`, `upgrade`) + OCI packaging + `stacks.lock`
2. **Registry API** — FastAPI service indexing stack metadata, serving search and detail endpoints
3. **Website** — server-rendered frontend (Jinja2 + htmx) on agentic-stacks.com

## Distribution

### Packaging & Publishing

`agentic-stacks publish` does:

1. Reads `stack.yaml` to get name, namespace, version
2. Validates the stack (runs `doctor` checks)
3. Tarballs the stack directory, excluding: `.git/`, `.venv/`, `state/`, `__pycache__/`, `*.pyc`, `.superpowers/`
4. Pushes the tarball as an OCI artifact via ORAS to `ghcr.io/{namespace}/{name}:{version}`
5. Attaches stack metadata as OCI annotations:
   - `dev.agentic-stacks.name`
   - `dev.agentic-stacks.namespace`
   - `dev.agentic-stacks.version`
   - `dev.agentic-stacks.description`
   - `dev.agentic-stacks.skills` (comma-separated skill names)
   - `dev.agentic-stacks.target-software`
   - `dev.agentic-stacks.target-versions` (comma-separated)
6. Registers the stack with the registry API (`POST /api/v1/stacks`)
7. Prints the OCI reference and digest

**OCI reference format:** `ghcr.io/agentic-stacks/openstack:1.3.0`

**Media type:** `application/vnd.agentic-stacks.stack.v1+tar+gzip`

**CLI config** (`~/.config/agentic-stacks/config.yaml`):
```yaml
registry: ghcr.io
default_namespace: agentic-stacks
api_url: https://agentic-stacks.com/api/v1
```

### Pull & Lock

`agentic-stacks pull agentic-stacks/openstack@1.3` does:

1. Queries the registry API for the latest version matching `1.3.x`
2. Downloads the OCI artifact from GHCR via ORAS
3. Verifies the digest matches
4. Extracts to `.stacks/agentic-stacks/openstack/1.3.0/`
5. Reads the stack's `depends_on`, pulls dependencies recursively
6. Writes/updates `stacks.lock`:

```yaml
stacks:
  - name: agentic-stacks/openstack
    version: "1.3.0"
    digest: sha256:abc123def456...
    registry: ghcr.io/agentic-stacks/openstack
  - name: agentic-stacks/base
    version: "1.0.2"
    digest: sha256:789ghi012jkl...
    registry: ghcr.io/agentic-stacks/base
```

`agentic-stacks pull` with no args re-pulls everything in `stacks.lock` at pinned digests.

### Upgrade

`agentic-stacks upgrade openstack` does:

1. Reads current version from `stacks.lock`
2. Queries the API for newer versions within SemVer range
3. Shows config diff (using `agentic_stacks.config_diff`)
4. Reports deprecation warnings from the new version's manifest
5. Updates `stacks.lock` on confirmation

### Search

`agentic-stacks search "kubernetes"` queries the registry API:

```
GET /api/v1/stacks/search?q=kubernetes
```

Returns ranked results with name, namespace, description, latest version, and target software.

## Registry API

### Tech Stack

- **FastAPI** — API framework
- **SQLite** (initially) — metadata storage, migrates to PostgreSQL when needed
- **SQLAlchemy** — ORM
- **Alembic** — database migrations
- **GitHub OAuth** — publisher authentication

### Data Model

**Stack:**
```
id, namespace, name, description, created_at, updated_at
```

**StackVersion:**
```
id, stack_id, version, target_software, target_versions (JSON),
skills (JSON), profiles (JSON), depends_on (JSON), deprecations (JSON),
requires (JSON), digest, registry_ref, published_at
```

**Namespace:**
```
id, name, github_org, verified, created_at
```

### Endpoints

```
GET  /api/v1/stacks                         — list stacks (paginated)
     ?q=query                                — text search
     ?target=kubernetes                      — filter by target software
     ?namespace=agentic-stacks               — filter by namespace
     ?sort=updated|name|downloads            — sort order
     ?page=1&per_page=20                     — pagination

GET  /api/v1/stacks/{namespace}/{name}       — stack detail (latest version)
GET  /api/v1/stacks/{namespace}/{name}/{ver} — specific version detail

POST /api/v1/stacks                          — register/update stack metadata
     Authorization: Bearer <github-token>
     Body: stack manifest metadata + digest + registry_ref

GET  /api/v1/namespaces/{namespace}          — publisher profile + their stacks
```

### Auth Flow

1. Publisher runs `agentic-stacks login` — opens browser for GitHub OAuth
2. CLI stores the token in `~/.config/agentic-stacks/config.yaml`
3. `agentic-stacks publish` uses the token for both GHCR push and API registration
4. API verifies the GitHub identity owns the namespace (matches GitHub org)

### Registration Flow

When `agentic-stacks publish` calls `POST /api/v1/stacks`:

```json
{
  "namespace": "agentic-stacks",
  "name": "openstack",
  "version": "1.3.0",
  "description": "Agent-driven OpenStack deployment on kolla-ansible",
  "target": {"software": "openstack", "versions": ["2024.2", "2025.1"]},
  "skills": [
    {"name": "config-build", "description": "Compiles environment.yml into kolla-ansible globals"},
    {"name": "kolla-deploy", "description": "Wraps kolla-ansible lifecycle"}
  ],
  "profiles": {"categories": ["security", "cloud-type", "networking", "storage", "scale", "features"]},
  "depends_on": [{"name": "base", "namespace": "agentic-stacks", "version": "^1.0"}],
  "deprecations": [],
  "requires": {"tools": ["kolla-ansible"], "python": ">=3.11"},
  "digest": "sha256:abc123...",
  "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
}
```

The API validates, stores, and indexes. If the namespace doesn't exist, it's created and linked to the GitHub identity.

## Website

### Tech Stack

- **FastAPI** — serves both API and HTML
- **Jinja2** — server-rendered templates
- **htmx** — interactivity without a JS framework
- **Tailwind CSS** — styling

### Pages

| Route | Purpose |
|-------|---------|
| `/` | Homepage — search bar, featured stacks, tagline |
| `/stacks` | Browse all stacks, search, filter by target software |
| `/stacks/{namespace}/{name}` | Stack detail — README, skills list, profiles, versions, install command, dependency graph |
| `/stacks/{namespace}/{name}/{version}` | Specific version detail |
| `/{namespace}` | Publisher page — list their stacks |
| `/docs` | Getting started, spec documentation, CLI reference |
| `/login` | GitHub OAuth login for publishers |

### Stack Detail Page

Shows:
- Name, namespace, description, latest version badge
- Install command: `agentic-stacks pull agentic-stacks/openstack@1.3`
- README (rendered from stack's README.md or CLAUDE.md)
- Skills tab — list of skills with descriptions
- Profiles tab — categories and available options
- Versions tab — version history with changelogs
- Dependencies tab — what this stack depends on
- Deprecations — any deprecated skills with migration pointers

### Search

Search bar on homepage and `/stacks` page. Uses htmx for live results:
```html
<input hx-get="/api/v1/stacks?q=" hx-trigger="keyup changed delay:300ms" hx-target="#results">
```

## Phased Delivery Within Phase 2

### Phase 2a: Distribution CLI
- `agentic-stacks publish` — package + push to OCI + register with API
- `agentic-stacks pull` — download from OCI + extract + lock file
- `agentic-stacks upgrade` — check for newer versions + diff + update lock
- `agentic-stacks search` — query API
- `agentic-stacks login` — GitHub OAuth
- `stacks.lock` format and resolution
- CLI config (`~/.config/agentic-stacks/config.yaml`)

### Phase 2b: Registry API
- FastAPI application with SQLite
- All endpoints listed above
- GitHub OAuth integration
- Stack registration and metadata indexing
- Text search across name, description, skills, target

### Phase 2c: Website
- Jinja2 templates + htmx + Tailwind
- All pages listed above
- Stack detail pages with tabs
- Search with live results
- Publisher profiles
- Documentation pages

## Dependencies

### Phase 2a (CLI additions)
- **oras-py** or subprocess calls to `oras` CLI — OCI push/pull
- **httpx** — API client for registry calls

### Phase 2b (API)
- **FastAPI** + **uvicorn** — web framework + server
- **SQLAlchemy** — ORM
- **Alembic** — migrations
- **authlib** — GitHub OAuth

### Phase 2c (Website)
- **Jinja2** — templates (comes with FastAPI)
- **htmx** — client-side interactivity (CDN, no build step)
- **Tailwind CSS** — styling (CDN or standalone CLI)
- **markdown2** or **mistune** — render README files

## Open Questions

1. **Hosting for the API/website** — Fly.io, Railway, a VPS, or your own infra? Affects deployment approach.
2. **GHCR auth for pull** — public stacks should be pullable without auth. Need to ensure GHCR packages are published as public.
3. **Rate limiting** — the API will need rate limiting once public. Add in 2b or defer?
4. **Cosign signing** — include in 2a or defer to a later hardening pass?
