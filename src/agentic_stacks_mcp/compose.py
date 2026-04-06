"""Compose guidance across pulled stacks — no MCP dependency."""

import pathlib
import re

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks_cli.lock import read_lock


async def compose_guidance_handler(task: str, path: str) -> dict:
    """Scan all pulled stacks and return relevant skills for a task.

    Returns a dict with:
      - stacks: list of {name, version, matched_skills, routing_excerpt, commit}
      - summary: human-readable briefing
    """
    project_dir = pathlib.Path(path)
    lock = read_lock(project_dir / "stacks.lock")
    stacks_entries = lock.get("stacks", [])

    if not stacks_entries:
        return {"stacks": [], "summary": "No stacks in this project."}

    task_lower = task.lower()
    task_words = set(task_lower.split())
    results = []

    for entry in stacks_entries:
        short_name = entry["name"].split("/")[-1]
        stack_dir = project_dir / ".stacks" / short_name
        manifest_path = stack_dir / "stack.yaml"

        if not manifest_path.exists():
            continue

        try:
            manifest = load_manifest(manifest_path)
        except ManifestError:
            continue

        # Score skills by relevance to the task
        matched_skills = []
        for skill in manifest.get("skills", []):
            skill_name = skill.get("name", "")
            skill_desc = skill.get("description", "")
            skill_entry = skill.get("entry", "")

            # Match against skill name, description, and entry path
            searchable = f"{skill_name} {skill_desc} {skill_entry}".lower()
            if any(word in searchable for word in task_words):
                # Read the skill README for content snippet
                readme_path = stack_dir / skill_entry / "README.md"
                content_snippet = ""
                if readme_path.exists():
                    text = readme_path.read_text()
                    lines = text.strip().splitlines()
                    content_snippet = "\n".join(lines[:20])

                matched_skills.append({
                    "name": skill_name,
                    "description": skill_desc,
                    "entry": skill_entry,
                    "content_preview": content_snippet,
                })

        # Also check CLAUDE.md routing table for task relevance
        routing_excerpt = ""
        claude_path = stack_dir / "CLAUDE.md"
        if claude_path.exists():
            claude_content = claude_path.read_text()
            routing_excerpt = _extract_matching_routes(claude_content, task_words)

        # Include stack if it has matched skills or relevant routing
        if matched_skills or routing_excerpt:
            commit = entry.get("digest", "")[:7]
            results.append({
                "name": entry["name"],
                "version": entry.get("version", "?"),
                "commit": commit,
                "matched_skills": matched_skills,
                "routing_excerpt": routing_excerpt,
            })

    # Build summary
    if not results:
        summary = (
            f"No stacks have skills directly matching '{task}'. "
            f"Try broader terms or check available stacks with 'agentic-stacks list'."
        )
    else:
        summary_lines = [f"Found guidance for '{task}' across {len(results)} stack(s):\n"]
        for r in results:
            summary_lines.append(f"  {r['name']}@{r['version']} ({len(r['matched_skills'])} skill(s))")
            for s in r["matched_skills"]:
                summary_lines.append(f"    - {s['name']}: {s['description']}")
                summary_lines.append(f"      entry: {s['entry']}")
            if r["routing_excerpt"]:
                summary_lines.append(f"    routing: {r['routing_excerpt']}")
        summary = "\n".join(summary_lines)

    return {"stacks": results, "summary": summary}


def _extract_matching_routes(claude_content: str, task_words: set[str]) -> str:
    """Extract routing table rows that match any task words."""
    matching_rows = []
    in_table = False

    for line in claude_content.splitlines():
        if re.match(r"(?i)##\s*routing\s*table", line):
            in_table = True
            continue
        if in_table:
            if re.match(r"^##\s+", line) and not re.match(r"^###", line):
                break
            # Match table rows (skip header and separator)
            if line.strip().startswith("|") and "---" not in line:
                line_lower = line.lower()
                if any(word in line_lower for word in task_words):
                    matching_rows.append(line.strip())

    return " | ".join(matching_rows) if matching_rows else ""
