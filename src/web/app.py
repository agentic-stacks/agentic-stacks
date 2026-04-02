"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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


def create_app(db_factory=None) -> FastAPI:
    global _db_factory

    from web.routes.stacks import router as stacks_router
    from web.routes.namespaces import router as namespaces_router
    from web.routes.web import router as web_router

    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(stacks_router)
    app.include_router(namespaces_router)
    app.include_router(web_router)

    if db_factory:
        _db_factory = db_factory

    return app


def create_formula_app(formulas: list[dict] | None = None) -> FastAPI:
    """Create app with formula backend — for local dev and production."""
    from web.db_formulas import FormulaDB

    if formulas is None:
        from web.formula_data import FORMULAS
        formulas = FORMULAS

    def factory():
        return FormulaDB(formulas)

    return create_app(db_factory=factory)
