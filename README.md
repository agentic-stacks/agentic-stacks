# Agentic Stacks

A platform for packaging, versioning, distributing, and discovering composed domain expertise for AI agents.

A **stack** bundles skills (markdown knowledge), profiles (composable YAML configs), automation, and environment schemas into a versioned package that gives an agent deep competence in a domain — deploying OpenStack, bootstrapping Kubernetes, standing up a Rails app, building a data pipeline.

## Why

There's no cross-domain, versioned, agent-queryable system for bundling domain expertise. Protocol layers exist (MCP, A2A). Single-tool registries exist (Smithery, Composio). Infrastructure package managers exist (Helm, Ansible Galaxy). But nobody owns the **composed capability pack** layer for AI agents. Agentic Stacks fills that gap.

## What a Stack Looks Like

```
my-stack/
├── stack.yaml              # Manifest — identity, version, deps, contents
├── skills/                 # Markdown brain — teaches the agent what to do
├── profiles/               # Composable YAML building blocks (security, networking, etc.)
├── environments/           # Declarative intent + JSON Schema validation
├── src/                    # Automation code — the hands
└── CLAUDE.md               # Agent entry point
```

## Install

```bash
pip install agentic-stacks
```

Or install with all extras for development:

```bash
pip install -e ".[dev,local,mcp]"
```

## CLI

```bash
# Create a new stack
agentic-stacks init ./my-stack --name example --namespace my-org

# Validate stack structure
agentic-stacks doctor ./my-stack

# Validate an environment against the stack schema
agentic-stacks validate my-stack prod

# Authenticate with GitHub
agentic-stacks login

# Publish to registry
agentic-stacks publish --path ./my-stack

# Pull a stack
agentic-stacks pull my-org/example@1.0.0

# Search the registry
agentic-stacks search kubernetes
```

## Three Layers

### 1. Stack Specification + Thin Runtime

The spec defines what a stack is. The runtime (`agentic_stacks` Python package) handles the mechanical parts shared across all stacks: profile merging with enforced key protection, environment validation, config diffing, state tracking, and approval gates.

### 2. Registry & Website

[agentic-stacks.com](https://agentic-stacks.com) — browse, search, and pull versioned stacks. Distribution uses OCI registries (GHCR) via ORAS. Stacks are content-addressable, signed via Cosign/Sigstore, and immutable once published.

### 3. Agent Discovery Protocol

An MCP server that lets agents find and pull stacks at runtime:

```bash
agentic-stacks-mcp
```

Exposes tools: `search_stacks`, `get_stack_info`, `get_skill`, `pull_stack`. An agent encounters a task it doesn't know how to do, searches the registry, pulls a stack, and loads the skills into context.

## Stack Manifest

```yaml
name: openstack-kolla
namespace: agentic-stacks
version: "1.3.0"
description: "Agent-driven OpenStack deployment on kolla-ansible"

target:
  software: openstack
  versions: ["2024.2", "2025.1"]

skills:
  - name: deploy
    entry: skills/deploy/
    description: "Wraps kolla-ansible lifecycle"

profiles:
  categories: [security, networking, storage, scale]
  path: profiles/
  merge_order: "security first (enforced), then declared order"

environment_schema: environments/_schema.json

depends_on:
  - name: base
    namespace: agentic-stacks
    version: "^1.0"
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,local,mcp]"

# Run tests
pytest -v --tb=short

# Run local registry server
uvicorn registry.local:app --reload

# Build
pip install build && python -m build
```

## License

See [LICENSE](LICENSE) for details.
