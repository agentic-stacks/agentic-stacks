"""Formula-backed database — reads from bundled Python data, no external DB needed."""


class FormulaDB:
    """StacksDB implementation backed by in-memory formula data.

    Replaces D1/SQLite. Data is bundled into the Worker at deploy time
    by generate_formula_data.py.
    """

    def __init__(self, formulas: list[dict]):
        self._formulas = formulas

    async def list_stacks(self, q: str | None = None, namespace: str | None = None,
                    target: str | None = None, sort: str = "updated",
                    page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        results = list(self._formulas)

        if namespace:
            results = [f for f in results if f.get("owner") == namespace]

        if target:
            t = target.lower()
            results = [f for f in results
                       if t in (f.get("target", {}).get("software", "") or "").lower()]

        if q:
            q_lower = q.lower()
            results = [f for f in results
                       if q_lower in f.get("name", "").lower()
                       or q_lower in f.get("description", "").lower()
                       or q_lower in (f.get("target", {}).get("software", "") or "").lower()
                       or any(q_lower in s.get("name", "").lower() or q_lower in s.get("description", "").lower()
                              for s in f.get("skills", []))]

        results.sort(key=lambda f: f.get("name", ""))

        total = len(results)
        start = (page - 1) * per_page
        page_results = results[start:start + per_page]

        return [self._to_stack_dict(f) for f in page_results], total

    async def get_stack(self, namespace: str, name: str) -> dict | None:
        for f in self._formulas:
            if f.get("owner") == namespace and f.get("name") == name:
                return self._to_stack_dict(f)
        return None

    async def get_stack_version(self, namespace: str, name: str, version: str) -> dict | None:
        for f in self._formulas:
            if f.get("owner") == namespace and f.get("name") == name:
                if f.get("version") == version:
                    return self._to_stack_dict(f)
        return None

    async def get_namespace_with_stacks(self, namespace: str) -> dict | None:
        stacks = [self._to_stack_dict(f) for f in self._formulas if f.get("owner") == namespace]
        if not stacks:
            return None
        return {
            "name": namespace,
            "github_org": namespace,
            "verified": True,
            "stacks": stacks,
        }

    async def create_namespace(self, name: str, github_org: str) -> dict:
        return {"name": name, "github_org": github_org}

    async def create_stack(self, namespace: str, name: str, description: str) -> dict:
        return {"namespace": namespace, "name": name, "description": description}

    async def create_version(self, namespace: str, name: str, version_data: dict) -> dict:
        return version_data

    async def version_exists(self, namespace: str, name: str, version: str) -> bool:
        for f in self._formulas:
            if f.get("owner") == namespace and f.get("name") == name and f.get("version") == version:
                return True
        return False

    async def featured_stacks(self, limit: int = 6) -> list[dict]:
        results = [self._to_stack_dict(f) for f in self._formulas]
        results.sort(key=lambda s: s.get("name", ""))
        return results[:limit]

    async def all_versions(self, namespace: str, name: str) -> list[dict]:
        for f in self._formulas:
            if f.get("owner") == namespace and f.get("name") == name:
                return [self._to_stack_dict(f)]
        return []

    def _to_stack_dict(self, formula: dict) -> dict:
        owner = formula.get("owner", "")
        return {
            "namespace": owner,
            "owner": owner,
            "name": formula.get("name", ""),
            "description": formula.get("description", ""),
            "category": formula.get("category", "other"),
            "version": formula.get("version", "0.0.1"),
            "target_software": formula.get("target", {}).get("software", ""),
            "target_versions": formula.get("target", {}).get("versions", []),
            "skills": formula.get("skills", []),
            "profiles": {},
            "depends_on": formula.get("depends_on", []),
            "deprecations": [],
            "requires": formula.get("requires", {}),
            "digest": "",
            "registry_ref": formula.get("repository", ""),
            "published_at": None,
        }
