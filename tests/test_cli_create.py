import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def test_create_with_owner_name(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "myorg/my-stack", str(tmp_path / "my-stack")]
    )
    assert result.exit_code == 0, result.output
    stack_dir = tmp_path / "my-stack"
    assert (stack_dir / "stack.yaml").exists()
    assert (stack_dir / "skills").is_dir()
    assert (stack_dir / "skills" / "training" / "README.md").exists()
    assert (stack_dir / "CLAUDE.md").exists()
    assert (stack_dir / "README.md").exists()


def test_create_stack_yaml_uses_owner(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["create", "myorg/my-stack", str(tmp_path / "my-stack")])
    manifest = yaml.safe_load((tmp_path / "my-stack" / "stack.yaml").read_text())
    assert manifest["name"] == "my-stack"
    assert manifest["owner"] == "myorg"
    assert "namespace" not in manifest
    assert len(manifest["skills"]) == 1
    assert manifest["skills"][0]["name"] == "training"
    assert manifest["skills"][0]["entry"] == "skills/training/"


def test_create_infers_path_from_name(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli, ["create", "myorg/test-stack"])
        assert result.exit_code == 0, result.output
        from pathlib import Path

        assert (Path(td) / "test-stack" / "stack.yaml").exists()


def test_create_existing_directory_fails(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "stack.yaml").write_text("name: existing\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "org/existing", str(target)])
    assert result.exit_code != 0


def test_create_bare_name_fails(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "no-slash", str(tmp_path / "x")])
    assert result.exit_code != 0


def test_create_claude_md_has_authoring_guide(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["create", "myorg/my-stack", str(tmp_path / "my-stack")])
    claude = (tmp_path / "my-stack" / "CLAUDE.md").read_text()
    assert "authoring" in claude.lower()
    assert "Routing Table" in claude
    assert "training" in claude


def test_create_readme(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["create", "myorg/my-stack", str(tmp_path / "my-stack")])
    readme = (tmp_path / "my-stack" / "README.md").read_text()
    assert "my-stack" in readme
    assert "myorg/my-stack" in readme
    assert "agentic-stacks pull" in readme


def test_create_minimal_scaffold(tmp_path):
    """Scaffold should be minimal — just skills dir, no profiles/environments/src."""
    runner = CliRunner()
    runner.invoke(cli, ["create", "org/s", str(tmp_path / "s")])
    stack_dir = tmp_path / "s"
    assert (stack_dir / "skills").is_dir()
    assert (stack_dir / "skills" / "training").is_dir()
    assert not (stack_dir / "profiles").exists()
    assert not (stack_dir / "environments").exists()
    assert not (stack_dir / "src").exists()
    assert not (stack_dir / "overrides").exists()


def test_create_training_skill_content(tmp_path):
    """Training skill should contain pedagogical instructions referencing the stack name."""
    runner = CliRunner()
    runner.invoke(cli, ["create", "myorg/my-stack", str(tmp_path / "my-stack")])
    training = (tmp_path / "my-stack" / "skills" / "training" / "README.md").read_text()
    assert "Training Mode" in training
    assert "my-stack" in training
    assert "Assess the learner" in training
    assert "Build a curriculum" in training
    assert "Quiz me" in training
