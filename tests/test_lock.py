import yaml
from agentic_stacks_cli.lock import read_lock, write_lock, add_to_lock, remove_from_lock


def test_read_lock_missing_file(tmp_path):
    lock = read_lock(tmp_path / "stacks.lock")
    assert lock == {"stacks": []}


def test_write_and_read_lock(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    lock_data = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc123", "registry": "ghcr.io/agentic-stacks/openstack"}
    ]}
    write_lock(lock_data, lock_path)
    loaded = read_lock(lock_path)
    assert len(loaded["stacks"]) == 1
    assert loaded["stacks"][0]["name"] == "agentic-stacks/openstack"


def test_add_to_lock(tmp_path):
    lock = read_lock(tmp_path / "stacks.lock")
    lock = add_to_lock(lock, name="agentic-stacks/openstack", version="1.3.0",
                       digest="sha256:abc", registry="ghcr.io/agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1
    lock = add_to_lock(lock, name="agentic-stacks/base", version="1.0.0",
                       digest="sha256:def", registry="ghcr.io/agentic-stacks/base")
    assert len(lock["stacks"]) == 2


def test_add_to_lock_updates_existing():
    lock = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:old", "registry": "ghcr.io/agentic-stacks/openstack"}
    ]}
    lock = add_to_lock(lock, name="agentic-stacks/openstack", version="1.4.0",
                       digest="sha256:new", registry="ghcr.io/agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["version"] == "1.4.0"


def test_remove_from_lock():
    lock = {"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack"},
        {"name": "agentic-stacks/base", "version": "1.0.0",
         "digest": "sha256:def", "registry": "ghcr.io/agentic-stacks/base"},
    ]}
    lock = remove_from_lock(lock, name="agentic-stacks/openstack")
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/base"


def test_lock_file_format(tmp_path):
    lock_path = tmp_path / "stacks.lock"
    lock = {"stacks": [{"name": "agentic-stacks/openstack", "version": "1.3.0",
                         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack"}]}
    write_lock(lock, lock_path)
    content = lock_path.read_text()
    assert "stacks:" in content
    assert "sha256:abc" in content
