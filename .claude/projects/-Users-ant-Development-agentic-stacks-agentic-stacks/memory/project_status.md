---
name: Project status
description: Agentic Stacks deployment status — registry live on CF Workers, D1 wired, website at agentic-stacks.ajmesserli.workers.dev
type: project
---

Registry API + website deployed to Cloudflare Workers at agentic-stacks.ajmesserli.workers.dev. D1 database wired. GitHub Actions CI (Python 3.12/3.13) and auto-deploy on push to main.

**Why:** Proving out the platform with a working registry before publishing first stacks (openstack-kolla, kubernetes-talos).

**How to apply:** When making changes, ensure they work on both local SQLite and CF Workers D1. Push to main triggers deploy automatically.
