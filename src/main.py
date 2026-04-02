"""Cloudflare Workers entry point."""
import os

from workers import WorkerEntrypoint

_app = None


def _get_app(env=None):
    global _app
    if _app is None:
        # Expose worker vars to os.environ so config.py can read them
        if env is not None:
            for key in ("BASE_URL", "ENVIRONMENT"):
                val = getattr(env, key, None)
                if val is not None:
                    os.environ[key] = str(val)

        from web.app import create_app
        from web.db_formulas import FormulaDB
        from web.formula_data import FORMULAS

        def db_factory():
            return FormulaDB(FORMULAS)

        _app = create_app(enable_rate_limit=False, db_factory=db_factory)
    return _app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        return await asgi.fetch(_get_app(self.env), request, self.env)
