"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.config import RATE_LIMIT

STATIC_DIR = pathlib.Path(__file__).parent / "static"

_db_factory = None


async def get_db():
    if _db_factory is None:
        raise RuntimeError("Database not configured")
    db = _db_factory()
    try:
        yield db
    finally:
        if hasattr(db, "close"):
            db.close()


def create_app(rate_limit: str | None = None, db_factory=None, enable_rate_limit: bool = True) -> FastAPI:
    global _db_factory

    from web.routes.stacks import router as stacks_router
    from web.routes.namespaces import router as namespaces_router
    from web.routes.web import router as web_router

    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")

    if enable_rate_limit:
        try:
            from slowapi import Limiter, _rate_limit_exceeded_handler
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded
            from slowapi.middleware import SlowAPIMiddleware

            limit = rate_limit or RATE_LIMIT
            limiter = Limiter(key_func=get_remote_address, default_limits=[limit])
            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            app.add_middleware(SlowAPIMiddleware)
        except (ImportError, RuntimeError):
            pass  # Skip rate limiting if slowapi unavailable or threads not supported

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(stacks_router)
    app.include_router(namespaces_router)
    app.include_router(web_router)

    if db_factory:
        _db_factory = db_factory

    return app


def create_formula_app(formulas: list[dict] | None = None, rate_limit: str | None = None) -> FastAPI:
    """Create app with formula backend — for local dev and production."""
    from web.db_formulas import FormulaDB

    if formulas is None:
        from web.formula_data import FORMULAS
        formulas = FORMULAS

    def factory():
        return FormulaDB(formulas)

    return create_app(rate_limit=rate_limit, db_factory=factory)
