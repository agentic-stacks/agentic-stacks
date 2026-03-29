# Authoring a Stack

A stack is a git repository that teaches an AI agent how to operate in a specific domain. When an agent reads your stack, it should become an expert operator — capable of deploying, managing, troubleshooting, and upgrading the target software.

This guide covers how to design and build a comprehensive stack. It extracts patterns from the [kubernetes-talos](https://github.com/agentic-stacks/kubernetes-talos) stack, which serves as a reference implementation for complex, multi-platform operational stacks.

## Anatomy of a Stack

Every stack has three required files at the root:

```
my-stack/
├── CLAUDE.md       # Agent entry point — persona, rules, routing
├── stack.yaml      # Machine-readable manifest
└── skills/         # Operational knowledge, organized by phase
```

Optional:
- `.gitignore` — ignore operator project artifacts
- `profiles/` — composable configuration presets
- `environments/` — environment-specific settings with JSON Schema validation

## Starting a Stack

```bash
agentic-stacks init ./my-stack --name my-stack --namespace my-org
```

This scaffolds the basic structure. The rest of this guide helps you fill it with high-quality operational knowledge.

---

## Step 1: Design the Skill Hierarchy

Skills are the core of your stack — directories of markdown files that teach the agent how to perform specific operations.

### Organize by Operational Phase

Group skills by *what the operator is trying to do*, not by technology component:

| Phase | Purpose | Examples |
|---|---|---|
| **Foundation** | Understanding and setup | Architecture concepts, configuration, provisioning |
| **Deploy** | Initial deployment | Bootstrap, networking, storage |
| **Platform** | Platform layer | GitOps, ingress, monitoring, security |
| **Operations** | Day-two management | Health checks, scaling, upgrades, backup, certs |
| **Diagnose** | Troubleshooting | Symptom-based decision trees |
| **Reference** | Cross-cutting lookups | Known issues, compatibility matrices, decision guides |

This phase-based organization gives the agent a natural workflow: foundation → deploy → platform → operations. When troubleshooting, the agent jumps directly to diagnose.

### Two-Layer Hierarchy

For complex stacks, use **phase/domain** nesting:

```
skills/
├── foundation/
│   ├── concepts/           # Mental model
│   ├── machine-config/     # Configuration management
│   └── infrastructure/     # Platform-specific provisioning
│       ├── README.md       # Overview + platform index
│       ├── aws.md          # AWS-specific guide
│       ├── gcp.md          # GCP-specific guide
│       └── ...
├── deploy/
│   ├── bootstrap/
│   ├── networking/
│   │   ├── README.md       # Decision matrix
│   │   ├── cilium.md       # Option A deep dive
│   │   └── flannel.md      # Option B deep dive
│   └── storage/
└── operations/
    ├── health-check/
    ├── upgrades/
    └── ...
```

Each skill directory has a `README.md` that provides overview and routing. Sub-files go deep into specific topics. This gives agents **progressive depth** — they can skim the README or drill into specifics.

### When to Use Single vs. Two-Layer

- **Simple stacks** (5-10 skills): flat `skills/config-build/`, `skills/deploy/`, etc. — like [openstack-kolla](https://github.com/agentic-stacks/openstack-kolla)
- **Complex stacks** (10+ skills, multiple deployment targets, many component choices): two-layer phase/domain hierarchy — like [kubernetes-talos](https://github.com/agentic-stacks/kubernetes-talos)

---

## Step 2: Write CLAUDE.md

`CLAUDE.md` is the agent's brain. It sets identity, enforces safety, and routes to skills.

### Structure

```markdown
# [Stack Name] — Agentic Stack

## Identity

[1-2 sentences establishing the agent's expertise and how it works with operators]

## Critical Rules

[Numbered list of hard safety guardrails the agent must never violate]

## Routing Table

| Operator Need | Skill | Entry Point |
|---|---|---|
| [What the operator wants to do] | [skill-name] | `skills/path/to/skill` |

## Workflows

### New Deployment
[Linear path through skills for first-time setup]

### Existing Deployment
[How to jump to the right skill for ongoing operations]

## Expected Operator Project Structure
[What the operator's own repo should look like when using this stack]
```

### Writing Critical Rules

Critical rules are the most important part of CLAUDE.md. They prevent the agent from doing damage. Good rules are:

- **Specific**: "Never run `talosctl reset` without operator approval" not "be careful with destructive operations"
- **Actionable**: the agent can check compliance unambiguously
- **Justified**: explain *why* — "etcd quorum loss means cluster down"
- **Minimal**: 5-10 rules. Too many and the agent ignores them.

**Template for a critical rule:**
```
N. **Never/Always [action]** — [what to do instead]. [Why this matters].
```

### Writing the Routing Table

The routing table maps *operator intent* to skills. Write entries from the operator's perspective:

- "Understand the architecture" not "Read concepts skill"
- "Choose and install CNI" not "Go to networking directory"
- "Troubleshoot issues" not "Read troubleshooting README"

Every skill in `stack.yaml` should appear in the routing table.

---

## Step 3: Write stack.yaml

The machine-readable manifest. Key fields:

```yaml
name: my-stack
namespace: my-org
version: 0.1.0
description: >
  One paragraph describing what this stack teaches agents to operate.

repository: https://github.com/my-org/my-stack

target:
  software: target-software-name
  versions:
    - "1.x"

skills:
  - name: skill-name
    entry: skills/path/to/skill
    description: One-line description of what this skill covers

project:
  structure:
    - file-or-dir-in-operator-project

requires:
  tools:
    - name: tool-name
      description: What it's used for

depends_on: []
```

**Tips:**
- `entry` points to a directory, not a file. The directory's `README.md` is the entry point.
- `description` should help an agent decide whether to read the skill.
- `project.structure` defines what the operator's repo looks like when using this stack.

---

## Step 4: Write Skill Content

### Writing Style for Agent Consumption

Agents process structured information differently than humans. Optimize for:

1. **Imperative headings**: "Install Cilium", "Verify Health", "Rotate Certificates" — not "About Cilium Installation"
2. **Exact commands**: full copy-pasteable commands, not pseudocode
   ```bash
   # Good
   talosctl upgrade -n 192.168.1.10 --image ghcr.io/siderolabs/installer:v1.9.5

   # Bad
   talosctl upgrade -n <node-ip> --image <installer-image>
   ```
   Use realistic example values, then explain what to substitute.
3. **Decision trees**: "If X fails → check Y → if Y is true → do Z"
4. **Tables for reference**: comparison matrices, port requirements, timing estimates
5. **Safety warnings**: explicit callouts before any destructive operation
6. **YAML/config examples**: include full, valid snippets — not fragments

### Consistent Templates

When multiple files cover the same type of content, use a consistent template. This helps agents pattern-match.

**Platform/infrastructure template:**
```markdown
# [Platform Name]

## Prerequisites
## Image Provisioning
## Network Requirements
## Configuration Specifics
## Control Plane / Primary Endpoint
## Provisioning Commands
## Platform-Specific Gotchas
```

**Component option template (CNI, CSI, etc.):**
```markdown
# [Component Name] on [Target]

## When to Choose [Component]
## Prerequisites
## Installation
## Configuration
## Verification
## Operational Notes
```

**Decision guide template:**
```markdown
# [Decision] Selection Guide

## Context
## Options
## Comparison Table
## Recommendation by Use Case
## Migration Path
```

### The Stock File Philosophy

When your target software generates configuration files, teach the agent to:

1. Generate from the tool's own command (never from scratch)
2. Commit the generated output as `.orig` files
3. Apply patches/modifications separately
4. Use `git diff` to see exactly what was customized

This prevents configuration drift and makes changes auditable.

### Known Issues Pattern

Version-specific bugs deserve their own files:

```
skills/reference/known-issues/
├── README.md              # How to use, naming convention
├── software-1.8.md        # Version-specific issues
└── software-1.9.md
```

Each entry follows a consistent format:
```markdown
### [Short Description]

**Symptom:** What the operator sees
**Cause:** Why it happens
**Workaround:** Exact steps to fix it
**Affected versions:** x.y.z through x.y.w
**Status:** Open / Fixed in x.y.w
```

Reference these from CLAUDE.md critical rules: "Always check known issues before deploying or upgrading."

---

## Step 5: Decision Guides and Compatibility Matrices

For stacks where operators must choose between components (CNI, storage, ingress, etc.), provide structured decision aids:

### Decision Guides

Place in `skills/reference/decision-guides/`. Each guide helps the agent recommend the right component:

```markdown
| Feature | Option A | Option B | Option C |
|---|---|---|---|
| Performance | High | Medium | High |
| Complexity | High | Low | Medium |
| ...         | ...  | ...     | ...     |

### Recommendation by Use Case

- **Production bare metal**: Option A — because [reason]
- **Development/testing**: Option B — because [reason]
- **Cloud-native**: Option C — because [reason]

### Migration Path

Can you change this decision later? [Yes/No, how hard, what breaks]
```

### Compatibility Matrices

Place in `skills/reference/compatibility/`. Map which versions of components work together:

```markdown
| Target Software | Component A | Component B | Notes |
|---|---|---|---|
| v1.9.x | v3.x - v4.x | v1.x - v2.x | Requires extension X |
| v1.8.x | v3.x only | v1.x only | Known issue with v2.x |
```

---

## Step 6: Validate Your Stack

Before publishing, verify:

```bash
# All skills in stack.yaml have directories
grep "entry:" stack.yaml | awk '{print $2}' | while read dir; do
  [ -d "$dir" ] && echo "OK: $dir" || echo "MISSING: $dir"
done

# No placeholders
grep -ri "tbd\|todo\|fixme\|placeholder" skills/ CLAUDE.md stack.yaml

# Routing table entries match skills
grep 'skills/' CLAUDE.md | grep -o 'skills/[^ ]*' | sort -u | while read path; do
  [ -d "$path" ] || [ -f "$path" ] && echo "OK: $path" || echo "BROKEN: $path"
done

# Validate manifest
agentic-stacks validate
```

---

## Checklist

Before publishing your stack:

- [ ] `CLAUDE.md` has identity, critical rules, routing table, and workflows
- [ ] `stack.yaml` lists all skills with correct entry paths
- [ ] Every skill directory has a `README.md`
- [ ] All commands are exact and copy-pasteable
- [ ] Safety warnings precede every destructive operation
- [ ] No placeholders (TBD, TODO, FIXME) remain
- [ ] Known issues are documented for supported versions
- [ ] Decision guides exist for any "choose between options" scenarios
- [ ] Cross-references between skills use correct paths
- [ ] The stack has been tested by having an agent use it end-to-end

---

## Reference Implementations

| Stack | Complexity | Pattern |
|---|---|---|
| [openstack-kolla](https://github.com/agentic-stacks/openstack-kolla) | Simple | Flat phase-based (5 skills) |
| [kubernetes-talos](https://github.com/agentic-stacks/kubernetes-talos) | Comprehensive | Two-layer phase/domain (20 skills, 66 files) |

Start from whichever is closest to your target complexity, then adapt.
