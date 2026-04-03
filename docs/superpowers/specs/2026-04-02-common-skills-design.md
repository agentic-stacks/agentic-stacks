# Common Skills Stack — Design Spec

**Date:** 2026-04-02
**Status:** Approved

## Overview

A shared stack (`agentic-stacks/common-skills`) containing cross-cutting skills that every project benefits from. Pulled automatically on `agentic-stacks init`, removable like any other stack.

**Repository:** https://github.com/agentic-stacks/common-skills

## Problem

Training, guided walkthroughs, orientation, and feedback capture are useful in every project regardless of domain. Currently training is copy-pasted into each domain stack. Adding new common skills (guide, orientation, feedback) would require updating 15+ repos. A shared stack centralizes these and makes them updatable via `agentic-stacks update`.

## Skills

### Training (`skills/training/`)

Switches the agent from task-execution mode to teaching mode. Uses the domain stack's skills as source material.

- Assess the learner's existing knowledge
- Build a curriculum from foundational to advanced
- Teach concepts before procedures
- Interactive exercises and quizzes
- Adapt depth based on the learner's progress
- Track session progress for continuity

Identical to the template already deployed across all domain stacks. Common-skills becomes the canonical source. Domain stacks can override by keeping their own `skills/training/`.

### Guide (`skills/guide/`)

Wizard-style guided walkthrough of actual tasks. Different from training (which teaches concepts) — guide produces a concrete plan tailored to the user's environment and walks through it.

1. Ask what the user wants to accomplish
2. Read the relevant domain stack's CLAUDE.md to find the matching workflow
3. Assess environment — ask about hosts, OS, network, existing state
4. Build a step-by-step plan tailored to their answers, referencing specific skills
5. Walk through each step — show commands, explain what they do, confirm before moving on
6. At each step, check if it worked. If not, route to diagnose skills
7. Summarize what was accomplished and current environment state

### Orientation (`skills/orientation/`)

Project-aware skill that reads all pulled stacks and gives a unified overview. The natural entry point for new users.

1. Read `.stacks/*/CLAUDE.md` for every pulled stack
2. Summarize each stack: name, domain, key capabilities
3. Highlight how stacks compose (e.g., "hardware-dell + kubernetes-talos = bare metal K8s")
4. Suggest starting points based on what's pulled
5. Mention that training and guide modes are available

This is the only skill that's project-aware rather than stack-scoped.

### Feedback (`skills/feedback/`)

Captures operational learnings and writes them to the appropriate domain stack for upstream contribution.

1. Ask what happened and which domain it relates to
2. Identify the right location in the domain stack (known-issues, skill content, etc.)
3. Write the entry using the stack's existing format conventions
4. Show the user the diff
5. Explain how to submit it upstream (git diff, PR)

## Stack Structure

```
common-skills/
├── CLAUDE.md
├── stack.yaml
├── README.md
└── skills/
    ├── training/README.md
    ├── guide/README.md
    ├── orientation/README.md
    └── feedback/README.md
```

**CLAUDE.md identity:** "You are a learning and project assistant. You help users learn from their stacks, get guided through tasks, understand what's available, and capture operational learnings."

**Routing table:**

| Need | Skill | Entry |
|---|---|---|
| Learn / Train | training | `skills/training/` |
| Walk me through a task | guide | `skills/guide/` |
| What can you help me with? | orientation | `skills/orientation/` |
| Capture a learning / fix | feedback | `skills/feedback/` |

**stack.yaml:** Standard manifest. `depends_on: []`. No special fields.

## CLI Changes

### `init` command

After creating `stacks.lock`, `.gitignore`, and `CLAUDE.md`, automatically pull `agentic-stacks/common-skills`.

- New `--no-common` flag skips the auto-pull
- Output shows: `Pulling common-skills...`
- If pull fails (no network, registry unavailable), init still succeeds with a warning — the project is usable without common-skills

### No changes to other commands

- `remove common-skills` works like any other stack
- `update` picks up common-skills alongside everything else
- `list` shows common-skills in the list

## Override Behavior

If a domain stack has its own `skills/training/README.md`, the agent sees both the common-skills version and the domain-stack version. The domain stack's CLAUDE.md routing table takes precedence for routing since the agent reads all stacks and the domain-specific routing is more specific. No merge logic needed — the agent handles this naturally.

## Testing

- `test_init_pulls_common_skills` — init creates `.stacks/common-skills/` and adds entry to `stacks.lock`
- `test_init_no_common_flag` — `--no-common` skips the auto-pull, no common-skills in lock or `.stacks/`
- `test_init_common_skills_failure_non_fatal` — if pull fails, init still succeeds with a warning
- `test_remove_common_skills` — `remove common-skills` works like any other stack
- `test_init_existing_project_skips` — re-running init still errors on existing `stacks.lock`

Tests mock git clone since common-skills is a real remote repo.

## Rollout

1. **Create the common-skills stack** — scaffold repo at `agentic-stacks/common-skills`, write four skills, push
2. **Publish to registry** — `agentic-stacks publish` so it's discoverable
3. **CLI changes** — modify `init` to auto-pull, add `--no-common` flag, release new CLI version
4. **Clean up per-stack training** — optional/later. Remove `skills/training/` from domain stacks once common-skills is established. Duplicates don't break anything.
5. **Update docs** — authoring guide, README, website to reference common-skills
