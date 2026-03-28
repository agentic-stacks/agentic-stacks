"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from registry.routes.stacks import router as stacks_router
from registry.routes.namespaces import router as namespaces_router
from registry.routes.web import router as web_router
from registry.config import RATE_LIMIT

STATIC_DIR = pathlib.Path(__file__).parent / "static"


def create_app(rate_limit: str | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")

    limit = rate_limit or RATE_LIMIT
    limiter = Limiter(key_func=get_remote_address, default_limits=[limit])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(stacks_router)
    app.include_router(namespaces_router)
    app.include_router(web_router)

    return app


app = create_app()
