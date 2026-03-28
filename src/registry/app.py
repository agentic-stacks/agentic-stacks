"""FastAPI application factory."""
from fastapi import FastAPI
from registry.routes.stacks import router as stacks_router

def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Stacks Registry", version="0.1.0")
    app.include_router(stacks_router)
    return app

app = create_app()
