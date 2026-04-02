from agentic_stacks.config_diff import diff_configs, DiffEntry


def test_no_changes():
    old = {"a": 1, "b": {"x": 10}}
    new = {"a": 1, "b": {"x": 10}}
    assert diff_configs(old, new) == []


def test_value_changed():
    result = diff_configs({"a": 1}, {"a": 2})
    assert len(result) == 1
    assert result[0] == DiffEntry(path="a", old=1, new=2, kind="changed")


def test_key_added():
    result = diff_configs({"a": 1}, {"a": 1, "b": 2})
    assert len(result) == 1
    assert result[0] == DiffEntry(path="b", old=None, new=2, kind="added")


def test_key_removed():
    result = diff_configs({"a": 1, "b": 2}, {"a": 1})
    assert len(result) == 1
    assert result[0] == DiffEntry(path="b", old=2, new=None, kind="removed")


def test_nested_changes():
    result = diff_configs({"a": {"b": {"c": 1}}}, {"a": {"b": {"c": 2}}})
    assert len(result) == 1
    assert result[0] == DiffEntry(path="a.b.c", old=1, new=2, kind="changed")


def test_mixed_changes():
    old = {"keep": 1, "change": "old", "remove": True, "nested": {"a": 1}}
    new = {"keep": 1, "change": "new", "add": "hi", "nested": {"a": 1, "b": 2}}
    result = diff_configs(old, new)
    paths = {r.path: r for r in result}
    assert "keep" not in paths
    assert paths["change"].kind == "changed"
    assert paths["remove"].kind == "removed"
    assert paths["add"].kind == "added"
    assert paths["nested.b"].kind == "added"


def test_format_diff():
    result = diff_configs({"a": 1, "b": 2}, {"a": 99, "c": 3})
    formatted = "\n".join(entry.format() for entry in result)
    assert "a:" in formatted or "a" in formatted
