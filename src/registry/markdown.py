"""Markdown rendering utility."""
import mistune

_renderer = mistune.create_markdown(escape=False)

def render_markdown(text: str) -> str:
    if not text:
        return ""
    return _renderer(text)
