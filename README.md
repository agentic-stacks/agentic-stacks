# Agentic Stacks

Domain expertise for AI agents. A stack is a git repo that teaches an agent how to operate in a specific domain — deploying OpenStack, bootstrapping Kubernetes, managing Dell hardware, and more.

<p align="center">
  <img src="docs/images/i-know-kung-fu.jpg" alt="I know kung fu" width="600">
</p>

Load skills into your AI agent like Neo downloads kung fu. One command and your agent knows OpenStack, Kubernetes, or whatever domain you need.

## How It Works

A **stack** is captured expertise: someone (or an agent) reads all the docs, does it a few times, and distills that knowledge into structured markdown skills. When a user pulls a stack, their agent becomes an expert in that domain.

```bash
# Start a project using a stack
agentic-stacks init agentic-stacks/openstack-kolla my-cloud
cd my-cloud
agentic-stacks pull

# Now talk to the agent — it knows OpenStack
# "I need an HA OpenStack cloud with OVN networking and Ceph storage
#  on these 10 hosts..."
```

The agent reads the stack's skills, asks the right questions, and creates the deployment configs. Everything it creates goes into your repo — reproducible, version-controlled, yours.

### Stack multiple domains

Need hardware expertise alongside your platform stack? Pull in more skills:

```bash
agentic-stacks pull dell-hardware    # now it knows Dell servers too
agentic-stacks list                  # see what's loaded
```

The agent reads all stacks and combines their expertise — hardware provisioning, platform deployment, and everything in between.

## What a Stack Looks Like

A stack is a git repo with this structure:

```
openstack-kolla/
├── CLAUDE.md               # Agent entry point — the expertise guide
├── stack.yaml              # Manifest — identity, skills, metadata
├── skills/                 # Markdown knowledge — teaches the agent
│   ├── deploy/
│   ├── health-check/
│   ├── config-build/
│   └── diagnose/
└── ...
```

The `CLAUDE.md` is the product — it's what makes the agent an expert. The skills directory contains detailed knowledge the agent references during operations.

## What a User's Project Looks Like

After `init` and working with the agent:

```
my-cloud/
├── .stacks/                # pulled stack repos (gitignored)
│   ├── openstack-kolla/    # platform expertise
│   └── dell-hardware/      # hardware expertise
├── CLAUDE.md               # points agent to .stacks/*/CLAUDE.md
├── stacks.lock             # pinned stack references
├── globals.yml             # kolla-ansible config (agent created this)
├── inventory/hosts.yml     # ansible inventory (agent helped build this)
├── config/                 # service overrides (agent guided these)
└── ...
```

The output is native format for whatever tool the stack wraps. No custom formats — just the configs the tool expects.

## Install

```bash
pip install agentic-stacks
```

## CLI

```bash
# Start a new project from a stack
agentic-stacks init agentic-stacks/openstack-kolla my-project

# Pull stacks into .stacks/
agentic-stacks pull                    # pulls all from stacks.lock
agentic-stacks pull dell-hardware      # add another stack

# Manage stacks
agentic-stacks list                    # see loaded stacks
agentic-stacks remove dell-hardware    # remove a stack

# Search for stacks
agentic-stacks search kubernetes

# Create a new stack (for stack authors)
agentic-stacks create my-org/my-stack

# Validate a stack
agentic-stacks doctor --path ./my-stack

# Register a stack with the registry
agentic-stacks publish --path ./my-stack
```

## Distribution

Stacks are git repos. Pull clones them. No package managers, no tarballs.

- **Curated stacks** live under the [`agentic-stacks`](https://github.com/agentic-stacks) GitHub org
- **Third-party stacks** live in their own repos — pull by `org/name`

```bash
agentic-stacks pull openstack-kolla           # → github.com/agentic-stacks/openstack-kolla
agentic-stacks pull someuser/their-stack      # → github.com/someuser/their-stack
```

## Registry & Website

[agentic-stacks.com](https://agentic-stacks.com) — browse and discover available stacks. The registry indexes stack metadata for search and display.

## Development

```bash
pip install -e ".[dev,local,mcp]"
pytest -v --tb=short
uvicorn registry.local:app --reload
```

## License

See [LICENSE](LICENSE) for details.
