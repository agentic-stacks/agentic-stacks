"""Local development entry point. Run with: uvicorn registry.local:app --reload"""
from registry.app import create_sqlite_app

app = create_sqlite_app()
