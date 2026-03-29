"""Registry server configuration."""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./agentic_stacks_registry.db")
GITHUB_API_URL = "https://api.github.com"
RATE_LIMIT = os.environ.get("RATE_LIMIT", "60/minute")
COMING_SOON = os.environ.get("COMING_SOON", "false").lower() in ("true", "1", "yes")
