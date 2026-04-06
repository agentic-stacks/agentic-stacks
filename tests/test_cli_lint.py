import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_stack(path, manifest_overrides=None, create_skills=True, create_claude_md=True):
    """Create a minimal stack for lint testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack",
        "owner": "testorg",
        "version": "1.0.0",
        "description": "A test stack",
        "target": {"software": "test-tool", "versions": ["1.0"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": "Deploy test-tool"},
            {"name": "health", "entry": "skills/health/", "description": "Health checks"},
        ],
        "depends_on": [],
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)

    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))

    if create_skills:
        for skill in manifest["skills"]:
            skill_dir = path / skill["entry"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "README.md").write_text(
                f"# {skill['name'].title()}\n\n"
                f"## Prerequisites\n\nNone.\n\n"
                f"## Install {skill['name'].title()}\n\nRun the install command.\n\n"
                f"## Verify\n\nCheck that it works.\n"
            )

    if create_claude_md:
        (path / "CLAUDE.md").write_text(
            "# test-stack — Agentic Stack\n\n"
            "## Identity\n\nI am an expert test-tool operator.\n\n"
            "## Critical Rules\n\n"
            "1. **Never delete data** — always back up first.\n"
            "2. **Always verify health** — run health checks after changes.\n"
            "3. **Use staging first** — test in staging before production.\n\n"
            "## Routing Table\n\n"
            "| Need | Skill | Entry |\n"
            "|---|---|---|\n"
            "| Deploy | deploy | skills/deploy/ |\n"
            "| Health | health | skills/health/ |\n\n"
            "## Workflows\n\n"
            "### New Deployment\nDeploy then verify.\n\n"
            "### Existing Deployment\nCheck health first.\n"
        )


def test_lint_clean_stack(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert result.exit_code == 0
    assert "clean" in result.output


def test_lint_missing_readme(tmp_path):
    _create_stack(tmp_path / "stack")
    # Remove one skill's README
    (tmp_path / "stack" / "skills" / "deploy" / "README.md").unlink()
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "skill-readme" in result.output


def test_lint_missing_claude_md(tmp_path):
    _create_stack(tmp_path / "stack", create_claude_md=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "claude-md" in result.output


def test_lint_placeholder_detected(tmp_path):
    _create_stack(tmp_path / "stack")
    # Add a placeholder to a skill file
    (tmp_path / "stack" / "skills" / "deploy" / "README.md").write_text(
        "# Deploy\n\n## Steps\n\nTODO: fill this in\n\n## Verify\n\nCheck logs.\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "placeholder" in result.output


def test_lint_non_imperative_heading(tmp_path):
    _create_stack(tmp_path / "stack")
    (tmp_path / "stack" / "skills" / "deploy" / "README.md").write_text(
        "# About Deploy\n\n## Overview of Installation\n\nSome content here.\n\n"
        "More content for minimum lines.\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "imperative-heading" in result.output


def test_lint_missing_routing_table(tmp_path):
    _create_stack(tmp_path / "stack")
    (tmp_path / "stack" / "CLAUDE.md").write_text(
        "# test-stack\n\n## Identity\n\nExpert operator.\n\n"
        "## Critical Rules\n\n"
        "1. Rule one.\n2. Rule two.\n3. Rule three.\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "routing-table" in result.output


def test_lint_few_critical_rules(tmp_path):
    _create_stack(tmp_path / "stack")
    (tmp_path / "stack" / "CLAUDE.md").write_text(
        "# test-stack\n\n"
        "## Critical Rules\n\n1. Only one rule.\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n|---|---|---|\n"
        "| Deploy | deploy | skills/deploy/ |\n"
        "| Health | health | skills/health/ |\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "critical-rules-count" in result.output


def test_lint_missing_skill_description(tmp_path):
    _create_stack(tmp_path / "stack", manifest_overrides={
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": ""},
        ],
    })
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "skill-description" in result.output


def test_lint_missing_target_software(tmp_path):
    _create_stack(tmp_path / "stack", manifest_overrides={
        "target": {"software": "", "versions": []},
    })
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "target-software" in result.output


def test_lint_skill_entry_missing(tmp_path):
    _create_stack(tmp_path / "stack")
    import shutil
    shutil.rmtree(tmp_path / "stack" / "skills" / "deploy")
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "skill-missing" in result.output


def test_lint_custom_rules_file(tmp_path):
    _create_stack(tmp_path / "stack")
    # Create a rules file that disables placeholder checking
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(yaml.dump({
        "forbid_placeholders": False,
        "require_critical_rules": False,
    }))
    # Add a placeholder — should not trigger with custom rules
    (tmp_path / "stack" / "skills" / "deploy" / "README.md").write_text(
        "# Deploy\n\n## Steps\n\nTODO: fill this in\n\n## Verify\n\nCheck.\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack"),
                                  "--rules", str(rules_file)])
    assert "placeholder" not in result.output


def test_lint_disabled_rules(tmp_path):
    _create_stack(tmp_path / "stack")
    # Stack-level rules that disable routing-completeness
    (tmp_path / "stack" / ".lint-rules.yaml").write_text(
        yaml.dump({"disabled_rules": ["routing-completeness"]})
    )
    # Remove a skill from routing table — normally a warning
    (tmp_path / "stack" / "CLAUDE.md").write_text(
        "# test-stack\n\n"
        "## Critical Rules\n\n1. One.\n2. Two.\n3. Three.\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n|---|---|---|\n"
        "| Deploy | deploy | skills/deploy/ |\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "routing-completeness" not in result.output


def test_lint_project(tmp_path):
    """Lint command works on a project with stacks.lock."""
    project = tmp_path / "project"
    project.mkdir()
    stacks_dir = project / ".stacks" / "my-stack"
    _create_stack(stacks_dir)
    lock = {"stacks": [{"name": "testorg/my-stack", "version": "1.0.0",
                         "digest": "abc123", "registry": ""}]}
    (project / "stacks.lock").write_text(yaml.dump(lock))
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(project)])
    # Expect either "clean" or some findings — not an error
    assert result.exit_code == 0
    # Should mention the stack name from the lock
    assert "my-stack" in result.output


def test_lint_common_skills_rules(tmp_path):
    """Rules from common-skills are picked up for project-level linting."""
    project = tmp_path / "project"
    project.mkdir()

    # Create common-skills with centralized rules
    common = project / ".stacks" / "common-skills"
    common.mkdir(parents=True)
    (common / ".lint-rules.yaml").write_text(
        yaml.dump({"max_skill_lines": 10, "min_critical_rules": 1})
    )

    # Create a stack to lint
    stack = project / ".stacks" / "my-stack"
    _create_stack(stack)

    lock = {"stacks": [
        {"name": "agentic-stacks/common-skills", "version": "1.0.0", "digest": "", "registry": ""},
        {"name": "testorg/my-stack", "version": "1.0.0", "digest": "", "registry": ""},
    ]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(project)])
    assert result.exit_code == 0


def test_lint_no_manifest(tmp_path):
    """Lint on empty directory gives an error."""
    (tmp_path / "empty").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "empty")])
    assert result.exit_code != 0


def test_lint_routing_completeness(tmp_path):
    """Skills in manifest but missing from routing table are flagged."""
    _create_stack(tmp_path / "stack")
    # CLAUDE.md only references deploy, not health
    (tmp_path / "stack" / "CLAUDE.md").write_text(
        "# test-stack\n\n"
        "## Critical Rules\n\n1. One.\n2. Two.\n3. Three.\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n|---|---|---|\n"
        "| Deploy | deploy | skills/deploy/ |\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--path", str(tmp_path / "stack")])
    assert "routing-completeness" in result.output
    assert "health" in result.output
