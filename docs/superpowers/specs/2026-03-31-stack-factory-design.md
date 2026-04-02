# Stack Factory Design

**Date:** 2026-03-31
**Repo:** `agentic-stacks/stack-factory`
**Status:** Approved

## Overview

An automated pipeline for creating agentic stacks at scale. The factory scaffolds new stack repos from a queue, then a local Claude Code session fills them with researched, production-quality content following the authoring guide.

Two-phase architecture:
1. **Scaffolding (GitHub Actions / CLI)** — cheap automation that creates repos, manages the queue, handles community intake
2. **Authoring (local Claude Code)** — expensive LLM work runs on the maintainer's machine using their Max plan

## Repository Structure

```
agentic-stacks/stack-factory/
├── README.md
├── pyproject.toml                # CLI package (click-based)
├── queue.yaml                    # Source of truth: stack queue with status
├── factory/
│   ├── __init__.py
│   ├── cli.py                    # Click CLI: scaffold, status, approve, list
│   ├── queue.py                  # Queue CRUD (read/write queue.yaml)
│   ├── scaffold.py               # Scaffold logic: agentic-stacks create + enrichment
│   └── github.py                 # gh CLI wrappers: repo create, issue management
├── skill/
│   ├── CLAUDE.md                 # Authoring skill — guides Claude Code sessions
│   └── research-plan.md          # Template documentation for research plans
├── templates/
│   └── research-plan.yaml.j2     # Jinja2 template for per-stack research plans
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── stack-request.yml     # Community request form
│   └── workflows/
│       ├── intake.yml            # Issue approved → add to queue.yaml
│       └── scaffold.yml          # Queue item ready → scaffold repo
└── tests/
```

## Queue Format

`queue.yaml` is the source of truth for all stack work:

```yaml
stacks:
  - name: prometheus-grafana
    owner: agentic-stacks
    description: "Monitoring stack — Prometheus metrics + Grafana dashboards"
    target_software:          # List of target software names
      - prometheus
      - grafana
    status: pending          # pending | scaffolded | in-progress | complete
    issue: null              # GitHub issue number (if from community request)
    repo: null               # Set after scaffold creates the repo
    created: 2026-03-31
```

### Initial Queue

Pre-loaded from the TODO.md "New Stacks to Author" list (minus frr, already added):

| Name | Target Software |
|---|---|
| ansible | Ansible fleet automation |
| terraform | Terraform IaC provisioning |
| proxmox | Proxmox hypervisor management |
| linux | Linux OS operations (systemd, networking, storage, tuning) |
| minio | MinIO S3-compatible object storage |
| zfs | ZFS storage management |
| prometheus-grafana | Prometheus + Grafana monitoring |
| loki | Grafana Loki log aggregation |
| vault | HashiCorp Vault secrets management |
| keycloak | Keycloak identity/SSO |
| opnsense | OPNsense network firewall/router |

## CLI Commands

```bash
# Queue management
factory list                        # Show queue with status
factory add <name> --target <sw>    # Add to queue manually
factory approve <issue-number>      # Move approved issue into queue

# Scaffolding
factory scaffold <name>             # Scaffold a single stack repo
factory scaffold --next             # Scaffold the next pending item

# Status
factory status <name>               # Show details for a stack
factory complete <name>             # Mark stack as complete
```

### What `factory scaffold <name>` Does

1. Reads queue entry for the named stack
2. Runs `agentic-stacks create agentic-stacks/<name>` in a temp directory
3. Generates `.factory/research-plan.yaml` from the Jinja2 template — target software, doc URLs to try, suggested skill phases
4. Copies the authoring skill into the scaffolded repo as `.factory/CLAUDE.md`, interpolating the stack name and target software into the template
5. Runs `gh repo create agentic-stacks/<name> --public --source .`
6. Pushes initial commit
7. Updates `queue.yaml`: status → `scaffolded`, sets `repo` field

### Local Authoring Workflow

```bash
gh repo clone agentic-stacks/prometheus-grafana
cd prometheus-grafana
claude   # .factory/CLAUDE.md guides the session
```

