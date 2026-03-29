# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Agentic Stacks — a platform for packaging, distributing, and discovering domain expertise for AI agents. A "stack" is a git repo containing skills (markdown that teaches an agent how to operate in a domain), plus metadata. The agent reads the skills and guides users through complex tasks like deploying OpenStack, bootstrapping Kubernetes, etc.

## Commands

```bash
# Install (editable, all extras)
pip install -e ".[dev,local,mcp]"

# Run all tests
pytest -v --tb=short

# Run a single test file or test
pytest tests/test_profiles.py -v
pytest tests/test_profiles.py::test_function_name -v

# Local dev server (SQLite-backed registry)
uvicorn registry.local:app --reload

# CLI
agentic-stacks --help
```

## Architecture

Four packages under `src/`, built with hatchling:

**`agentic_stacks`** — Core runtime library. Manifest parsing (`manifest.py`), profile loading + deep merge (`profiles.py`), environment validation (`environments.py`), config diffing (`config_diff.py`), state store (`state_store.py`), approval gates (`approval.py`).

**`agentic_stacks_cli`** — Click-based CLI. Key commands: `init` (scaffold stack or project), `pull` (git clone stack into `.stacks/`), `publish` (register stack with registry API), `search`, `doctor`, `login`. Config at `~/.config/agentic-stacks/config.yaml`.

**`registry`** — FastAPI web service (API + Jinja2 HTML pages). Routes in `routes/`: stacks.py, namespaces.py, web.py. Auth via GitHub OAuth token verification. Coming soon mode controlled by `COMING_SOON` env var (bypass with `?preview=1`).

**`agentic_stacks_mcp`** — MCP server exposing registry as agent-callable tools.

## Distribution Model

Stacks are git repos. No OCI/ORAS.

- `init owner/name [path]` creates a user project with `stacks.lock`, `.gitignore`, and a `CLAUDE.md` pointing to `.stacks/*/CLAUDE.md`
- `pull` clones a stack's GitHub repo into `.stacks/<name>/` (or `git pull` to update)
- `pull <ref>` adds a new stack to the project and updates `stacks.lock`
- `list` shows all stacks in the current project and their pull status
- `remove <ref>` removes a stack from `stacks.lock` and deletes its `.stacks/` directory
- `publish` registers the stack's repo URL + metadata with the registry API
- `search` queries the registry API
- `create owner/name [path]` scaffolds a new stack (for stack authors)

Default GitHub org is `agentic-stacks`. `pull openstack-kolla` clones from `github.com/agentic-stacks/openstack-kolla`.

## User Projects

Projects can compose multiple stacks for cross-domain expertise. For example, combining a hardware stack with a platform stack:

```bash
agentic-stacks init agentic-stacks/openstack-kolla my-deployment
cd my-deployment
agentic-stacks pull dell-hardware    # add a second stack
agentic-stacks list                  # see all stacks
```

This creates:

```
my-deployment/
├── .stacks/              # pulled stack repos (gitignored)
│   ├── openstack-kolla/  # platform expertise
│   └── dell-hardware/    # hardware expertise
├── CLAUDE.md             # points agent to .stacks/*/CLAUDE.md
├── stacks.lock           # pinned stack references
├── .gitignore
└── ... (whatever the agent creates — native tool configs)
```

The agent reads each stack's CLAUDE.md (via `.stacks/*/CLAUDE.md`) and combines their expertise. The output is native format for whatever tools the stacks wrap.

## Database Layer

The registry uses a **protocol-based DB abstraction** (`db.py` defines `StacksDB` Protocol):

- `db_sqlite.py` — SQLAlchemy ORM, used for local dev and all tests
- `db_d1.py` — Cloudflare D1 via Pyodide JS interop, used in production
- `db_stub.py` — Empty stub for bootstrap deploys

All StacksDB methods are async. Route handlers must `await` every DB call. Tests that call DB methods directly use `_run()` helper with `asyncio.new_event_loop()`.

**Two schemas must be kept in sync**: SQLAlchemy models in `registry/models.py` and raw SQL in `migrations/0001_initial.sql`.

## Cloudflare Workers Deployment

Production runs on Cloudflare Python Workers via ASGI bridge.

- `wrangler.toml` — config with D1 binding (`DB`), `COMING_SOON=true`
- `src/main.py` — Worker entry point. Lazy imports, D1 binding set per-request.

**Workers constraints**: no threads, all route handlers must be async, heavy imports must be lazy, D1 returns JS objects needing `to_py()` conversion, D1 operations return PyodideFuture that must be awaited.

## Testing

pytest with pytest-asyncio. Tests in `tests/`, fixtures in `tests/fixtures/`. All tests use SQLite in-memory. CI runs on Python 3.12 and 3.13.
