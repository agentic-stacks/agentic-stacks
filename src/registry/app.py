"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from registry.config import RATE_LIMIT

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

    from registry.routes.stacks import router as stacks_router
    from registry.routes.namespaces import router as namespaces_router
    from registry.routes.web import router as web_router

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


def create_sqlite_app(rate_limit: str | None = None) -> FastAPI:
    """Create app with SQLite backend — for local dev."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from registry.database import Base
    from registry.db_sqlite import SQLiteDB

    engine = create_engine("sqlite:///./agentic_stacks_registry.db",
                          connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def factory():
        return SQLiteDB(Session())

    return create_app(rate_limit=rate_limit, db_factory=factory)
