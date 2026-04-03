# Agentic Stacks

[![CI](https://github.com/agentic-stacks/agentic-stacks/actions/workflows/ci.yml/badge.svg)](https://github.com/agentic-stacks/agentic-stacks/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Installable skill packs that give AI agents deep domain expertise. A stack is a git repo that teaches an agent how to operate in a specific domain — deploying OpenStack, bootstrapping Kubernetes, managing server hardware, and more.

<p align="center">
  <img src="docs/images/i-know-kung-fu.jpg" alt="I know kung fu" width="600">
</p>

Pull a stack into your project and your AI agent instantly knows how to deploy, manage, troubleshoot, and upgrade the target software. Stacks teach agents *and* humans — ask the agent to train you on any domain and it builds an interactive curriculum from the stack's skills.

## How It Works

```bash
# Start a project and pull a stack
agentic-stacks init my-cluster
cd my-cluster
agentic-stacks pull kubernetes-talos

# Now talk to the agent — it knows Kubernetes on Talos
# "I need a 5-node HA cluster with Cilium CNI and
#  local-path storage on these hosts..."
```

The agent reads the stack's skills, asks the right questions, and creates the deployment configs. Everything it creates goes into your repo — reproducible, version-controlled, yours.

### Compose multiple domains

Need hardware expertise alongside your platform stack? Pull in more skills:

```bash
agentic-stacks pull hardware-dell    # now it knows Dell servers too
agentic-stacks list                  # see what's loaded
```

The agent reads all stacks and combines their expertise — hardware provisioning, platform deployment, and everything in between.

### Learn from your stacks

Every project includes [common-skills](https://github.com/agentic-stacks/common-skills) — a shared stack with training, guided walkthroughs, orientation, and feedback capture. Ask the agent to teach you the domain and it builds a curriculum from the stack's skills.

```bash
# In a project with stacks pulled:
> train me on this stack
> train me on RAID management
> quiz me
> what should I learn next?
```

The agent assesses what you already know, sequences topics from foundational to advanced, and adapts as you go. Stacks teach agents *and* humans.

### Capture learnings as you go

Hit an issue? Ask your agent to document it. Stacks get smarter over time — every workaround, gotcha, and fix feeds back into the stack for the next person.

> "That NTP fix we just did — add it to known issues for this version."

## Available Stacks

<!-- STACKS-TABLE-START -->
| Stack | Target | Skills |
|-------|--------|--------|
| [docker](https://www.agentic-stacks.com/stacks/agentic-stacks/docker) | docker | 21 |
| [kubernetes-talos](https://www.agentic-stacks.com/stacks/agentic-stacks/kubernetes-talos) | talos-linux | 20 |
| [openstack-core](https://www.agentic-stacks.com/stacks/agentic-stacks/openstack-core) | openstack | 25 |
| [openstack-kolla](https://www.agentic-stacks.com/stacks/agentic-stacks/openstack-kolla) | openstack | 8 |
| [ceph](https://www.agentic-stacks.com/stacks/agentic-stacks/ceph) | ceph | 17 |
| [hardware-dell](https://www.agentic-stacks.com/stacks/agentic-stacks/hardware-dell) | Dell PowerEdge | 18 |
| [hardware-hpe](https://www.agentic-stacks.com/stacks/agentic-stacks/hardware-hpe) | hpe-ilo | 16 |
| [hardware-supermicro](https://www.agentic-stacks.com/stacks/agentic-stacks/hardware-supermicro) | Supermicro BMC | 17 |
| [frr](https://www.agentic-stacks.com/stacks/agentic-stacks/frr) | frr | 35 |
| [ipxe](https://www.agentic-stacks.com/stacks/agentic-stacks/ipxe) | ipxe | 20 |
| [ansible](https://www.agentic-stacks.com/stacks/agentic-stacks/ansible) | ansible | 16 |
| [terraform](https://www.agentic-stacks.com/stacks/agentic-stacks/terraform) | terraform | 16 |
| [prometheus-grafana](https://www.agentic-stacks.com/stacks/agentic-stacks/prometheus-grafana) | prometheus-grafana | 18 |
| [common-skills](https://www.agentic-stacks.com/stacks/agentic-stacks/common-skills) | agentic-stacks | 4 |
| [linux](https://www.agentic-stacks.com/stacks/agentic-stacks/linux) | linux | 31 |
| [rails](https://www.agentic-stacks.com/stacks/agentic-stacks/rails) | rails | 20 |
<!-- STACKS-TABLE-END -->

Browse all stacks at [agentic-stacks.com/stacks](https://agentic-stacks.com/stacks).

## Install

```bash
pipx install agentic-stacks
```

## CLI

```bash
# Start a new project
agentic-stacks init my-project
cd my-project

# Pull stacks into .stacks/
agentic-stacks pull kubernetes-talos    # pull a stack
agentic-stacks pull hardware-dell      # add another stack

# Manage stacks
agentic-stacks list                    # see loaded stacks
agentic-stacks update                  # update all to latest
agentic-stacks update --check          # check without updating
agentic-stacks remove hardware-dell    # remove a stack

# Search for stacks
agentic-stacks search kubernetes

# Create a new stack (for stack authors)
agentic-stacks create my-org/my-stack

# Validate a stack
agentic-stacks doctor --path ./my-stack
```

## What a Stack Looks Like

A stack is a git repo with this structure:

```
kubernetes-talos/
├── CLAUDE.md               # Agent entry point — the expertise guide
├── stack.yaml              # Manifest — identity, skills, metadata
└── skills/                 # Markdown knowledge — teaches the agent
    ├── deploy/             # Bootstrap, Networking, Storage
    ├── foundation/         # Concepts, Infrastructure, Machine Config
    ├── operations/         # Backup, Certs, Health Check, Scaling, Upgrades
    ├── platform/           # GitOps, Ingress, Observability, Security
    └── reference/          # Compatibility, Known Issues, Decision Guides
```

The `CLAUDE.md` is the product — it's what makes the agent an expert. The skills directory contains detailed knowledge the agent references during operations.

## What a User's Project Looks Like

After `init` and working with the agent:

```
my-cluster/
├── .stacks/                # pulled stack repos (gitignored)
│   ├── kubernetes-talos/   # platform expertise
│   └── hardware-dell/      # hardware expertise
├── CLAUDE.md               # points agent to .stacks/*/CLAUDE.md
├── stacks.lock             # pinned stack references
├── controlplane.yaml       # Talos machine config (agent created this)
├── worker.yaml             # worker node config (agent helped build this)
└── ...
```

The output is native format for whatever tool the stack wraps. No custom formats — just the configs the tool expects.

## Distribution

Stacks are git repos. Pull clones them. No package managers, no tarballs.

- **Curated stacks** live under the [`agentic-stacks`](https://github.com/agentic-stacks) GitHub org
- **Third-party stacks** live in their own repos — pull by `org/name`

```bash
agentic-stacks pull kubernetes-talos           # → github.com/agentic-stacks/kubernetes-talos
agentic-stacks pull someuser/their-stack      # → github.com/someuser/their-stack
```

## Author a Stack

See the [authoring guide](https://agentic-stacks.com/docs/authoring) for how to create and publish your own stack.

```bash
agentic-stacks create my-org/my-stack
# edit skills, CLAUDE.md, stack.yaml
agentic-stacks doctor --path ./my-stack
agentic-stacks publish --path ./my-stack
```

## Development

```bash
pip install -e ".[dev,local,mcp]"
pytest -v --tb=short
```

## License

MIT — see [LICENSE](LICENSE).
