"""Cloudflare Workers entry point.

For local development, use: uvicorn registry.local:app --reload
"""
from workers import WorkerEntrypoint
import asgi

_app = None


def _get_app():
    global _app
    if _app is None:
        from registry.app import create_app
        _app = create_app(enable_rate_limit=False)
    return _app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(_get_app(), request, self.env)
