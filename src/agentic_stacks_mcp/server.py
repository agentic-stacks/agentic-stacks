"""MCP server exposing Agentic Stacks registry as agent-callable tools."""

import pathlib
import subprocess

from mcp.server.fastmcp import FastMCP

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.registry_repo import ensure_registry, load_formula, search_formulas
from agentic_stacks_mcp.compose import compose_guidance_handler

mcp = FastMCP("agentic-stacks")


def _get_registry_path():
    cfg = load_config()
    return ensure_registry(
        repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
    )


# --- Handlers (testable without MCP transport) ---

async def search_stacks_handler(query: str) -> list[dict]:
    registry_path = _get_registry_path()
    return search_formulas(registry_path, query)


async def get_stack_info_handler(name: str, version: str | None = None) -> dict:
    cfg = load_config()
    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = cfg.get("default_namespace", "agentic-stacks")
        stack_name = name
    registry_path = ensure_registry(
        repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
    )
    formula = load_formula(registry_path, namespace, stack_name)
    return formula


async def get_skill_handler(stack: str, skill_name: str) -> dict | None:
    info = await get_stack_info_handler(stack)
    if not info:
        return None
    for skill in info.get("skills", []):
        if skill["name"] == skill_name:
            return skill
    return None


async def pull_stack_handler(name: str, version: str, path: str) -> dict:
    cfg = load_config()
    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = cfg.get("default_namespace", "agentic-stacks")
        stack_name = name
    registry_path = ensure_registry(
        repo_url=cfg.get("registry_repo", "https://github.com/agentic-stacks/registry"),
    )
    formula = load_formula(registry_path, namespace, stack_name)
    if formula:
        repo_url = formula["repository"]
    else:
        repo_url = f"https://github.com/{namespace}/{stack_name}"
    output_dir = pathlib.Path(path) / ".stacks" / stack_name
    if output_dir.exists():
        subprocess.run(["git", "-C", str(output_dir), "pull"], check=True,
                        capture_output=True, text=True)
    else:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(output_dir)], check=True,
                        capture_output=True, text=True)
    actual_version = formula.get("version", version) if formula else version
    return {"path": str(output_dir), "version": actual_version}


# --- MCP Tools ---

@mcp.tool()
async def search_stacks(query: str) -> str:
    """Search for stacks in the Agentic Stacks registry.

    Use this when you need to find a stack that provides domain expertise.
    For example: "kubernetes deployment", "openstack", "ceph storage".

    Returns a list of matching stacks with name, namespace, version, and description.
    """
    results = await search_stacks_handler(query)
    if not results:
        return f"No stacks found for '{query}'."
    lines = [f"Found {len(results)} stack(s):\n"]
    for s in results:
        lines.append(f"  {s.get('owner', '')}/{s['name']}@{s.get('version', 'latest')}")
        if s.get("description"):
            lines.append(f"    {s['description']}")
    return "\n".join(lines)


@mcp.tool()
async def get_stack_info(name: str, version: str | None = None) -> str:
    """Get detailed information about a specific stack.

    Args:
        name: Stack name in "namespace/name" format (e.g., "agentic-stacks/openstack-kolla").
        version: Optional specific version. If omitted, returns the latest version.

    Returns detailed information including skills, dependencies, and install command.
    """
    try:
        info = await get_stack_info_handler(name, version)
    except Exception as e:
        return f"Error: Could not get info for '{name}': {e}"

    if not info:
        return f"Stack '{name}' not found."

    owner = info.get("owner", "")
    lines = [f"Stack: {owner}/{info['name']}@{info.get('version', '?')}"]
    lines.append(f"Description: {info.get('description', 'No description')}")

    skills = info.get("skills", [])
    if skills:
        lines.append(f"\nSkills ({len(skills)}):")
        for s in skills:
            desc = f" — {s['description']}" if s.get("description") else ""
            lines.append(f"  - {s['name']}{desc}")

    deps = info.get("depends_on", [])
    if deps:
        lines.append(f"\nDependencies:")
        for d in deps:
            lines.append(f"  - {d.get('namespace', d.get('owner', ''))}/{d['name']} {d.get('version', '')}")

    requires = info.get("requires", {})
    tools = requires.get("tools", [])
    if tools:
        lines.append(f"\nRequired tools: {', '.join(tools)}")

    lines.append(f"\nInstall: agentic-stacks pull {owner}/{info['name']}")
    return "\n".join(lines)


@mcp.tool()
async def get_skill(stack: str, skill_name: str) -> str:
    """Get information about a specific skill in a stack.

    Args:
        stack: Stack name in "namespace/name" format.
        skill_name: Name of the skill to look up.

    Returns the skill description and metadata.
    """
    result = await get_skill_handler(stack, skill_name)
    if not result:
        return f"Skill '{skill_name}' not found in stack '{stack}'."
    lines = [f"Skill: {result['name']}"]
    if result.get("description"):
        lines.append(f"Description: {result['description']}")
    return "\n".join(lines)


@mcp.tool()
async def pull_stack(name: str, version: str, path: str = ".") -> str:
    """Pull a stack from the registry to a local directory.

    This downloads the stack so its skills and profiles can be loaded into context.

    Args:
        name: Stack name in "namespace/name" format (e.g., "agentic-stacks/openstack-kolla").
        version: Version to pull (e.g., "1.0.0").
        path: Local directory to pull into. Defaults to current directory.

    Returns the path where the stack was extracted.
    """
    try:
        result = await pull_stack_handler(name, version, path)
        return (
            f"Pulled {name}@{result['version']} to {result['path']}\n\n"
            f"The stack's skills are now available at {result['path']}/skills/"
        )
    except Exception as e:
        return f"Error pulling stack: {e}"


@mcp.tool()
async def compose_guidance(task: str, path: str = ".") -> str:
    """Get synthesized guidance for a task across all pulled stacks.

    Scans every stack in the project, finds skills relevant to the task,
    and returns a combined briefing with content previews and entry points.
    Use this when an operator asks a question that might span multiple domains
    (e.g., "upgrade Kubernetes on Dell hardware").

    Args:
        task: What the operator wants to do (e.g., "deploy", "upgrade",
              "troubleshoot networking", "rotate certificates").
        path: Project directory containing stacks.lock. Defaults to ".".

    Returns a briefing with matched skills from each stack, routing table
    excerpts, and content previews.
    """
    result = await compose_guidance_handler(task, path)
    return result["summary"]


def main():
    mcp.run()
