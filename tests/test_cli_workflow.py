"""End-to-end CLI workflow test: init → pull → list → doctor.

Uses a real local git repo as a fixture stack to exercise the full
pipeline without network access.
"""
import pathlib
import subprocess

import yaml
from click.testing import CliRunner
from unittest.mock import patch

from agentic_stacks_cli import cli


def _create_fixture_stack(path: pathlib.Path) -> str:
    """Create a local git repo that looks like a real stack. Returns repo path."""
    path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": "test-stack",
        "owner": "test-org",
        "version": "1.0.0",
        "description": "A test stack for workflow validation",
        "repository": f"file://{path}",
        "target": {"software": "test-software", "versions": ["1.0", "2.0"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy/", "description": "Deploy the software"},
            {"name": "operations", "entry": "skills/operations/", "description": "Day-two operations"},
            {"name": "troubleshoot", "entry": "skills/troubleshoot/", "description": "Diagnose issues"},
        ],
        "depends_on": [],
        "requires": {"tools": [{"name": "test-tool", "description": "Required tool"}], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))

    # Create skills with content
    for skill in manifest["skills"]:
        skill_dir = path / skill["entry"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "README.md").write_text(
            f"# {skill['name'].title()}\n\n{skill['description']}.\n"
        )

    # Create CLAUDE.md
    (path / "CLAUDE.md").write_text(
        "# test-stack\n\n"
        "## Routing Table\n\n"
        "| Need | Skill | Entry |\n"
        "|---|---|---|\n"
        "| Deploy | deploy | skills/deploy/ |\n"
        "| Operate | operations | skills/operations/ |\n"
        "| Debug | troubleshoot | skills/troubleshoot/ |\n"
    )

    # Init as git repo
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "initial"],
        capture_output=True, check=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com",
             "HOME": str(path.parent), "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin"},
    )

    return f"file://{path}"


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_full_workflow(mock_common, tmp_path):
    """init → pull → list → doctor — full project lifecycle."""
    runner = CliRunner()
    stack_repo = tmp_path / "stack-repo"
    project_dir = tmp_path / "my-project"
    repo_url = _create_fixture_stack(stack_repo)

    # 1. Init a project
    result = runner.invoke(cli, ["init", str(project_dir)])
    assert result.exit_code == 0, result.output
    assert (project_dir / "stacks.lock").exists()
    assert (project_dir / "CLAUDE.md").exists()
    assert (project_dir / ".gitignore").exists()

    # 2. Pull a stack (mock registry lookup to return our local repo)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))

    formula = {
        "name": "test-stack",
        "owner": "test-org",
        "repository": repo_url,
        "version": "1.0.0",
    }

    with patch("agentic_stacks_cli.commands.pull.ensure_registry") as mock_reg, \
         patch("agentic_stacks_cli.commands.pull.load_formula", return_value=formula):
        mock_reg.return_value = tmp_path / "registry"
        result = runner.invoke(cli, [
            "pull", "test-org/test-stack",
            "--path", str(project_dir), "--config", str(config_path),
        ])
    assert result.exit_code == 0, result.output
    assert (project_dir / ".stacks" / "test-stack" / "stack.yaml").exists()
    assert (project_dir / ".stacks" / "test-stack" / "CLAUDE.md").exists()

    # 3. Verify lock file
    lock = yaml.safe_load((project_dir / "stacks.lock").read_text())
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "test-org/test-stack"
    assert lock["stacks"][0]["repository"] == repo_url

    # 4. List stacks
    result = runner.invoke(cli, ["list", "--path", str(project_dir)])
    assert result.exit_code == 0, result.output
    assert "test-org/test-stack" in result.output
    assert "pulled" in result.output

    # 5. Doctor — validate project and stack health
    result = runner.invoke(cli, ["doctor", "--path", str(project_dir)])
    assert result.exit_code == 0, result.output
    assert "test-org/test-stack" in result.output
    assert "skills: 3" in result.output
    assert "healthy" in result.output.lower()
    # No warnings about missing skills
    assert "skill entry not found" not in result.output.lower()


def test_doctor_catches_broken_skills(tmp_path):
    """Doctor should warn when a pulled stack has missing skill entries."""
    runner = CliRunner()
    stack_repo = tmp_path / "stack-repo"
    project_dir = tmp_path / "my-project"
    _create_fixture_stack(stack_repo)

    # Init and pull
    runner.invoke(cli, ["init", str(project_dir)])
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))

    formula = {
        "name": "test-stack", "owner": "test-org",
        "repository": f"file://{stack_repo}", "version": "1.0.0",
    }
    with patch("agentic_stacks_cli.commands.pull.ensure_registry") as mock_reg, \
         patch("agentic_stacks_cli.commands.pull.load_formula", return_value=formula):
        mock_reg.return_value = tmp_path / "registry"
        runner.invoke(cli, [
            "pull", "test-org/test-stack",
            "--path", str(project_dir), "--config", str(config_path),
        ])

    # Break a skill by removing its directory
    import shutil
    shutil.rmtree(project_dir / ".stacks" / "test-stack" / "skills" / "troubleshoot")

    # Doctor should catch it
    result = runner.invoke(cli, ["doctor", "--path", str(project_dir)])
    assert result.exit_code == 0, result.output
    assert "skill entry not found" in result.output.lower()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_then_doctor(mock_common, tmp_path):
    """Doctor on a fresh project with no stacks should work."""
    runner = CliRunner()
    project_dir = tmp_path / "empty-project"

    result = runner.invoke(cli, ["init", str(project_dir)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["doctor", "--path", str(project_dir)])
    assert result.exit_code == 0, result.output
    assert "0 stack(s)" in result.output
    assert "healthy" in result.output.lower()


def test_pull_second_stack(tmp_path):
    """Pulling a second stack adds to the lock file without replacing the first."""
    runner = CliRunner()
    project_dir = tmp_path / "multi-stack"
    runner.invoke(cli, ["init", str(project_dir)])

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))

    # Create two fixture stacks
    for name in ["stack-a", "stack-b"]:
        repo = tmp_path / f"{name}-repo"
        repo.mkdir(parents=True)
        manifest = {
            "name": name, "owner": "test-org", "version": "1.0.0",
            "description": f"{name} stack",
            "repository": f"file://{repo}",
            "target": {"software": name}, "skills": [],
            "depends_on": [], "requires": {},
        }
        (repo / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
        (repo / "skills").mkdir()
        (repo / "CLAUDE.md").write_text(f"# {name}\n")
        subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "initial"],
            capture_output=True, check=True,
            env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
                 "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com",
                 "HOME": str(tmp_path), "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin"},
        )

        formula = {"name": name, "owner": "test-org",
                    "repository": f"file://{repo}", "version": "1.0.0"}
        with patch("agentic_stacks_cli.commands.pull.ensure_registry") as mock_reg, \
             patch("agentic_stacks_cli.commands.pull.load_formula", return_value=formula):
            mock_reg.return_value = tmp_path / "registry"
            result = runner.invoke(cli, [
                "pull", f"test-org/{name}",
                "--path", str(project_dir), "--config", str(config_path),
            ])
            assert result.exit_code == 0, result.output

    # Both stacks in lock
    lock = yaml.safe_load((project_dir / "stacks.lock").read_text())
    names = [s["name"] for s in lock["stacks"]]
    assert "test-org/stack-a" in names
    assert "test-org/stack-b" in names

    # List shows both
    result = runner.invoke(cli, ["list", "--path", str(project_dir)])
    assert "stack-a" in result.output
    assert "stack-b" in result.output
