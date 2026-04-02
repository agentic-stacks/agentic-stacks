# TODO

## CLI Improvements

- [ ] **`create --github` flag** — `agentic-stacks create my-org/new-stack --github` should scaffold locally AND create the GitHub repo + push in one command. Use `gh repo create` under the hood. Removes friction when spinning up new stacks.

- [ ] **`create --template` flag** — use a GitHub template repo as the starting point instead of the built-in scaffold. Lets contributors fork a known-good stack structure.

- [ ] **Version pinning** — `agentic-stacks pin <name> <version>` to lock a stack to a specific calver tag/commit. Pinned stacks skip `update`. Useful for production deployments where stability matters more than freshness.

## Registry & Distribution

- [ ] **Third-party stack submissions** — allow anyone to submit a formula PR to `agentic-stacks/registry` pointing to their own repo. Review the formula, not the code. (Homebrew model)

- [ ] **`publish` writes to git registry** — currently `publish` hits the API. Should also/instead commit a formula to the registry repo via PR.

## Website

- [ ] **Stack README rendering** — fetch and render the stack's README.md on the detail page so visitors see full documentation without leaving the site.

## Stack Factory

- [ ] **Automated stack authoring pipeline** — a repo (`agentic-stacks/stack-factory`) that takes a list of stacks to create and automates the full authoring process. Reads the [authoring guide](docs/guides/authoring-a-stack.md), discovers official docs for each target software (llms.txt, sitemap.xml, GitHub), researches and verifies commands/configs, generates skills, CLAUDE.md, and stack.yaml, creates the repo, and publishes. Turns the "New Stacks to Author" list below into a queue that agents can work through.

## New Stacks to Author

- [ ] proxmox — hypervisor management
- [ ] linux — OS-level operations (systemd, networking, storage, tuning)
- [ ] minio — S3-compatible object storage
- [ ] zfs — storage management on bare metal
- [ ] loki — log aggregation
- [ ] vault — secrets management
- [ ] keycloak — identity/SSO
- [ ] opnsense — network firewall/router
