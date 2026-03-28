"""Stub database implementation for initial deployment.

Returns empty results for all queries. Used when no real database
backend is configured (e.g., first Cloudflare Workers deploy before
D1 is fully wired).
"""


class StubDB:
    async def list_stacks(self, q=None, namespace=None, target=None,
                    sort="updated", page=1, per_page=20):
        return [], 0

    async def get_stack(self, namespace, name):
        return None

    async def get_stack_version(self, namespace, name, version):
        return None

    async def get_namespace_with_stacks(self, namespace):
        return None

    async def create_namespace(self, name, github_org):
        return {"id": 0, "name": name}

    async def create_stack(self, namespace, name, description):
        return {"id": 0, "name": name}

    async def create_version(self, namespace, name, version_data):
        return {"id": 0, "version": version_data.get("version", "0.0.0")}

    async def version_exists(self, namespace, name, version):
        return False

    async def featured_stacks(self, limit=6):
        return []

    async def all_versions(self, namespace, name):
        return []
