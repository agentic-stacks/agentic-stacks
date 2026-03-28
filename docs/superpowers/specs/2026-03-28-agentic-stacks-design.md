# Agentic Stacks — Design Specification

**Date:** 2026-03-28
**Status:** Draft
**Author:** Operator + Claude

## Overview

Agentic Stacks is a platform for packaging, versioning, distributing, and discovering **composed domain expertise** for AI agents and humans. A "stack" is a bundle of skills (markdown knowledge), profiles (composable YAML configs), automation (scripts/code), and environment schemas that together give an agent deep competence in a domain — deploying OpenStack, bootstrapping Kubernetes, standing up a Rails app, building a data pipeline.

The platform has three layers, shipped incrementally:

1. **Stack Specification + Thin Runtime** — the standard for what a stack is and how it works
2. **Registry & Website (agentic-stacks.com)** — discover, browse, and pull versioned stacks
3. **Agent Discovery Protocol** — an MCP server that lets agents find and pull stacks at runtime

The core insight: nobody owns the "composed capability pack" layer for AI agents. There are protocol layers (MCP, A2A), single-tool registries (Smithery, Composio), and infrastructure package managers (Helm, Ansible Galaxy). But there is no cross-domain, versioned, agent-queryable system for bundling domain expertise. Agentic Stacks fills that gap.

### Goals

- Define a universal format for packaging AI agent domain expertise
- Provide a thin, stable runtime for the mechanical parts (profile merging, state tracking, approval gates)
- Build a registry where stacks are versioned, signed, and discoverable by both humans and agents
- Enable agents to discover and acquire capabilities at runtime — the "I know kung fu" moment
- Ship incrementally: spec first (proven with OpenStack + Kubernetes stacks), registry second, agent protocol third

### Non-Goals

- Replacing MCP or any protocol layer — stacks are consumed alongside MCP, not instead of it
- Building a hosted execution environment — stacks run locally, the platform is distribution
- Prescribing which AI model to use — stacks are model-agnostic, skills are the durable layer
- Building a marketplace with monetization (yet) — open ecosystem first

## What Is a Stack

A stack is a directory with a standard structure and a `stack.yaml` manifest:

```
my-stack/
├── stack.yaml              # Manifest (identity, version, deps, contents)
├── skills/                 # Markdown brain — teaches the agent what to do
│   ├── deploy/
│   ├── health-check/
│   ├── diagnose/
│   └── ...
├── profiles/               # Composable YAML building blocks
│   ├── networking/
│   ├── storage/
│   ├── security/
│   ├── scale/
│   └── features/
├── environments/           # Declarative intent + schema
│   ├── _schema.yml
│   └── example/
│       └── environment.yml
├── overrides/              # Optional layered config overrides
├── src/                    # Automation code (Python, scripts — the hands)
└── CLAUDE.md               # Agent entry point and project context
```

This structure is validated by the existing agentic-openstack and agentic-kubernetes projects, which independently converged on this pattern.

### The Manifest: `stack.yaml`

```yaml
name: openstack
namespace: littleknifelabs
version: "1.3.0"
description: "Agent-driven OpenStack cloud deployment and operations on kolla-ansible"

target:
  software: openstack
  versions: ["2024.2", "2025.1"]

skills:
  - name: config-build
    entry: skills/config-build/
    description: "Compiles environment.yml into kolla-ansible globals and overrides"
  - name: kolla-deploy
    entry: skills/deploy/
    description: "Wraps kolla-ansible lifecycle: prechecks, pull, deploy, reconfigure"
  - name: health-check
    entry: skills/health-check/
    description: "Validates environment health: APIs, agents, containers, resources"
  - name: diagnose
    entry: skills/diagnose/
    description: "Root cause analysis from symptoms: logs, configs, container state"

profiles:
  categories: [security, cloud-type, networking, storage, scale, features]
  path: profiles/
  merge_order: "security first (enforced), then declared order"

environment_schema: environments/_schema.yml

depends_on:
  - name: base
    namespace: agentic-stacks
    version: "^1.0"

requires:
  tools: [kolla-ansible, openstack-cli, sops]
  python: ">=3.11"

deprecations:
  - skill: deploy-with-kolla-cli
    since: "1.2.0"
    removal: "2.0.0"
    replacement: kolla-deploy
    reason: "kolla-cli deprecated upstream, kolla-deploy skill wraps kolla-ansible directly"
```

### What's Universal Across All Stacks

| Concern | Pattern | Varies per stack? |
|---------|---------|-------------------|
| Skills (markdown) | `skills/` directory, each skill a folder with markdown files | Content varies, structure is universal |
| Profiles | `profiles/` with category subdirectories, composable YAML | Categories and values vary, merge mechanics are universal |
| Environments | `environments/` with schema + declarations | Schema varies, the concept is universal |
| Profile merge order | Security first (enforced), then category order | Category names vary, ordering rules are universal |
| Action flow | Intent → Plan → Approve → Execute → Verify | Universal |
| Approval gates | auto / auto-notify / human-approve per environment | Universal |
| State tracking | Append-only log of actions | Universal |
| Skill composition | Skills chain together for complex operations | Universal |

