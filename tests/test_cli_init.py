import yaml
from click.testing import CliRunner
from astack import cli


def test_init_creates_stack_structure(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "my-stack"), "--name", "my-stack", "--namespace", "myorg"])
    assert result.exit_code == 0
    stack_dir = tmp_path / "my-stack"
    assert (stack_dir / "stack.yaml").exists()
    assert (stack_dir / "skills").is_dir()
    assert (stack_dir / "profiles").is_dir()
    assert (stack_dir / "environments").is_dir()
    assert (stack_dir / "src").is_dir()
    assert (stack_dir / "CLAUDE.md").exists()


def test_init_stack_yaml_content(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "test-stack"), "--name", "test-stack", "--namespace", "testorg"])
    manifest = yaml.safe_load((tmp_path / "test-stack" / "stack.yaml").read_text())
    assert manifest["name"] == "test-stack"
    assert manifest["namespace"] == "testorg"
    assert manifest["version"] == "0.1.0"
    assert "skills" in manifest
    assert "profiles" in manifest


def test_init_existing_directory_fails(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "stack.yaml").write_text("name: existing\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target), "--name", "x", "--namespace", "y"])
    assert result.exit_code != 0


def test_init_default_profiles(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "s"), "--name", "s", "--namespace", "n"])
    stack_dir = tmp_path / "s"
    assert (stack_dir / "profiles" / "security").is_dir()
    assert (stack_dir / "environments" / "_schema.json").exists()
