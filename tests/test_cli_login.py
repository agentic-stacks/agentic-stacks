import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def test_login_saves_token(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--token", "ghp_test123", "--config", str(config_path)])
    assert result.exit_code == 0
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["token"] == "ghp_test123"


def test_login_shows_success_message(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--token", "ghp_test", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "logged in" in result.output.lower() or "saved" in result.output.lower()


def test_login_no_token_prompts(tmp_path):
    config_path = tmp_path / "config.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "--config", str(config_path)], input="ghp_from_prompt\n")
    assert result.exit_code == 0
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["token"] == "ghp_from_prompt"
