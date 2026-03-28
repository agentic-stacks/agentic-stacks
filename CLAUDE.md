# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Agentic Stacks — a platform for packaging, versioning, distributing, and discovering composed domain expertise for AI agents. A "stack" bundles skills (markdown knowledge), profiles (composable YAML configs), automation, and environment schemas. Three layers shipped incrementally: spec+runtime, registry+website (agentic-stacks.com), agent discovery (MCP server).

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

# Build distributable package
pip install build && python -m build

# CLI
agentic-stacks --help

# MCP server
agentic-stacks-mcp --help
```

## Architecture

Four packages under `src/`, built with hatchling:

**`agentic_stacks`** — Core runtime library. Profile loading + ordered deep merge with enforced key protection (`profiles.py`), manifest parsing (`manifest.py`), environment validation against JSON Schema (`environments.py`), config diffing (`config_diff.py`), append-only state store (`state_store.py`), approval gates with three tiers: auto/auto-notify/human-approve (`approval.py`).

**`agentic_stacks_cli`** — Click-based CLI. Subcommands in `commands/`: init, doctor, validate, login, publish, pull, search, upgrade. Uses `api_client.py` (httpx) for registry API and `oci.py` for ORAS-based OCI artifact push/pull. Config at `~/.config/agentic-stacks/config.json`.

**`registry`** — FastAPI web service (API + Jinja2 HTML pages). Routes in `routes/`: stacks.py, namespaces.py, web.py. Auth via GitHub OAuth token verification (`auth.py`). Rate limiting via slowapi (disabled on Workers).

**`agentic_stacks_mcp`** — MCP server exposing registry as agent-callable tools (search_stacks, get_stack_info, get_skill, pull_stack). Handlers are separated from MCP decorators for testability.

## Database Layer

The registry uses a **protocol-based DB abstraction** (`db.py` defines `StacksDB` Protocol):

- `db_sqlite.py` — SQLAlchemy ORM implementation, used for local dev and all tests
- `db_d1.py` — Cloudflare D1 via Pyodide JS interop, used in production
- `db_stub.py` — Empty stub for bootstrap deploys

`app.py` has `create_app(db_factory=...)` factory; routes get DB via `Depends(get_db)`. `create_sqlite_app()` wires SQLite. `local.py` is the uvicorn entry point.

**Two schemas must be kept in sync**: SQLAlchemy models in `registry/models.py` and raw SQL in `migrations/0001_initial.sql` (for D1).

## Cloudflare Workers Deployment

Production runs on Cloudflare Python Workers via ASGI bridge.

- `wrangler.toml` — config with D1 binding (`DB`)
- `src/main.py` — Worker entry point. `Default(WorkerEntrypoint)` lazily creates FastAPI app with D1DB. The D1 binding is a global set per-request before `asgi.fetch()`.

**Workers constraints**: no threads (no slowapi, no sync generators), all route handlers must be async, heavy imports must be lazy (not at module level), D1 returns JS objects needing `to_py()` conversion.

CI deploys automatically on push to main (`.github/workflows/deploy.yml`).

## Operator Projects

`agentic-stacks init --from <stack-path>` scaffolds an operator project that extends a base stack. The operator project has `environments/`, `state/`, and `stacks.lock` but no `skills/` or `profiles/` — those come from the parent stack in `.stacks/`.

The stack's `project` field in `stack.yaml` declares what each environment directory should contain (`config.yml`, `inventory/`, `files/`, `secrets/`, etc.). The generated `CLAUDE.md` wires the agent to the stack's skills.

The agent reads the parent stack's skills to know the domain and the operator's config to know specifics. The operator works with the agent to build out their deployment iteratively.

`doctor` detects operator projects (via the `extends` field) and validates: parent stack is pulled, environments exist, state directory present.

## Testing

pytest with pytest-asyncio. Tests in `tests/`, fixtures in `tests/fixtures/sample-stack/` and `tests/fixtures/parent-stack/`. All tests use SQLite in-memory — no D1 in tests. CI runs on Python 3.12 and 3.13.
