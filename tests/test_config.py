import yaml
from agentic_stacks_cli.config import load_config, save_config, default_config


def test_default_config():
    cfg = default_config()
    assert cfg["registry_repo"] == "https://github.com/agentic-stacks/registry"
    assert cfg["default_namespace"] == "agentic-stacks"
    assert cfg["api_url"] == "https://agentic-stacks.com/api/v1"
    assert cfg["token"] is None


def test_load_config_missing_file(tmp_path):
    cfg = load_config(tmp_path / "config.yaml")
    assert cfg["registry_repo"] == "https://github.com/agentic-stacks/registry"
    assert cfg["token"] is None


def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    cfg = default_config()
    cfg["token"] = "ghp_test123"
    cfg["default_namespace"] = "myorg"
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded["token"] == "ghp_test123"
    assert loaded["default_namespace"] == "myorg"
    assert loaded["registry_repo"] == "https://github.com/agentic-stacks/registry"


def test_load_config_merges_with_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "abc"}))
    loaded = load_config(config_path)
    assert loaded["token"] == "abc"
    assert loaded["registry_repo"] == "https://github.com/agentic-stacks/registry"
