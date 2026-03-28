"""Append-only state store for tracking actions."""

import json
import pathlib
from datetime import datetime, timezone
from typing import Any


class StateStore:
    def __init__(self, path: pathlib.Path):
        self._path = pathlib.Path(path)

    def append(self, action: str, environment: str, actor: str, outcome: str, details: dict[str, Any] | None = None) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "environment": environment,
            "actor": actor,
            "outcome": outcome,
            "details": details or {},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def list(self, environment: str | None = None, action: str | None = None) -> list[dict]:
        if not self._path.exists():
            return []
        entries = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if environment and entry.get("environment") != environment:
                    continue
                if action and entry.get("action") != action:
                    continue
                entries.append(entry)
        return entries

    def last(self, environment: str | None = None, action: str | None = None) -> dict | None:
        entries = self.list(environment=environment, action=action)
        return entries[-1] if entries else None
