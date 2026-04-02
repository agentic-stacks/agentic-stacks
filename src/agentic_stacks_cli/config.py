"""CLI configuration loading and saving."""

import pathlib
from typing import Any

import yaml

CONFIG_DEFAULTS = {
    "registry_repo": "https://github.com/agentic-stacks/registry",
    "default_namespace": "agentic-stacks",
    "api_url": "https://agentic-stacks.com/api/v1",
    "token": None,
}

DEFAULT_CONFIG_DIR = pathlib.Path.home() / ".config" / "agentic-stacks"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"


def default_config() -> dict[str, Any]:
    return dict(CONFIG_DEFAULTS)


def load_config(path: pathlib.Path | None = None) -> dict[str, Any]:
    path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    cfg = default_config()
    if path.exists():
        with open(path) as f:
            user_cfg = yaml.safe_load(f)
        if isinstance(user_cfg, dict):
            cfg.update(user_cfg)
    return cfg


def save_config(config: dict[str, Any], path: pathlib.Path | None = None) -> None:
    path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
