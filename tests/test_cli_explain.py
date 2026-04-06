import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_stack(path, manifest_overrides=None):
    """Create a stack for explain testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "kube-stack",
        "owner": "myorg",
        "version": "2.1.0",
        "description": "Teaches agents to deploy and operate Kubernetes.",
        "target": {"software": "kubernetes", "versions": ["1.29", "1.30"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": "Bootstrap a cluster"},
            {"name": "upgrade", "entry": "skills/upgrade/", "description": "Rolling upgrades"},
            {"name": "health", "entry": "skills/health/", "description": "Health checks"},
        ],
        "profiles": {"categories": ["security", "networking"], "path": "profiles/"},
        "depends_on": ["hardware-dell"],
        "requires": {
            "tools": [{"name": "kubectl", "description": "Kubernetes CLI"}],
            "python": ">=3.11",
        },
        "deprecations": [
            {"skill": "old-deploy", "since": "1.0.0", "removal": "3.0.0", "replacement": "deploy",
             "reason": "Replaced"},
        ],
        "docs_sources": ["https://kubernetes.io/docs"],
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))

    # Skills dirs
    for skill in manifest["skills"]:
        (path / skill["entry"]).mkdir(parents=True, exist_ok=True)

    # CLAUDE.md with workflows
    (path / "CLAUDE.md").write_text(
        "# kube-stack — Agentic Stack\n\n"
        "## Workflows\n\n"
        "### New Cluster\nBootstrap from scratch.\n\n"
        "### Day Two Operations\nUpgrades, scaling, certs.\n"
    )


def test_explain_stack_direct(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert result.exit_code == 0
    assert "myorg/kube-stack@2.1.0" in result.output
    assert "kubernetes" in result.output
    assert "deploy" in result.output
    assert "upgrade" in result.output
    assert "health" in result.output


def test_explain_shows_target(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "kubernetes" in result.output
    assert "1.29" in result.output


def test_explain_shows_profiles(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "security" in result.output
    assert "networking" in result.output


def test_explain_shows_dependencies(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "hardware-dell" in result.output


def test_explain_shows_requirements(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "kubectl" in result.output
    assert ">=3.11" in result.output


def test_explain_shows_deprecations(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "old-deploy" in result.output
    assert "deploy" in result.output


def test_explain_shows_workflows(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "New Cluster" in result.output
    assert "Day Two Operations" in result.output


def test_explain_shows_docs_sources(tmp_path):
    _create_stack(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "kubernetes.io" in result.output


def test_explain_pulled_stack_by_name(tmp_path):
    """Explain a stack by name from a project directory."""
    project = tmp_path / "project"
    project.mkdir()
    _create_stack(project / ".stacks" / "kube-stack")
    lock = {"stacks": [{"name": "myorg/kube-stack", "version": "2.1.0",
                         "digest": "abc", "registry": ""}]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "kube-stack", "--path", str(project)])
    assert result.exit_code == 0
    assert "myorg/kube-stack" in result.output


def test_explain_project_all_stacks(tmp_path):
    """Explain all stacks in a project."""
    project = tmp_path / "project"
    project.mkdir()
    _create_stack(project / ".stacks" / "kube-stack")

    # Create a second minimal stack
    s2 = project / ".stacks" / "other"
    s2.mkdir(parents=True)
    (s2 / "stack.yaml").write_text(yaml.dump({
        "name": "other", "owner": "org", "version": "0.1.0",
        "description": "Another stack", "skills": [],
    }, sort_keys=False))

    lock = {"stacks": [
        {"name": "myorg/kube-stack", "version": "2.1.0", "digest": "", "registry": ""},
        {"name": "org/other", "version": "0.1.0", "digest": "", "registry": ""},
    ]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(project)])
    assert result.exit_code == 0
    assert "kube-stack" in result.output
    assert "other" in result.output


def test_explain_not_pulled(tmp_path):
    """Explain a stack that isn't pulled gives an error."""
    project = tmp_path / "project"
    project.mkdir()
    lock = {"stacks": [{"name": "myorg/missing", "version": "1.0.0",
                         "digest": "", "registry": ""}]}
    (project / "stacks.lock").write_text(yaml.dump(lock))

    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "missing", "--path", str(project)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_explain_no_stack_no_project(tmp_path):
    """Explain in an empty directory gives an error."""
    (tmp_path / "empty").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "empty")])
    assert result.exit_code != 0


def test_explain_minimal_stack(tmp_path):
    """Explain works with a minimal manifest (no optional fields)."""
    stack = tmp_path / "stack"
    stack.mkdir()
    (stack / "stack.yaml").write_text(yaml.dump({
        "name": "minimal", "owner": "org", "version": "0.1.0",
        "description": "Bare minimum",
    }, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(stack)])
    assert result.exit_code == 0
    assert "org/minimal@0.1.0" in result.output
    assert "Bare minimum" in result.output


def test_explain_string_depends_on(tmp_path):
    """Explain handles depends_on as plain strings."""
    _create_stack(tmp_path / "stack", manifest_overrides={
        "depends_on": ["common-skills", "monitoring-stack"],
    })
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "common-skills" in result.output
    assert "monitoring-stack" in result.output


def test_explain_tool_as_string(tmp_path):
    """Explain handles requires.tools as plain strings."""
    _create_stack(tmp_path / "stack", manifest_overrides={
        "requires": {"tools": ["kubectl", "helm"], "python": ">=3.12"},
    })
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--path", str(tmp_path / "stack")])
    assert "kubectl" in result.output
    assert "helm" in result.output
