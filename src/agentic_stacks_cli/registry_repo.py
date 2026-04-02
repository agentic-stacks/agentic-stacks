"""Local registry repo — read, search, and write formula YAML files."""

import pathlib
import subprocess
from typing import Any

import yaml


Formula = dict[str, Any]

STACKS_DIR = "stacks"
DEFAULT_REGISTRY_REPO = "https://github.com/agentic-stacks/registry"
DEFAULT_CONFIG_DIR = pathlib.Path.home() / ".config" / "agentic-stacks"


def registry_cache_path(config_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Return the path to the local registry cache."""
    base = config_dir if config_dir else DEFAULT_CONFIG_DIR
    return base / "registry"


def ensure_registry(
    repo_url: str = DEFAULT_REGISTRY_REPO,
    cache_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    """Clone or update the local registry cache. Returns the cache path."""
    if cache_dir is None:
        cache_dir = registry_cache_path()

    if (cache_dir / ".git").is_dir():
        subprocess.run(
            ["git", "-C", str(cache_dir), "fetch", "--quiet"],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(cache_dir), "reset", "--hard", "origin/main", "--quiet"],
            capture_output=True, text=True,
        )
    else:
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", repo_url, str(cache_dir)],
            capture_output=True, text=True,
        )

    return cache_dir


def load_formula(registry_path: pathlib.Path, owner: str, name: str) -> Formula:
    """Load a single formula by owner/name."""
    formula_path = registry_path / STACKS_DIR / owner / f"{name}.yaml"
    if not formula_path.exists():
        raise FileNotFoundError(f"Formula not found: {owner}/{name}")
    with open(formula_path) as f:
        return yaml.safe_load(f)


def list_formulas(registry_path: pathlib.Path) -> list[Formula]:
    """List all formulas in the registry."""
    stacks_dir = registry_path / STACKS_DIR
    if not stacks_dir.exists():
        return []
    formulas = []
    for owner_dir in sorted(stacks_dir.iterdir()):
        if not owner_dir.is_dir():
            continue
        for formula_file in sorted(owner_dir.glob("*.yaml")):
            with open(formula_file) as f:
                formulas.append(yaml.safe_load(f))
    return formulas


def search_formulas(registry_path: pathlib.Path, query: str) -> list[Formula]:
    """Search formulas by name, description, target software, or skill names."""
    query_lower = query.lower()
    results = []
    for formula in list_formulas(registry_path):
        searchable = " ".join([
            formula.get("name", ""),
            formula.get("description", ""),
            formula.get("owner", ""),
            formula.get("target", {}).get("software", ""),
            " ".join(s.get("name", "") + " " + s.get("description", "")
                     for s in formula.get("skills", [])),
        ]).lower()
        if query_lower in searchable:
            results.append(formula)
    return results


def write_formula(registry_path: pathlib.Path, formula: Formula) -> pathlib.Path:
    """Write a formula YAML file to the registry directory."""
    owner = formula["owner"]
    name = formula["name"]
    owner_dir = registry_path / STACKS_DIR / owner
    owner_dir.mkdir(parents=True, exist_ok=True)
    formula_path = owner_dir / f"{name}.yaml"
    with open(formula_path, "w") as f:
        yaml.dump(formula, f, default_flow_style=False, sort_keys=False)
    return formula_path
