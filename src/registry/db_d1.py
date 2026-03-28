"""Cloudflare D1 implementation of StacksDB.

Uses the D1 binding (env.DB) via Pyodide JS interop.
D1 methods return JS objects — we convert them to Python dicts.
"""

import json


def _js_to_dict(js_obj):
    """Convert a JS object from D1 result to a Python dict."""
    if js_obj is None:
        return None
    # In Pyodide, JS objects can be converted via .to_py() or dict()
    try:
        return js_obj.to_py()
    except AttributeError:
        return dict(js_obj)


def _js_results_to_list(result):
    """Convert D1 .all() result to a list of dicts."""
    if result is None:
        return []
    try:
        results = result.results
        if results is None:
            return []
        return [_js_to_dict(r) for r in results]
    except AttributeError:
        return []


def _json_loads_safe(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _row_to_version_dict(row):
    """Convert a D1 row to a full version dict."""
    if not row:
        return None
    return {
        "namespace": row.get("ns_name", ""),
        "name": row.get("stack_name", row.get("name", "")),
        "description": row.get("description", ""),
        "version": row.get("version", ""),
        "target_software": row.get("target_software", ""),
        "target_versions": _json_loads_safe(row.get("target_versions"), []),
        "skills": _json_loads_safe(row.get("skills"), []),
        "profiles": _json_loads_safe(row.get("profiles"), {}),
        "depends_on": _json_loads_safe(row.get("depends_on"), []),
        "deprecations": _json_loads_safe(row.get("deprecations"), []),
        "requires": _json_loads_safe(row.get("requires"), {}),
        "digest": row.get("digest", ""),
        "registry_ref": row.get("registry_ref", ""),
        "published_at": row.get("published_at"),
    }


def _row_to_summary(row):
    """Convert a D1 row to a stack list summary."""
    if not row:
        return None
    return {
        "namespace": row.get("ns_name", ""),
        "name": row.get("stack_name", row.get("name", "")),
        "description": row.get("description", ""),
        "version": row.get("version", "0.0.0"),
        "target_software": row.get("target_software", ""),
        "target_versions": _json_loads_safe(row.get("target_versions"), []),
    }


class D1DB:
    """StacksDB backed by Cloudflare D1."""

    def __init__(self, d1_binding):
        self._db = d1_binding

    async def _first(self, sql, *params):
        if params:
            result = await self._db.prepare(sql).bind(*params).first()
        else:
            result = await self._db.prepare(sql).first()
        return _js_to_dict(result)

    async def _all(self, sql, *params):
        if params:
            result = await self._db.prepare(sql).bind(*params).all()
        else:
            result = await self._db.prepare(sql).all()
        return _js_results_to_list(result)

    async def _run(self, sql, *params):
        if params:
            await self._db.prepare(sql).bind(*params).run()
        else:
            await self._db.prepare(sql).run()

    async def list_stacks(self, q=None, namespace=None, target=None,
                    sort="updated", page=1, per_page=20):
        # Build query dynamically
        where_clauses = []
        params = []

        if q:
            where_clauses.append("(s.name LIKE ? OR s.description LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        if namespace:
            where_clauses.append("n.name = ?")
            params.append(namespace)

        where = ""
        if where_clauses:
            where = "WHERE " + " AND ".join(where_clauses)

        order = "s.updated_at DESC" if sort != "name" else "s.name"
        offset = (page - 1) * per_page

        # Count
        count_sql = f"SELECT COUNT(*) as cnt FROM stacks s JOIN namespaces n ON s.namespace_id = n.id {where}"
        count_row = await self._first(count_sql, *params) if params else await self._first(count_sql)
        total = count_row["cnt"] if count_row else 0

        # Fetch stacks with latest version
        sql = f"""
            SELECT s.id as stack_id, s.name as stack_name, s.description, n.name as ns_name,
                   sv.version, sv.target_software, sv.target_versions, sv.digest, sv.registry_ref
            FROM stacks s
            JOIN namespaces n ON s.namespace_id = n.id
            LEFT JOIN stack_versions sv ON sv.id = (
                SELECT id FROM stack_versions WHERE stack_id = s.id ORDER BY published_at DESC LIMIT 1
            )
            {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])
        rows = await self._all(sql, *params) if params else await self._all(sql)

        items = [_row_to_summary(r) for r in rows if r]
        return items, total

    async def get_stack(self, namespace, name):
        sql = """
            SELECT sv.*, s.name as stack_name, s.description, n.name as ns_name
            FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ?
            ORDER BY sv.published_at DESC LIMIT 1
        """
        row = await self._first(sql, namespace, name)
        return _row_to_version_dict(row)

    async def get_stack_version(self, namespace, name, version):
        sql = """
            SELECT sv.*, s.name as stack_name, s.description, n.name as ns_name
            FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ? AND sv.version = ?
        """
        row = await self._first(sql, namespace, name, version)
        return _row_to_version_dict(row)

    async def get_namespace_with_stacks(self, namespace):
        ns = await self._first("SELECT * FROM namespaces WHERE name = ?", namespace)
        if not ns:
            return None
        stacks_sql = """
            SELECT s.id as stack_id, s.name as stack_name, s.description, ? as ns_name,
                   sv.version, sv.target_software, sv.target_versions
            FROM stacks s
            LEFT JOIN stack_versions sv ON sv.id = (
                SELECT id FROM stack_versions WHERE stack_id = s.id ORDER BY published_at DESC LIMIT 1
            )
            WHERE s.namespace_id = ?
        """
        rows = await self._all(stacks_sql, namespace, ns["id"])
        stacks = [_row_to_summary(r) for r in rows if r and r.get("version")]
        return {
            "name": ns["name"],
            "github_org": ns.get("github_org"),
            "verified": bool(ns.get("verified")),
            "stacks": stacks,
        }

    async def create_namespace(self, name, github_org):
        await self._run("INSERT INTO namespaces (name, github_org) VALUES (?, ?)", name, github_org)
        row = await self._first("SELECT * FROM namespaces WHERE name = ?", name)
        return {"id": row["id"], "name": row["name"]}

    async def create_stack(self, namespace, name, description):
        ns = await self._first("SELECT id FROM namespaces WHERE name = ?", namespace)
        await self._run("INSERT INTO stacks (namespace_id, name, description) VALUES (?, ?, ?)",
                  ns["id"], name, description)
        row = await self._first("SELECT * FROM stacks WHERE namespace_id = ? AND name = ?", ns["id"], name)
        return {"id": row["id"], "name": row["name"]}

    async def create_version(self, namespace, name, version_data):
        ns = await self._first("SELECT id FROM namespaces WHERE name = ?", namespace)
        stack = await self._first("SELECT id FROM stacks WHERE namespace_id = ? AND name = ?", ns["id"], name)
        await self._run(
            """INSERT INTO stack_versions
               (stack_id, version, target_software, target_versions, skills, profiles,
                depends_on, deprecations, requires, digest, registry_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            stack["id"],
            version_data.get("version", "0.0.0"),
            version_data.get("target_software", ""),
            version_data.get("target_versions", "[]"),
            version_data.get("skills", "[]"),
            version_data.get("profiles", "{}"),
            version_data.get("depends_on", "[]"),
            version_data.get("deprecations", "[]"),
            version_data.get("requires", "{}"),
            version_data.get("digest", ""),
            version_data.get("registry_ref", ""),
        )
        return {"id": 0, "version": version_data.get("version", "0.0.0")}

    async def version_exists(self, namespace, name, version):
        sql = """
            SELECT 1 as found FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ? AND sv.version = ?
        """
        row = await self._first(sql, namespace, name, version)
        return row is not None

    async def featured_stacks(self, limit=6):
        sql = """
            SELECT s.id as stack_id, s.name as stack_name, s.description, n.name as ns_name,
                   sv.version, sv.target_software, sv.target_versions
            FROM stacks s
            JOIN namespaces n ON s.namespace_id = n.id
            LEFT JOIN stack_versions sv ON sv.id = (
                SELECT id FROM stack_versions WHERE stack_id = s.id ORDER BY published_at DESC LIMIT 1
            )
            ORDER BY s.updated_at DESC LIMIT ?
        """
        rows = await self._all(sql, limit)
        return [_row_to_summary(r) for r in rows if r and r.get("version")]

    async def all_versions(self, namespace, name):
        sql = """
            SELECT sv.version, sv.digest, sv.published_at
            FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ?
            ORDER BY sv.published_at DESC
        """
        rows = await self._all(sql, namespace, name)
        return [{"version": r["version"], "digest": r.get("digest", ""),
                 "published_at": r.get("published_at", "")} for r in rows]
