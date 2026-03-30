#!/usr/bin/env python3
"""Sync formula YAML files from stack repos in the agentic-stacks org.

Usage:
    python sync_formulas.py --org agentic-stacks --output ./stacks
    python sync_formulas.py --org agentic-stacks --output ./stacks --token ghp_...

Requires: PyYAML, and either `gh` CLI (authenticated) or a --token arg.
"""

import argparse
import pathlib
import subprocess
import sys
from typing import Any
from base64 import b64decode

import yaml


def manifest_to_formula(manifest: dict[str, Any]) -> dict[str, Any]:
    """Convert a stack.yaml manifest into a registry formula."""
    owner = manifest.get("owner") or manifest.get("namespace", "")
    name = manifest["name"]
    version = manifest.get("version", "0.0.0")

    # Strip 'entry' from skills — formulas only need name + description
    skills = []
    for skill in manifest.get("skills", []):
        skills.append({
            "name": skill["name"],
            "description": skill.get("description", ""),
        })

    # Flatten tools to just names if they're dicts
    requires = dict(manifest.get("requires", {}))
    if "tools" in requires:
        tools = requires["tools"]
        if tools and isinstance(tools[0], dict):
            requires["tools"] = [t["name"] for t in tools]

    return {
        "name": name,
        "owner": owner,
        "version": str(version),
        "repository": manifest.get("repository", ""),
        "tag": f"v{version}",
        "sha256": "",
        "description": manifest.get("description", "").strip(),
        "target": manifest.get("target", {}),
        "skills": skills,
        "depends_on": manifest.get("depends_on", []),
        "requires": requires,
    }


def write_formulas(output_dir: pathlib.Path, formulas: list[dict]) -> None:
    """Write formula YAML files to output_dir/stacks/<owner>/<name>.yaml."""
    for formula in formulas:
        owner = formula["owner"]
        name = formula["name"]
        owner_dir = output_dir / "stacks" / owner
        owner_dir.mkdir(parents=True, exist_ok=True)
        formula_path = owner_dir / f"{name}.yaml"
        with open(formula_path, "w") as f:
            yaml.dump(formula, f, default_flow_style=False, sort_keys=False)


def fetch_repos(org: str, token: str | None = None) -> list[str]:
    """List all repos in a GitHub org."""
    cmd = ["gh", "api", f"orgs/{org}/repos", "--paginate", "--jq", ".[].name"]
    if token:
        cmd.extend(["--header", f"Authorization: token {token}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error listing repos: {result.stderr}", file=sys.stderr)
        return []
    return [name.strip() for name in result.stdout.strip().split("\n") if name.strip()]


def fetch_manifest(org: str, repo: str, token: str | None = None) -> dict | None:
    """Fetch stack.yaml from a repo. Returns None if not found."""
    cmd = ["gh", "api", f"repos/{org}/{repo}/contents/stack.yaml", "--jq", ".content"]
    if token:
        cmd.extend(["--header", f"Authorization: token {token}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        content = b64decode(result.stdout.strip()).decode("utf-8")
        return yaml.safe_load(content)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Sync registry formulas from GitHub org")
    parser.add_argument("--org", default="agentic-stacks", help="GitHub org to scan")
    parser.add_argument("--output", default=".", help="Output directory (registry repo root)")
    parser.add_argument("--token", default=None, help="GitHub token (optional, uses gh auth)")
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output)
    print(f"Scanning {args.org}...")

    repos = fetch_repos(args.org, args.token)
    print(f"Found {len(repos)} repos")

    formulas = []
    for repo in repos:
        manifest = fetch_manifest(args.org, repo, args.token)
        if manifest:
            formula = manifest_to_formula(manifest)
            formulas.append(formula)
            print(f"  {formula['owner']}/{formula['name']}@{formula['version']}")
        else:
            print(f"  {repo} — no stack.yaml, skipping")

    write_formulas(output_dir, formulas)
    print(f"\nWrote {len(formulas)} formula(s)")


if __name__ == "__main__":
    main()
