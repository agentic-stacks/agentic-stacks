import json
from agentic_stacks.state_store import StateStore


def test_empty_store(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    assert store.list() == []


def test_append_and_list(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="operator", outcome="success", details={"version": "1.0"})
    entries = store.list()
    assert len(entries) == 1
    assert entries[0]["action"] == "deploy"
    assert entries[0]["environment"] == "dev"
    assert entries[0]["actor"] == "operator"
    assert entries[0]["outcome"] == "success"
    assert entries[0]["details"] == {"version": "1.0"}
    assert "timestamp" in entries[0]


def test_append_multiple(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="success")
    store.append(action="upgrade", environment="staging", actor="operator", outcome="failed")
    assert len(store.list()) == 3


def test_filter_by_environment(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="deploy", environment="prod", actor="agent", outcome="success")
    dev_entries = store.list(environment="dev")
    assert len(dev_entries) == 1
    assert dev_entries[0]["environment"] == "dev"


def test_filter_by_action(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="success")
    assert len(store.list(action="deploy")) == 1


def test_persistence_across_instances(tmp_path):
    state_file = tmp_path / "state.jsonl"
    StateStore(state_file).append(action="deploy", environment="dev", actor="agent", outcome="success")
    assert len(StateStore(state_file).list()) == 1


def test_last(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    store.append(action="deploy", environment="dev", actor="agent", outcome="success")
    store.append(action="health-check", environment="dev", actor="agent", outcome="failed")
    last = store.last(environment="dev")
    assert last["action"] == "health-check"
    assert last["outcome"] == "failed"


def test_last_empty(tmp_path):
    store = StateStore(tmp_path / "state.jsonl")
    assert store.last() is None
