# worker/main.py
"""Cloudflare Workers entry point.

Bridges the FastAPI ASGI app to the Cloudflare Workers runtime.
For local development, use: uvicorn registry.app:app --reload
"""
from asgi import asgi
from registry.app import create_sqlite_app

# Use SQLite for now — D1 integration requires the Workers runtime
# which provides env.DB binding. When deployed to Cloudflare,
# this will be replaced with create_app(db_factory=d1_factory)
app = create_sqlite_app()


async def on_fetch(request, env):
    return await asgi(app, request, env)
