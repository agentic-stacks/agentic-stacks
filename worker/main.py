"""Cloudflare Workers entry point.

Bridges the FastAPI ASGI app to the Cloudflare Workers runtime.
For local development, use: uvicorn registry.app:app --reload
"""
from workers import WorkerEntrypoint
import asgi
from registry.app import create_sqlite_app

app = create_sqlite_app()


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
