# Git-Backed Registry Design

## Overview

A Homebrew-style git-backed registry where a central repo (`github.com/agentic-stacks/registry`) holds formula YAML files — one per stack. Each formula points to the stack's source repo with metadata. The CLI clones/caches the registry repo locally for search and pull operations. The existing D1 database and API remain as a read cache for the website.

## Registry Repo Structure

```
github.com/agentic-stacks/registry/
├── stacks/
│   ├── agentic-stacks/
│   │   ├── openstack-kolla.yaml
│   │   ├── kubernetes-talos.yaml
│   │   └── dell-hardware.yaml
│   └── <third-party-owner>/
│       └── <stack-name>.yaml
├── .github/
│   └── workflows/
│       └── sync.yml
├── scripts/
│   └── sync_formulas.py
└── README.md
```

Formulas are scoped by owner (`stacks/<owner>/<name>.yaml`) to avoid name collisions across orgs and mirror the CLI's `owner/name` convention.

## Formula Format

Each formula is a YAML file derived from the stack's `stack.yaml` manifest, with added distribution fields (`tag`, `sha256`).

```yaml
name: openstack-kolla
owner: agentic-stacks
version: "0.1.0"
repository: https://github.com/agentic-stacks/openstack-kolla
tag: v0.1.0
sha256: ""
description: "Agent-driven OpenStack deployment on kolla-ansible"
target:
  software: openstack
  versions: ["2025.1", "2025.2"]
skills:
  - name: config-build
    description: "Build globals.yml, inventory, and service configs"
  - name: deploy
    description: "Full kolla-ansible deploy lifecycle"
  - name: health-check
    description: "Validate environment health"
  - name: diagnose
    description: "Systematic troubleshooting"
  - name: day-two
    description: "Day-two operations"
  - name: decision-guides
    description: "Choose between networking and storage options"
  - name: compatibility
    description: "Version compatibility matrix"
  - name: known-issues
    description: "Known bugs and workarounds"
depends_on: []
requires:
  tools:
    - kolla-ansible
    - openstack
    - docker
  python: ">=3.11"
```

Fields:

| Field | Source | Description |
|---|---|---|
| `name` | stack.yaml | Stack name |
| `owner` | stack.yaml | Stack owner (replaces `namespace`) |
| `version` | stack.yaml | Semantic version |
| `repository` | stack.yaml | GitHub repo URL |
| `tag` | Derived | Git tag for this version (e.g., `v0.1.0`) |
| `sha256` | Computed | SHA256 of the GitHub archive tarball (empty until first release) |
| `description` | stack.yaml | One-line description |
| `target` | stack.yaml | Target software and supported versions |
| `skills` | stack.yaml | Skill list (name + description only, no `entry` paths) |
| `depends_on` | stack.yaml | Stack dependencies |
| `requires` | stack.yaml | Tool and Python requirements |

Formula omits fields only needed inside the stack (skill `entry` paths, `profiles`, `project.structure`, `environment_schema`, `deprecations`) — those are read from the stack itself after pull.

## Auto-Sync: GitHub Action

A GitHub Action in the registry repo scans the `agentic-stacks` org and generates/updates formulas automatically.

### Workflow: `.github/workflows/sync.yml`

- **Triggers:** Hourly schedule + manual `workflow_dispatch`
- **Steps:**
  1. Check out the registry repo
  2. Run `scripts/sync_formulas.py` with a GitHub token
  3. If any formulas changed, commit and push

### Sync Script: `scripts/sync_formulas.py`

Plain Python (PyYAML + GitHub CLI or GitHub API via httpx). No external dependencies beyond what's available in GitHub Actions runners.

**Logic:**
1. List all repos in the `agentic-stacks` org via GitHub API
2. For each repo, check if `stack.yaml` exists at the repo root
3. If it exists, fetch its contents and parse
4. Generate a formula YAML from the manifest fields
5. Write to `stacks/agentic-stacks/<name>.yaml`
6. If the formula differs from what's on disk, it gets committed

**What the script does NOT do:**
- Manage third-party stacks (those come via PR)
- Delete formulas for removed repos (manual cleanup)
- Compute `sha256` (requires downloading the archive, done separately)

## CLI Integration

### Local Registry Cache

The CLI clones the registry repo to `~/.config/agentic-stacks/registry/` on first use. Subsequent calls run `git fetch && git reset --hard origin/main` to update.

**New module: `src/agentic_stacks_cli/registry_repo.py`**

```python
# Key functions:
ensure_registry()          # Clone or update the local cache
load_formula(owner, name)  # Read a single formula
list_formulas()            # List all formulas
search_formulas(query)     # Search by name, description, target, skills
write_formula(formula)     # Write a formula YAML (for publish)
```

### Command Changes

**`pull`** — When pulling a stack by reference:
1. `ensure_registry()` to update the local cache
2. Look up the formula in `stacks/<owner>/<name>.yaml`
3. Git clone the `repository` URL into `.stacks/<name>/`
4. Update `stacks.lock`

When pulling without args (from `stacks.lock`), behavior unchanged — reads lock entries directly.

**`search`** — Searches local formulas instead of calling the API:
1. `ensure_registry()` to update the local cache
2. `search_formulas(query)` matching against name, description, target software, and skill names
3. Display results

**`publish`** — For third-party stacks:
1. Read `stack.yaml` from the current directory
2. Generate a formula YAML
3. Fork the registry repo (or use existing fork)
4. Write the formula to `stacks/<owner>/<name>.yaml`
5. Open a PR to `agentic-stacks/registry`

For org stacks, `publish` is unnecessary — the auto-sync handles it. But running `publish` from an org stack could trigger an immediate sync or just confirm the formula is up to date.

### Config Changes

**`~/.config/agentic-stacks/config.yaml`:**
```yaml
registry_repo: https://github.com/agentic-stacks/registry
api_url: https://agentic-stacks.ajmesserli.workers.dev/api/v1  # for website cache
token: ghp_...
```

`registry_repo` replaces the OCI registry URL as the primary distribution config.

## Website / DB Cache

The existing D1 database and FastAPI API remain for the website (`agentic-stacks.com`). A separate GitHub Action (or the same sync workflow) pushes formula data to the API after updating formulas. This is a separate concern and not part of the initial implementation.

**Future sync flow:**
1. Sync action updates formulas in the registry repo
2. After commit, a second step calls `POST /api/v1/stacks` for each changed formula
3. Website reads from D1 as before

The DB schema needs one addition: a `repository` column on the `stacks` table to store the source repo URL.

## What Changes vs. Current State

| Component | Current | After |
|---|---|---|
| Source of truth | D1 database | Registry repo (git) |
| CLI search | Calls API | Reads local formulas |
| CLI pull | Git clones from hardcoded GitHub URL | Git clones from formula's `repository` field |
| CLI publish | POSTs to API | Writes formula + opens PR |
| Website | Reads D1 | Reads D1 (synced from registry repo) |
| `namespace` field | Being replaced by `owner` | Fully replaced by `owner` |

## Implementation Order

1. **Create the registry repo** with formulas for the 3 existing stacks (openstack-kolla, kubernetes-talos, dell-hardware)
2. **Add the sync script and GitHub Action** to auto-detect stacks in the org
3. **Build `registry_repo.py`** — the local cache reader/writer
4. **Rewrite `search`** to use local formulas
5. **Update `pull`** to resolve stacks via formulas
6. **Update `publish`** to generate formulas and open PRs
7. **Add `repository` column to DB** and wire up website sync (separate PR)
