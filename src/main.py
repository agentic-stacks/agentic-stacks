"""Cloudflare Workers entry point.

For local development, use: uvicorn registry.local:app --reload
"""
from workers import WorkerEntrypoint
import asgi
from registry.app import create_app

# Create app without SQLite — D1 will be wired via env binding
app = create_app()


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
