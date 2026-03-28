"""MCP server exposing Agentic Stacks registry as agent-callable tools."""

import json
import pathlib

from mcp.server.fastmcp import FastMCP

from agentic_stacks_cli.config import load_config
from agentic_stacks_cli.api_client import RegistryClient
from agentic_stacks_cli.oci import pull_stack as oci_pull_stack

mcp = FastMCP("agentic-stacks")

_client_instance = None


def _get_client() -> RegistryClient:
    global _client_instance
    if _client_instance is None:
        cfg = load_config()
        _client_instance = RegistryClient(
            api_url=cfg.get("api_url", "https://agentic-stacks.com/api/v1"),
            token=cfg.get("token"),
        )
    return _client_instance


# --- Handlers (testable without MCP transport) ---

async def search_stacks_handler(query: str) -> list[dict]:
    client = _get_client()
    return client.search(query)


async def get_stack_info_handler(name: str, version: str | None = None) -> dict:
    client = _get_client()
    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = name
    return client.get_stack(namespace, stack_name, version=version)


async def get_skill_handler(stack: str, skill_name: str) -> dict | None:
    client = _get_client()
    if "/" in stack:
        namespace, stack_name = stack.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = stack
    info = client.get_stack(namespace, stack_name)
    for skill in info.get("skills", []):
        if skill["name"] == skill_name:
            return skill
    return None


async def pull_stack_handler(name: str, version: str, path: str) -> dict:
    client = _get_client()
    cfg = load_config()
    registry = cfg.get("registry", "ghcr.io")
    if "/" in name:
        namespace, stack_name = name.split("/", 1)
    else:
        namespace = "agentic-stacks"
        stack_name = name
    info = client.get_stack(namespace, stack_name, version=version)
    actual_version = info.get("version", version)
    output_dir = pathlib.Path(path) / ".stacks" / namespace / stack_name / actual_version
    digest = oci_pull_stack(
        registry=registry, namespace=namespace, name=stack_name,
        version=actual_version, output_dir=output_dir,
    )
    return {"path": str(output_dir), "digest": digest, "version": actual_version}


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
        lines.append(f"  {s['namespace']}/{s['name']}@{s.get('version', 'latest')}")
        if s.get("description"):
            lines.append(f"    {s['description']}")
    return "\n".join(lines)


@mcp.tool()
async def get_stack_info(name: str, version: str | None = None) -> str:
    """Get detailed information about a specific stack.

    Args:
        name: Stack name in "namespace/name" format (e.g., "agentic-stacks/openstack-kolla").
        version: Optional specific version. If omitted, returns the latest version.

    Returns detailed information including skills, profiles, dependencies, and install command.
    """
    try:
        info = await get_stack_info_handler(name, version)
    except Exception as e:
        return f"Error: Could not get info for '{name}': {e}"

    lines = [f"Stack: {info.get('namespace', '')}/{info['name']}@{info['version']}"]
    lines.append(f"Description: {info.get('description', 'No description')}")

    skills = info.get("skills", [])
    if skills:
        lines.append(f"\nSkills ({len(skills)}):")
        for s in skills:
            desc = f" — {s['description']}" if s.get("description") else ""
            lines.append(f"  - {s['name']}{desc}")

    profiles = info.get("profiles", {})
    categories = profiles.get("categories", [])
    if categories:
        lines.append(f"\nProfile categories: {', '.join(categories)}")

    deps = info.get("depends_on", [])
    if deps:
        lines.append(f"\nDependencies:")
        for d in deps:
            lines.append(f"  - {d['namespace']}/{d['name']} {d['version']}")

    deprecations = info.get("deprecations", [])
    if deprecations:
        lines.append(f"\nDeprecations:")
        for d in deprecations:
            lines.append(f"  - {d['skill']}: use '{d['replacement']}' instead")

    requires = info.get("requires", {})
    tools = requires.get("tools", [])
    if tools:
        lines.append(f"\nRequired tools: {', '.join(tools)}")

    lines.append(f"\nInstall: agentic-stacks pull {info.get('namespace', '')}/{info['name']}@{info['version']}")
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
            f"Pulled {name}@{result['version']} to {result['path']}\n"
            f"Digest: {result['digest']}\n\n"
            f"The stack's skills are now available at {result['path']}/skills/"
        )
    except Exception as e:
        return f"Error pulling stack: {e}"


def main():
    mcp.run()
