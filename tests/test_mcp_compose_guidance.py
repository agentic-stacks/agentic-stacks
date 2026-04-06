"""Tests for compose_guidance — the cross-stack guidance synthesis tool."""

import pathlib

import pytest
import yaml


def _create_project_with_stacks(tmp_path):
    """Create a project with two pulled stacks for testing."""
    project = tmp_path / "project"
    project.mkdir()

    # Stack 1: kubernetes
    k8s = project / ".stacks" / "kubernetes"
    k8s.mkdir(parents=True)
    k8s_manifest = {
        "name": "kubernetes",
        "owner": "agentic-stacks",
        "version": "2.0.0",
        "description": "Kubernetes operations",
        "target": {"software": "kubernetes", "versions": ["1.30"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": "Bootstrap a cluster"},
            {"name": "upgrade", "entry": "skills/upgrade/", "description": "Rolling upgrades"},
            {"name": "networking", "entry": "skills/networking/", "description": "CNI and service mesh"},
        ],
    }
    (k8s / "stack.yaml").write_text(yaml.dump(k8s_manifest, sort_keys=False))

    for skill in k8s_manifest["skills"]:
        skill_dir = k8s / skill["entry"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "README.md").write_text(
            f"# {skill['name'].title()}\n\n"
            f"## Prerequisites\n\nCluster must be running.\n\n"
            f"## Steps\n\nRun the {skill['name']} procedure.\n"
        )

    (k8s / "CLAUDE.md").write_text(
        "# kubernetes — Agentic Stack\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n"
        "|---|---|---|\n"
        "| Deploy a cluster | deploy | skills/deploy/ |\n"
        "| Upgrade Kubernetes | upgrade | skills/upgrade/ |\n"
        "| Configure networking | networking | skills/networking/ |\n"
    )

    # Stack 2: hardware-dell
    dell = project / ".stacks" / "hardware-dell"
    dell.mkdir(parents=True)
    dell_manifest = {
        "name": "hardware-dell",
        "owner": "agentic-stacks",
        "version": "1.0.0",
        "description": "Dell hardware management",
        "target": {"software": "dell-idrac", "versions": ["9"]},
        "skills": [
            {"name": "firmware", "entry": "skills/firmware/", "description": "Firmware upgrades for Dell servers"},
            {"name": "deploy", "entry": "skills/deploy/", "description": "Bare metal provisioning"},
        ],
    }
    (dell / "stack.yaml").write_text(yaml.dump(dell_manifest, sort_keys=False))

    for skill in dell_manifest["skills"]:
        skill_dir = dell / skill["entry"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "README.md").write_text(
            f"# {skill['name'].title()}\n\n## Steps\n\nDell {skill['name']} steps.\n"
        )

    (dell / "CLAUDE.md").write_text(
        "# hardware-dell — Agentic Stack\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n"
        "|---|---|---|\n"
        "| Upgrade firmware | firmware | skills/firmware/ |\n"
        "| Deploy bare metal | deploy | skills/deploy/ |\n"
    )

    # stacks.lock
    lock = {"stacks": [
        {"name": "agentic-stacks/kubernetes", "version": "2.0.0", "digest": "abc1234567", "registry": ""},
        {"name": "agentic-stacks/hardware-dell", "version": "1.0.0", "digest": "def7654321", "registry": ""},
    ]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    return project


@pytest.fixture
def project_with_stacks(tmp_path):
    return _create_project_with_stacks(tmp_path)


@pytest.mark.asyncio
async def test_compose_guidance_matches_across_stacks(project_with_stacks):
    """'deploy' should match skills in both kubernetes and hardware-dell."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("deploy", str(project_with_stacks))
    assert len(result["stacks"]) == 2
    stack_names = [s["name"] for s in result["stacks"]]
    assert "agentic-stacks/kubernetes" in stack_names
    assert "agentic-stacks/hardware-dell" in stack_names


@pytest.mark.asyncio
async def test_compose_guidance_single_stack_match(project_with_stacks):
    """'firmware' should only match hardware-dell."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("firmware", str(project_with_stacks))
    assert len(result["stacks"]) == 1
    assert result["stacks"][0]["name"] == "agentic-stacks/hardware-dell"
    assert result["stacks"][0]["matched_skills"][0]["name"] == "firmware"


@pytest.mark.asyncio
async def test_compose_guidance_no_match(project_with_stacks):
    """A totally unrelated task returns no stacks."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("quantum computing", str(project_with_stacks))
    assert len(result["stacks"]) == 0
    assert "No stacks" in result["summary"]


@pytest.mark.asyncio
async def test_compose_guidance_includes_content_preview(project_with_stacks):
    """Matched skills should include content preview from README."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("upgrade", str(project_with_stacks))
    k8s_stack = next(s for s in result["stacks"] if "kubernetes" in s["name"])
    upgrade_skill = next(s for s in k8s_stack["matched_skills"] if s["name"] == "upgrade")
    assert upgrade_skill["content_preview"]
    assert "Upgrade" in upgrade_skill["content_preview"]


@pytest.mark.asyncio
async def test_compose_guidance_includes_routing_excerpt(project_with_stacks):
    """Routing table entries matching the task should be included."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("networking", str(project_with_stacks))
    k8s_stack = next(s for s in result["stacks"] if "kubernetes" in s["name"])
    assert k8s_stack["routing_excerpt"]
    assert "networking" in k8s_stack["routing_excerpt"].lower()


@pytest.mark.asyncio
async def test_compose_guidance_includes_version_and_commit(project_with_stacks):
    """Results should include version and commit SHA for staleness detection."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("deploy", str(project_with_stacks))
    k8s_stack = next(s for s in result["stacks"] if "kubernetes" in s["name"])
    assert k8s_stack["version"] == "2.0.0"
    assert k8s_stack["commit"] == "abc1234"


@pytest.mark.asyncio
async def test_compose_guidance_summary_format(project_with_stacks):
    """Summary should be a readable multi-line string."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler("deploy", str(project_with_stacks))
    summary = result["summary"]
    assert "deploy" in summary
    assert "2 stack(s)" in summary
    assert "skills/deploy/" in summary


@pytest.mark.asyncio
async def test_compose_guidance_empty_project(tmp_path):
    """Works on a project with no stacks."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    project = tmp_path / "empty-project"
    project.mkdir()
    lock = {"stacks": []}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    result = await compose_guidance_handler("deploy", str(project))
    assert result["stacks"] == []
    assert "No stacks" in result["summary"]


@pytest.mark.asyncio
async def test_compose_guidance_unpulled_stack(tmp_path):
    """Skips stacks in lock that aren't actually pulled."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    project = tmp_path / "project"
    project.mkdir()
    lock = {"stacks": [
        {"name": "org/missing-stack", "version": "1.0.0", "digest": "", "registry": ""},
    ]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    result = await compose_guidance_handler("deploy", str(project))
    assert result["stacks"] == []


@pytest.mark.asyncio
async def test_compose_guidance_handler_returns_summary_string(project_with_stacks):
    """The handler summary is a readable string suitable for MCP tool output."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    result = await compose_guidance_handler(task="deploy", path=str(project_with_stacks))
    summary = result["summary"]
    assert isinstance(summary, str)
    assert "deploy" in summary
    assert "stack(s)" in summary


@pytest.mark.asyncio
async def test_compose_guidance_routing_only_match(project_with_stacks):
    """A task matching only in the routing table (not skill names) still returns."""
    from agentic_stacks_mcp.compose import compose_guidance_handler

    # "bare metal" appears in the Dell routing table but not in skill names
    result = await compose_guidance_handler("bare", str(project_with_stacks))
    dell_stacks = [s for s in result["stacks"] if "dell" in s["name"]]
    assert len(dell_stacks) >= 1
