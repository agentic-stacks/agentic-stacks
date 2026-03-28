"""Cloudflare Workers entry point.

For local development, use: uvicorn registry.local:app --reload
"""
from workers import WorkerEntrypoint
import asgi
from registry.app import create_app

# CF Workers doesn't support threads (needed by slowapi's in-memory store)
# Rate limiting on CF is handled by their built-in DDoS protection instead
app = create_app(enable_rate_limit=False)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