## Authoring Skill (`.factory/CLAUDE.md`)

The skill that guides Claude Code when running locally in a scaffolded repo:

```markdown
# Stack Factory — Authoring Agent

## Identity
You are building the {name} agentic stack. Your job is to research
the target software's official documentation and generate a complete,
production-quality stack following the authoring guide.

## Research Plan
Read `.factory/research-plan.yaml` for target software, doc URLs,
and version targets.

## Workflow
1. Discover docs — fetch llms.txt, sitemap.xml, GitHub repo for
   the target software. Find the two most recent major versions.
2. Design skill hierarchy — based on what the software does,
   propose skill phases (foundation/deploy/operations/diagnose/reference).
   Present to operator for approval before proceeding.
3. Research & generate skills — for each skill, fetch the relevant
   doc pages, extract exact commands/configs/warnings, write the skill
   content following authoring guide templates.
4. Generate CLAUDE.md — identity, critical rules, routing table,
   workflows. Based on actual skills created.
5. Generate stack.yaml — manifest with all skills, target versions,
   required tools.
6. Validate — run the authoring guide checklist. No placeholders,
   all paths resolve, all commands are exact.

## Rules
- Every command must come from official docs — never reconstruct from memory
- Cover current major version AND previous major version
- Note version-specific differences explicitly
- Use authoring guide templates for consistent structure
- Ask the operator when you hit a design decision
```

## Research Plan Template

Generated per stack during scaffolding (`.factory/research-plan.yaml`):

```yaml
name: prometheus-grafana
target_software:
  - name: prometheus
    docs_url: https://prometheus.io/docs
    github: prometheus/prometheus
  - name: grafana
    docs_url: https://grafana.com/docs/grafana/latest
    github: grafana/grafana
suggested_phases:
  - foundation
  - deploy
  - operations
  - diagnose
  - reference
notes: "Combined monitoring stack — cover both tools and their integration"
```

The research plan is a starting point — Claude Code adjusts based on what it discovers during research.

## GitHub Actions & Community Intake

### Issue Template (`stack-request.yml`)

Fields: stack name (required), target software (required), description of what the stack should cover (required). Auto-labeled `stack-request`.

### Intake Workflow (`intake.yml`)

- **Trigger:** maintainer adds the `approved` label to a `stack-request` issue
- **Action:** runs `factory approve <issue-number>` — reads issue fields, adds entry to `queue.yaml`, commits, comments on issue confirming it's queued

### Scaffold Workflow (`scaffold.yml`)

- **Trigger:** manual `workflow_dispatch` with stack name input
- **Action:** runs `factory scaffold <name>`, comments on linked issue with repo URL

Both workflows are lightweight — no LLM calls, just Python CLI + `gh` commands.

## End-to-End Flow

### Path 1: Maintainer-Driven (Initial Batch)

```
queue.yaml (pre-loaded with 11 stacks)
  → factory scaffold prometheus-grafana
  → repo created at agentic-stacks/prometheus-grafana
  → maintainer clones it, runs claude
  → Claude Code follows .factory/CLAUDE.md
  → researches docs, generates skills, validates
  → maintainer reviews, commits, pushes
  → registry hourly sync picks it up automatically
```

### Path 2: Community Request

```
User opens issue using template
  → maintainer adds "approved" label
  → intake.yml adds to queue.yaml
  → maintainer runs scaffold workflow (or factory scaffold locally)
  → same authoring flow as above
```

### State Transitions

```
pending → scaffolded → in-progress → complete
   ↑          ↑            ↑           ↑
 approve   scaffold    maintainer    maintainer
  issue     action    starts claude   finishes
```

## Version Coverage

Each stack covers the **two most recent major version lines** of the target software (e.g., Prometheus 2.x and 3.x, Grafana 10.x and 11.x). The Claude Code research phase discovers what these are and documents version-specific differences within the skill content.

## Out of Scope

- No automatic content generation in CI — all LLM work runs locally
- No auto-merge or auto-publish — maintainer reviews everything
- No multi-branch version strategy — single branch covers both major versions in skill content
- No dependency ordering between stacks in the queue — each is independent
