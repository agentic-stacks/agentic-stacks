"""Local registry repo — read, search, and write formula YAML files."""

import pathlib
from typing import Any

import yaml


Formula = dict[str, Any]

STACKS_DIR = "stacks"


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
