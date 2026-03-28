"""Cloudflare Workers entry point."""
from workers import WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        from registry.app import create_app
        from registry.db_stub import StubDB

        app = create_app(enable_rate_limit=False, db_factory=lambda: StubDB())
        return await asgi.fetch(app, request, self.env)
