# Authoring a Stack

A stack is a git repository that teaches an AI agent how to operate in a specific domain. When an agent reads your stack, it should become an expert operator — capable of deploying, managing, troubleshooting, and upgrading the target software.

This guide covers how to design and build a comprehensive stack. It extracts patterns from the [kubernetes-talos](https://github.com/agentic-stacks/kubernetes-talos) stack, which serves as a reference implementation for complex, multi-platform operational stacks.

## Anatomy of a Stack

Every stack has these files at the root:

```
my-stack/
├── README.md       # Repo landing page — usage, composability, authoring link
├── CLAUDE.md       # Agent entry point — persona, rules, routing
├── stack.yaml      # Machine-readable manifest
└── skills/         # Operational knowledge, organized by phase
```

Optional:
- `.gitignore` — ignore operator project artifacts

## Starting a Stack

```bash
agentic-stacks create my-org/my-stack
```

This scaffolds `README.md`, `CLAUDE.md`, `stack.yaml`, and a `skills/` directory. The rest of this guide helps you fill it with high-quality operational knowledge.

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
owner: my-org
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

## Step 4: Research and Verify Against Official Docs

A stack is only as good as its accuracy. Before writing any skill, you must fetch and verify against the target software's official documentation. Agents using your stack will execute commands verbatim — a wrong flag name or outdated YAML field can break a production cluster.

### Find the Documentation Index

Most documentation sites publish an index or sitemap. Look for:

- **`/llms.txt`** — an emerging standard for AI-readable doc indexes (e.g., `https://docs.siderolabs.com/llms.txt`)
- **`/sitemap.xml`** — standard sitemap
- **API docs at `/api/`** — for tools with HTTP APIs
- **GitHub repo** — the source markdown files are often more accurate than rendered docs

Start by fetching the index to understand what pages exist and where the canonical URLs are. Documentation sites restructure frequently — the URL you found in a blog post may redirect.

### Verify Every Command and Config Field

For each skill you write:

1. **Fetch the relevant official doc page** before writing content
2. **Copy exact commands** from the docs — do not reconstruct from memory
3. **Verify YAML field names** — `certSANs` not `certSans`, `kubeProxyReplacement` not `kube-proxy-replacement`
4. **Check flag names** — `--insecure` vs `--dangerous` vs `--skip-verify` vary between tools and versions
5. **Note version-specific behavior** — commands and config fields change between releases

### What to Extract from Official Docs

When reading a doc page, extract:

| Category | Examples |
|---|---|
| **Exact commands** | `talosctl gen config`, `helm install` with all flags |
| **Config structure** | YAML schema, required vs optional fields |
| **Default values** | What happens if you omit a field |
| **Warnings and caveats** | "Only run this once", "This is destructive" |
| **Order of operations** | What must happen before what |
| **Port numbers and protocols** | Network requirements for firewall rules |
| **Version compatibility** | Which versions of A work with which versions of B |
| **Known issues** | Bugs, workarounds, and fixes |

### Cross-Reference Multiple Sources

Official docs sometimes lag behind reality. Cross-reference with:

- **Release notes** — the most current source of breaking changes and new features
- **GitHub issues** — confirmed bugs with workarounds
- **CLI help output** — `tool --help` is always accurate for the installed version
- **Source code** — the ultimate source of truth when docs are ambiguous

### Example: Research Workflow

When building the kubernetes-talos stack, each skill was written by:

1. Fetching `docs.siderolabs.com/llms.txt` to find all available pages
2. Fetching the specific topic page (e.g., deploying Cilium, upgrading Talos)
3. Extracting exact commands, YAML snippets, warnings, and version notes
4. Cross-referencing with release notes for version-specific behavior
5. Writing the skill content with verified information
6. Including the doc URL as a reference for future updates

### Keep Content Fresh

Documentation is a snapshot in time. Include version markers in your content:

```markdown
> **Talos v1.9+**: `systemd-udev` replaces `eudev`. Network interface names may change.
```

And maintain version-specific known issues files that can be updated independently of the main skill content.

---

## Step 5: Write Skill Content

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

## Step 6: Training Skill

Every stack ships with a **training skill** — a special skill that tells the agent how to teach the stack's domain to new users. When a user says "train me on this stack," the agent reads the training skill and switches from task-execution mode to teaching mode, using all the other skills as source material.

### What It Does

The training skill gives the agent pedagogical instructions:

- **Assess the learner** — ask what they already know, adjust depth
- **Build a curriculum** — sequence the stack's skills from foundational to advanced
- **Teach interactively** — explain concepts, give exercises, ask questions
- **Adapt** — go deeper on weak areas, skip ahead on strong ones
- **Track progress** — summarize what's been covered, what remains

The agent uses your other skills as the source material. No separate training content is needed — the domain knowledge already exists in your skills.

### New Stacks

`agentic-stacks create` scaffolds `skills/training/README.md` automatically. The training skill is pre-populated with pedagogical instructions and already listed in `stack.yaml` and the CLAUDE.md routing table.

### Adding to Existing Stacks

If your stack was created before the training skill was introduced, add it manually:

1. Create `skills/training/README.md` with the template below
2. Add the skill entry to `stack.yaml`:
   ```yaml
   skills:
     - name: training
       entry: skills/training/
       description: Interactive training — teaches this stack's domain to new users
     # ... your other skills
   ```
3. Add a routing table entry to `CLAUDE.md`:
   ```markdown
   | Learn / Train | training | skills/training/ |
   ```

**Training skill template** (`skills/training/README.md`):

```markdown
# Training Mode

When the user asks to be trained on this stack, switch from task-execution
mode to teaching mode. Use the stack's skills as your source material.

## Getting Started

1. **Assess the learner.** Ask what they already know about [stack-name] and
   related technologies. Adjust depth accordingly.

2. **Build a curriculum.** Read every skill in this stack. Sequence them
   from foundational concepts to advanced operations. Present the
   learning path and let the user adjust it.

3. **Teach concepts before procedures.** For each skill, explain the
   *why* before the *how*. Use the skill's content as your source
   material — not generic knowledge.

4. **Make it interactive.** After explaining a concept, give the user
   a practical task or question. Use real commands and configurations
   from the skill content. Ask them to predict outcomes before
   showing answers.

5. **Check understanding.** Ask questions between topics. If the user
   struggles, go deeper on prerequisites. If they're moving quickly,
   skip ahead or go deeper on advanced material.

6. **Connect the dots.** Explicitly link concepts across skills.
   Help the user build a mental model of how everything fits together.

7. **Summarize each section.** Recap key concepts and what the user
   can now do before moving on.

## Handling Specific Requests

- "Train me on this stack" — start from the beginning with an assessment.
- "Train me on [topic]" — jump to the relevant skill and teach from there.
- "Quiz me" — test knowledge on material covered so far.
- "What should I learn next?" — recommend the next topic based on progress.

## Session Continuity

Track which topics the user has covered in this session. If they want
to stop and continue later, summarize where they left off and what
topics remain.
```

Replace `[stack-name]` with your stack's name.

### Customizing the Training Skill

The default template works well out of the box, but stack authors can customize it:

- **Add prerequisite hints** — "Users should understand Linux networking before the networking module"
- **Suggest a learning order** — "Start with concepts, then bootstrap, then networking"
- **Add domain-specific exercises** — "Have the user deploy a single-node cluster before moving to multi-node"
- **Include assessment questions** — "Ask the user to explain the difference between control plane and worker nodes"

---

## Step 7: Decision Guides and Compatibility Matrices

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

## Step 8: Validate Your Stack

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
agentic-stacks doctor
```

---

## Checklist

Before publishing your stack:

- [ ] `CLAUDE.md` has identity, critical rules, routing table, and workflows
- [ ] `stack.yaml` lists all skills with correct entry paths
- [ ] Training skill exists at `skills/training/README.md`
- [ ] Every skill directory has a `README.md`
- [ ] All commands are exact and copy-pasteable
- [ ] Safety warnings precede every destructive operation
- [ ] No placeholders (TBD, TODO, FIXME) remain
- [ ] Known issues are documented for supported versions
- [ ] Decision guides exist for any "choose between options" scenarios
- [ ] Cross-references between skills use correct paths
- [ ] `README.md` describes what the stack does and how to use it
- [ ] The stack has been tested by having an agent use it end-to-end

---

## Designing for Composition

Operators can pull multiple stacks into a single project. For example, a Kubernetes stack and a Dell hardware stack working together:

```bash
agentic-stacks init my-cluster
cd my-cluster
agentic-stacks pull kubernetes-talos
agentic-stacks pull hardware-dell
```

The agent reads all stacks via `.stacks/*/CLAUDE.md` and combines their expertise. To make your stack compose well:

- **Stay in your domain.** A hardware stack shouldn't reimplement networking concepts that a platform stack already covers.
- **Use `depends_on` in stack.yaml** to declare stacks that pair well with yours (e.g., a storage stack that expects a Kubernetes stack).
- **Avoid conflicting file outputs.** If two stacks both generate `/etc/foo.conf`, operators will have a bad time. Document what files your stack creates in `project.structure`.
- **Name skills distinctively.** When an agent loads multiple stacks, skill names should make it clear which domain they belong to.

---

## Reference Implementations

| Stack | Complexity | Pattern |
|---|---|---|
| [openstack-kolla](https://github.com/agentic-stacks/openstack-kolla) | Simple | Flat phase-based (5 skills) |
| [kubernetes-talos](https://github.com/agentic-stacks/kubernetes-talos) | Comprehensive | Two-layer phase/domain (20 skills, 66 files) |

Start from whichever is closest to your target complexity, then adapt.
