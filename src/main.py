"""Cloudflare Workers entry point."""
from workers import WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        from registry.app import create_app
        app = create_app(enable_rate_limit=False)
        return await asgi.fetch(app, request, self.env)
