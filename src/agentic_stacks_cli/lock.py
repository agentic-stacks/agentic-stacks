"""stacks.lock reading, writing, and manipulation."""

import pathlib
import yaml


def read_lock(path: pathlib.Path) -> dict:
    path = pathlib.Path(path)
    if not path.exists():
        return {"stacks": []}
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "stacks" not in data:
        return {"stacks": []}
    return data


def write_lock(lock: dict, path: pathlib.Path) -> None:
    path = pathlib.Path(path)
    with open(path, "w") as f:
        yaml.dump(lock, f, default_flow_style=False, sort_keys=False)


def add_to_lock(lock: dict, name: str, version: str, digest: str, registry: str) -> dict:
    stacks = lock.get("stacks", [])
    for i, entry in enumerate(stacks):
        if entry["name"] == name:
            stacks[i] = {"name": name, "version": version, "digest": digest, "registry": registry}
            return {"stacks": stacks}
    stacks.append({"name": name, "version": version, "digest": digest, "registry": registry})
    return {"stacks": stacks}


def remove_from_lock(lock: dict, name: str) -> dict:
    stacks = [s for s in lock.get("stacks", []) if s["name"] != name]
    return {"stacks": stacks}
