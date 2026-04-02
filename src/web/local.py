"""Local development entry point. Run with: uvicorn registry.local:app --reload"""
from web.app import create_formula_app

app = create_formula_app()
