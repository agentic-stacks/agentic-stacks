import pathlib
import pytest
import yaml

from agentic_stacks_cli.registry_repo import (
    load_formula,
    list_formulas,
    search_formulas,
    write_formula,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


def test_load_formula():
    formula = load_formula(FIXTURES, "agentic-stacks", "openstack-kolla")
    assert formula["name"] == "openstack-kolla"
    assert formula["owner"] == "agentic-stacks"
    assert formula["repository"] == "https://github.com/agentic-stacks/openstack-kolla"
    assert len(formula["skills"]) > 0


def test_load_formula_not_found():
    with pytest.raises(FileNotFoundError):
        load_formula(FIXTURES, "agentic-stacks", "nonexistent")


def test_list_formulas():
    formulas = list_formulas(FIXTURES)
    names = [f["name"] for f in formulas]
    assert "openstack-kolla" in names
    assert "kubernetes-talos" in names
    assert "hardware-dell" in names


def test_list_formulas_empty(tmp_path):
    formulas = list_formulas(tmp_path)
    assert formulas == []


def test_search_by_name():
    results = search_formulas(FIXTURES, "openstack")
    assert any(f["name"] == "openstack-kolla" for f in results)


def test_search_by_description():
    results = search_formulas(FIXTURES, "kubernetes")
    assert any(f["name"] == "kubernetes-talos" for f in results)


def test_search_by_target():
    results = search_formulas(FIXTURES, "talos-linux")
    assert any(f["name"] == "kubernetes-talos" for f in results)


def test_search_by_skill():
    results = search_formulas(FIXTURES, "RAID")
    assert any(f["name"] == "hardware-dell" for f in results)


def test_search_no_match():
    results = search_formulas(FIXTURES, "zzz-nonexistent-zzz")
    assert results == []


def test_search_case_insensitive():
    results = search_formulas(FIXTURES, "OPENSTACK")
    assert any(f["name"] == "openstack-kolla" for f in results)


def test_write_formula(tmp_path):
    formula = {
        "name": "test-stack",
        "owner": "test-org",
        "version": "1.0.0",
        "repository": "https://github.com/test-org/test-stack",
        "tag": "v1.0.0",

        "description": "A test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "description": "Deploy it"}],
        "depends_on": [],
        "requires": {"tools": ["test-tool"]},
    }
    write_formula(tmp_path, formula)
    written = tmp_path / "stacks" / "test-org" / "test-stack.yaml"
    assert written.exists()
    loaded = yaml.safe_load(written.read_text())
    assert loaded["name"] == "test-stack"
    assert loaded["owner"] == "test-org"
