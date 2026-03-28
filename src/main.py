"""Cloudflare Workers entry point."""
from workers import WorkerEntrypoint

# Module-level ref to the D1 binding — set per request by the fetch handler
_d1_binding = None
_app = None


def _get_app():
    global _app
    if _app is None:
        from registry.app import create_app
        from registry.db_d1 import D1DB

        def db_factory():
            return D1DB(_d1_binding)

        _app = create_app(enable_rate_limit=False, db_factory=db_factory)
    return _app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        global _d1_binding
        import asgi
        _d1_binding = self.env.DB
        return await asgi.fetch(_get_app(), request, self.env)