The only thing that varies between stacks is **what tools the automation drives** and **what the profiles contain**. The shape is the same.

## Architecture

### Layer 1: Stack Specification + Thin Runtime

**The Spec** defines:
- `stack.yaml` manifest format and required fields
- Directory conventions (`skills/`, `profiles/`, `environments/`)
- Profile merge rules: load by category, merge in declared order, respect `enforced: true` keys
- Environment declaration schema pattern
- Skill composition patterns
- Action flow contract (intent → plan → approve → execute → verify)

**The Thin Runtime** (`agentic_stacks` Python package) provides:
- Profile loader + ordered deep merge with enforced key protection
- JSON Schema validation for environments and manifests
- Config diff engine (show what changes before applying)
- Append-only state store (what happened, when, by whom, outcome)
- Approval gate engine (auto / auto-notify / human-approve)
- Stack manifest parser and validator

Design principle: **small API surface, changes rarely.** The runtime handles the mechanical parts that are identical across every stack. Stack-specific logic stays in the stack's own `src/` directory. Stacks can use the runtime or implement the spec themselves — the runtime is a convenience, not a requirement.

### Layer 2: Registry & Website (agentic-stacks.com)

**Distribution** uses OCI registries (GHCR as primary):
- Stacks are packaged as OCI artifacts via ORAS
- Content-addressable (SHA256 digests) for integrity
- Signed via Cosign/Sigstore for provenance
- Immutable once published — version 1.3.0 can never change

**The Website** provides:
- Browse and search stacks by domain, target software, keywords
- Stack detail pages: README, skill list, profile categories, version history, dependency graph
- Publisher profiles (namespace pages)
- Install counts, version badge, compatibility matrix

**The CLI** (`astack`):
- `astack init --stack namespace/name@version` — scaffold a new project from a stack
- `astack pull namespace/name@version` — download a stack into `.stacks/`
- `astack upgrade name` — upgrade with deprecation warnings and diff
- `astack doctor` — validate stack.yaml, profiles, schemas, check for deprecated skills
- `astack publish` — package and push to registry
- `astack search "query"` — search the registry

**Lock file** (`stacks.lock`):
```yaml
stacks:
  - name: littleknifelabs/openstack
    version: "1.3.0"
    digest: sha256:abc123def456...
  - name: agentic-stacks/base
    version: "1.0.2"
    digest: sha256:789ghi012jkl...
```

Git-committable. Guarantees reproducible builds. `astack pull` without a version uses the lock file.

### Layer 3: Agent Discovery Protocol

An MCP server that exposes the registry as tools any AI agent can call:

**Tools:**
- `search_stacks(query)` — semantic search over stack descriptions and skills. Returns ranked results.
- `get_stack_info(name, version)` — full manifest, skill list, profiles, dependencies, trust level.
- `get_skill(stack, skill_name)` — returns the full markdown content of a specific skill.
- `pull_stack(name, version, path)` — downloads the stack locally. Returns the path.

**Agent consumption flow:**
1. Agent encounters a task it doesn't know how to do ("deploy an OpenStack cloud")
2. Calls `search_stacks("openstack deployment")` → gets `littleknifelabs/openstack@2.1`
3. Calls `get_stack_info` to evaluate: reads skills, profiles, requirements
4. Asks human for approval (unless trust policy allows auto-pull for verified stacks)
5. Calls `pull_stack`, loads skills into context
6. Agent now has domain expertise — "I know OpenStack"

**Trust tiers** control agent autonomy:
- **Verified** — signed by known publisher. Agents with matching trust policy can auto-pull.
- **Community** — published by community members. Agents require human approval before pulling.
- **Experimental** — unreviewed. Always requires explicit human approval. Flagged in UI and API.

## Versioning

### Dual Version Model

Every stack carries two version concepts:
- `version` — the stack's own version. Strict SemVer 2.0. Immutable once published.
- `target.versions` — what versions of the target software this stack supports. Freeform, domain-specific.

### SemVer Rules for Stacks

- **Major** (2.0.0) — breaking changes: renamed/removed skills, changed environment schema, incompatible profile changes, removed profiles
- **Minor** (1.3.0) — new skills added, new profiles added, new profile categories, expanded target version support
- **Patch** (1.3.1) — corrections to existing skill content, profile value fixes, automation bug fixes

### Dependency Ranges

Stacks declare dependencies with SemVer ranges:
```yaml
depends_on:
  - name: base
    namespace: agentic-stacks
    version: "^1.0"      # >=1.0.0, <2.0.0
  - name: kubernetes
    namespace: littleknifelabs
    version: "~2.1"      # >=2.1.0, <2.2.0
```

### Deprecation Policy

Skills and profiles can be deprecated with explicit migration pointers:
```yaml
deprecations:
  - skill: deploy-with-kubeadm
    since: "2.1.0"          # when it was deprecated
    removal: "3.0.0"        # when it will be removed
    replacement: deploy-with-k3s   # what to use instead
    reason: "k3s simplifies bootstrap"
```

The `astack doctor` command flags deprecated skills in use. The `astack upgrade` command shows deprecation warnings. The registry UI marks deprecated skills visually.

