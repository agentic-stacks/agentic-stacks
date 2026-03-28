"""Diff current vs proposed configuration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiffEntry:
    path: str
    old: Any
    new: Any
    kind: str  # "added", "removed", "changed"

    def format(self) -> str:
        if self.kind == "added":
            return f"  + {self.path}: {self.new!r}"
        elif self.kind == "removed":
            return f"  - {self.path}: {self.old!r}"
        else:
            return f"  ~ {self.path}: {self.old!r} -> {self.new!r}"


def diff_configs(old: dict, new: dict, _prefix: str = "") -> list[DiffEntry]:
    entries = []
    all_keys = sorted(set(list(old.keys()) + list(new.keys())))
    for key in all_keys:
        path = f"{_prefix}.{key}" if _prefix else key
        in_old = key in old
        in_new = key in new
        if in_old and not in_new:
            entries.append(DiffEntry(path=path, old=old[key], new=None, kind="removed"))
        elif in_new and not in_old:
            entries.append(DiffEntry(path=path, old=None, new=new[key], kind="added"))
        elif isinstance(old[key], dict) and isinstance(new[key], dict):
            entries.extend(diff_configs(old[key], new[key], _prefix=path))
        elif old[key] != new[key]:
            entries.append(DiffEntry(path=path, old=old[key], new=new[key], kind="changed"))
    return entries
