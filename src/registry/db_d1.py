# src/registry/db_d1.py
"""Cloudflare D1 implementation of StacksDB.

This module documents the SQL queries for D1. On Cloudflare Workers,
the D1 binding (env.DB) is accessed via JavaScript interop through Pyodide.
Methods here are async and use the D1 prepare/bind/all/first/run API.

For local dev and tests, use db_sqlite.py instead.
"""

import json


class D1DB:
    """StacksDB implementation for Cloudflare D1.

    Usage in a Cloudflare Worker:
        db = D1DB(env.DB)  # env.DB is the D1 binding from wrangler.toml
    """

    def __init__(self, d1_binding):
        self._db = d1_binding

    # Note: All methods below are documented with their SQL queries.
    # In the Cloudflare Worker runtime, these would use:
    #   await self._db.prepare(sql).bind(*params).first()  -- for single row
    #   await self._db.prepare(sql).bind(*params).all()    -- for multiple rows
    #   await self._db.prepare(sql).bind(*params).run()    -- for INSERT/UPDATE/DELETE

    # The sync protocol methods raise NotImplementedError because D1 is async.
    # When running on Cloudflare, the worker entry point handles the async bridge.

    def list_stacks(self, q=None, namespace=None, target=None,
                    sort="updated", page=1, per_page=20):
        """
        SQL:
            SELECT s.*, n.name as ns_name FROM stacks s
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE s.name LIKE ? OR s.description LIKE ?  -- if q
            AND n.name = ?  -- if namespace
            ORDER BY s.updated_at DESC  -- or s.name
            LIMIT ? OFFSET ?

        For each stack, get latest version:
            SELECT * FROM stack_versions WHERE stack_id = ?
            ORDER BY published_at DESC LIMIT 1
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def get_stack(self, namespace, name):
        """
        SQL:
            SELECT s.*, n.name as ns_name FROM stacks s
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ?

        Then latest version:
            SELECT * FROM stack_versions WHERE stack_id = ?
            ORDER BY published_at DESC LIMIT 1
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def get_stack_version(self, namespace, name, version):
        """
        SQL:
            SELECT sv.*, s.name as stack_name, s.description, n.name as ns_name
            FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ? AND sv.version = ?
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def get_namespace_with_stacks(self, namespace):
        """
        SQL:
            SELECT * FROM namespaces WHERE name = ?
        Then:
            SELECT s.* FROM stacks s WHERE s.namespace_id = ?
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def create_namespace(self, name, github_org):
        """
        SQL: INSERT INTO namespaces (name, github_org) VALUES (?, ?)
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def create_stack(self, namespace, name, description):
        """
        SQL:
            SELECT id FROM namespaces WHERE name = ?
            INSERT INTO stacks (namespace_id, name, description) VALUES (?, ?, ?)
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def create_version(self, namespace, name, version_data):
        """
        SQL:
            SELECT s.id FROM stacks s JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ?

            INSERT INTO stack_versions (stack_id, version, target_software, ...)
            VALUES (?, ?, ?, ...)
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def version_exists(self, namespace, name, version):
        """
        SQL:
            SELECT 1 FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ? AND sv.version = ?
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def featured_stacks(self, limit=6):
        """
        SQL:
            SELECT s.*, n.name as ns_name FROM stacks s
            JOIN namespaces n ON s.namespace_id = n.id
            ORDER BY s.updated_at DESC LIMIT ?
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")

    def all_versions(self, namespace, name):
        """
        SQL:
            SELECT sv.version, sv.digest, sv.published_at
            FROM stack_versions sv
            JOIN stacks s ON sv.stack_id = s.id
            JOIN namespaces n ON s.namespace_id = n.id
            WHERE n.name = ? AND s.name = ?
            ORDER BY sv.published_at DESC
        """
        raise NotImplementedError("Use async D1 binding in Cloudflare Worker")