Deprecated skills must survive for at least one major version after deprecation. Removal only happens in the next major version or later.

## Composability

### Three Composition Mechanisms

**depends_on** — this stack requires another stack to be available. The dependent stack is pulled automatically.
```yaml
depends_on:
  - name: kubernetes
    namespace: littleknifelabs
    version: "^2.0"
```

**includes** — cherry-pick specific skills from another stack without taking the whole dependency.
```yaml
includes:
  - from: observability
    namespace: agentic-stacks
    version: "^1.0"
    skills: [setup-prometheus, configure-grafana]
```

**extends** — take a base stack and override/patch specific parts. Like Kustomize overlays.
```yaml
extends:
  base: generic-webapp
  namespace: agentic-stacks
  version: "~1.0"
  overrides:
    build-strategy: maven
```

### Stack Hierarchy

```
Level 1 — Atomic Skills: Individual capabilities (e.g., "configure-nginx-reverse-proxy")
Level 2 — Stacks: Composed sets of skills with profiles (e.g., "kubernetes-cluster")
Level 3 — Solutions: Umbrella stacks combining other stacks (e.g., "java-webapp-on-k8s")
```

Solutions are just stacks whose primary content is `depends_on` and `includes` from other stacks, with thin orchestration skills that wire them together.

## Security and Trust

### Artifact Signing

Published stacks are signed via Cosign/Sigstore, attached to OCI artifacts. Signatures are verified on pull. The registry displays verification status.

### Permission Declaration

Stacks declare what they need in `stack.yaml`:
```yaml
requires:
  tools: [kubectl, helm, talosctl]
  python: ">=3.11"
  network: true           # needs outbound network access
  filesystem:
    read: ["/etc/kubernetes", "~/.kube"]
    write: ["./state/", "./generated/"]
```

Agents and the `astack` CLI can evaluate these requirements before pulling.

### Publisher Verification

Namespaces are claimed by publishers. Verified publishers undergo identity verification (linked GitHub org, domain verification). Verified status displayed on stacks and in API responses.

## Phased Delivery

### Phase 1: Stack Specification + Thin Runtime
- Formalize `stack.yaml` manifest spec
- Define directory conventions and profile merge rules
- Build `agentic_stacks` Python package (profile engine, state store, approval gates, schema validation, config diff)
- Refactor agentic-openstack to use the spec and runtime
- Refactor agentic-kubernetes to use the spec and runtime
- `astack` CLI: init, doctor, validate (local operations only)
- Publish spec documentation

### Phase 2: Registry & Website
- OCI-based distribution via ORAS + GHCR
- `astack` CLI: pull, push, upgrade, search, publish
- `stacks.lock` and dependency resolution
- agentic-stacks.com: browse, search, stack detail pages, publisher profiles
- Cosign signing and verification
- Publish agentic-openstack and agentic-kubernetes as the first two stacks

### Phase 3: Agent Discovery Protocol
- MCP server exposing registry as agent-callable tools
- Semantic search over stack metadata and skill descriptions
- Trust tier enforcement (verified / community / experimental)
- Agent consumption flow with approval gates
- Documentation and examples for agent integration

## Dependencies and Integrations

### Phase 1
- **Python 3.11+** — runtime language
- **PyYAML, jsonschema** — profile loading and validation
- **Click or Typer** — CLI framework for `astack`

### Phase 2
- **ORAS** — OCI artifact push/pull
- **GHCR** — primary OCI registry
- **Cosign/Sigstore** — artifact signing
- **Web framework (TBD)** — for agentic-stacks.com

### Phase 3
- **MCP SDK** — for building the agent discovery server
- **Vector embeddings (TBD)** — for semantic search over stack metadata

## Existing Work

Two stacks already exist as proof of concept:

- **agentic-openstack** (`/Users/ant/Development/littleknifelabs/agentic-openstack/`) — agent-driven OpenStack deployment on kolla-ansible. Design spec complete, Phase 1 plan written.
- **agentic-kubernetes** (`/Users/ant/Development/littleknifelabs/agentic-kubernetes/`) — agent-driven Kubernetes on Talos Linux. Design spec complete, Phase 1 plan written. Already extracting shared core as `agentic_stacks` package.

Both repos validate the stack anatomy: skills, profiles, environments, execution layer, approval gates, state tracking. Both share the same 5-layer architecture and action flow.

## Open Questions

1. **Web framework for agentic-stacks.com** — Static site + API, or full-stack app? Could start with a static site that reads from the OCI registry metadata.
2. **Semantic search implementation** — Embeddings-based search for Phase 3. Could use Claude embeddings or open-source models. Deferred until Phase 3.
3. **Private registries** — Enterprises will want private stack registries. Should the spec support configurable registry sources from Phase 1? Likely yes (like Helm's multiple repos).
4. **Stack testing** — Should the spec define a standard way to test stacks (validate profiles merge correctly, skills parse, schemas are valid)? `astack doctor` covers some of this but a formal test framework could help.
5. **Namespace governance** — How are namespaces claimed and managed? First-come-first-served with verification, or application-based?
