"""Web page routes — server-rendered HTML."""
import pathlib

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from web.app import get_db
from web.config import BASE_URL

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
_loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
_env = jinja2.Environment(loader=_loader, autoescape=jinja2.select_autoescape(), cache_size=0)
templates = Jinja2Templates(env=_env)

router = APIRouter()





class _Obj:
    """Thin wrapper so templates can use attribute access on dicts."""
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)


@router.get("/favicon.ico")
async def favicon_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/static/favicon.svg", status_code=301)


@router.get("/sitemap.xml")
async def sitemap(request: Request, db=Depends(get_db)):
    items, _ = await db.list_stacks(per_page=100)
    urls = [
        (f"{BASE_URL}/", "daily", "1.0"),
        (f"{BASE_URL}/stacks", "daily", "0.9"),
        (f"{BASE_URL}/about", "monthly", "0.7"),
        (f"{BASE_URL}/docs/getting-started", "monthly", "0.8"),
        (f"{BASE_URL}/docs/authoring", "monthly", "0.8"),
        (f"{BASE_URL}/docs/faq", "monthly", "0.8"),
    ]
    for s in items:
        if s.get("version") is not None:
            urls.append((f"{BASE_URL}/stacks/{s['namespace']}/{s['name']}", "weekly", "0.8"))
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for loc, freq, priority in urls:
        xml_lines.append(f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    xml_lines.append("</urlset>")
    return Response(content="\n".join(xml_lines), media_type="application/xml")


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db=Depends(get_db)):
    featured = await db.featured_stacks(limit=6)
    # Templates expect plain dicts with namespace/name/version/description keys
    featured_dicts = []
    for s in featured:
        if s.get("version") is not None:
            featured_dicts.append({
                "namespace": s["namespace"], "owner": s.get("owner", s["namespace"]), "name": s["name"],
                "version": s["version"], "description": s.get("description", ""),
            })
    return templates.TemplateResponse(request, "home.html", {"featured_stacks": featured_dicts})


@router.get("/stacks", response_class=HTMLResponse)
async def stacks_page(request: Request, q: str = "", db=Depends(get_db)):
    items, total = await db.list_stacks(q=q or None, per_page=50)
    stacks_list = []
    for s in items:
        if s.get("version") is not None:
            skills = s.get("skills", [])
            stacks_list.append({
                "namespace": s["namespace"], "owner": s.get("owner", s["namespace"]), "name": s["name"],
                "version": s["version"], "description": s.get("description", ""),
                "target_software": s.get("target_software", ""),
                "skill_count": len(skills),
                "category": s.get("category", "other"),
            })
    stacks_list.sort(key=lambda s: s["name"])
    categories = sorted(set(s["category"] for s in stacks_list))
    return templates.TemplateResponse(request, "stacks.html", {
        "stacks": stacks_list, "query": q, "total": total, "categories": categories,
    })


@router.get("/web/search", response_class=HTMLResponse)
async def search_fragment(request: Request, q: str = "", db=Depends(get_db)):
    if not q:
        return HTMLResponse("")
    items, _ = await db.list_stacks(q=q, per_page=10)
    stacks_list = []
    for s in items:
        if s.get("version") is not None:
            stacks_list.append({
                "namespace": s["namespace"], "owner": s.get("owner", s["namespace"]), "name": s["name"],
                "version": s["version"], "description": s.get("description", ""),
            })
    return templates.TemplateResponse(request, "_search_results.html", {"stacks": stacks_list, "query": q})


@router.get("/stacks/{namespace}/{name}", response_class=HTMLResponse)
async def stack_detail_page(request: Request, namespace: str, name: str, db=Depends(get_db)):
    stack_data = await db.get_stack(namespace, name)
    if not stack_data:
        raise HTTPException(404, "Not found")
    all_ver = await db.all_versions(namespace, name)

    stack_obj = _Obj(stack_data)
    version_obj = _Obj(stack_data)

    skills = stack_data.get("skills", [])
    profiles = stack_data.get("profiles", {})
    depends_on = stack_data.get("depends_on", [])
    deprecations = stack_data.get("deprecations", [])
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}
    versions_data = [{"version": v["version"], "digest": v.get("digest", ""),
                       "published_at": v.get("published_at", "")}
                      for v in all_ver]
    registry_ref = stack_data.get("registry_ref", "")
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack_obj, "version": version_obj,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data, "registry_ref": registry_ref,
    })


@router.get("/stacks/{namespace}/{name}/{version}", response_class=HTMLResponse)
async def stack_version_page(request: Request, namespace: str, name: str, version: str,
                       db=Depends(get_db)):
    ver_data = await db.get_stack_version(namespace, name, version)
    if not ver_data:
        raise HTTPException(404, "Not found")
    all_ver = await db.all_versions(namespace, name)

    stack_obj = _Obj(ver_data)
    version_obj = _Obj(ver_data)

    skills = ver_data.get("skills", [])
    profiles = ver_data.get("profiles", {})
    depends_on = ver_data.get("depends_on", [])
    deprecations = ver_data.get("deprecations", [])
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}
    versions_data = [{"version": v["version"], "digest": v.get("digest", ""),
                       "published_at": v.get("published_at", "")}
                      for v in all_ver]
    registry_ref = ver_data.get("registry_ref", "")
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack_obj, "version": version_obj,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data, "registry_ref": registry_ref,
    })


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request, db=Depends(get_db)):
    items, _ = await db.list_stacks(per_page=100)
    lines = [
        "# Agentic Stacks",
        "",
        "Installable skill packs that give AI coding agents deep domain expertise.",
        "Pull a stack into your project and the agent knows how to deploy, manage,",
        "troubleshoot, and upgrade the target software.",
        "",
        "Works with Claude Code, Codex CLI, Gemini CLI, Cursor, and any agent",
        "that reads markdown.",
        "",
        "## Quick Start",
        "",
        "```",
        "pipx install agentic-stacks",
        "agentic-stacks init my-project",
        "cd my-project",
        "agentic-stacks pull kubernetes-talos",
        "```",
        "",
        "Every project auto-includes common-skills (training, guided walkthroughs,",
        "orientation, feedback capture). Users can ask:",
        "- \"train me on this stack\" — interactive learning",
        "- \"guide me through [task]\" — step-by-step walkthrough",
        "- \"what can you help me with?\" — project orientation",
        "",
        "## Available Stacks",
        "",
    ]
    for s in sorted(items, key=lambda x: x.get("name", "")):
        if s.get("version") is not None:
            name = f"{s['namespace']}/{s['name']}"
            desc = s.get("description", "").strip()
            url = f"{BASE_URL}/stacks/{s['namespace']}/{s['name']}"
            lines.append(f"- [{name}]({url}): {desc}")
    lines.extend([
        "",
        "## Links",
        "",
        f"- About: {BASE_URL}/about",
        f"- Browse: {BASE_URL}/stacks",
        f"- Getting Started: {BASE_URL}/docs/getting-started",
        f"- Authoring Guide: {BASE_URL}/docs/authoring",
        f"- Common Skills: https://github.com/agentic-stacks/common-skills",
        "- GitHub: https://github.com/agentic-stacks",
    ])
    return PlainTextResponse("\n".join(lines))


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html")


@router.get("/docs/getting-started", response_class=HTMLResponse)
async def getting_started_page(request: Request):
    return templates.TemplateResponse(request, "getting_started.html")


@router.get("/docs/authoring", response_class=HTMLResponse)
async def authoring_page(request: Request):
    return templates.TemplateResponse(request, "authoring.html")


@router.get("/docs/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    return templates.TemplateResponse(request, "faq.html")


@router.get("/{namespace}", response_class=HTMLResponse)
async def namespace_page(request: Request, namespace: str, db=Depends(get_db)):
    ns_data = await db.get_namespace_with_stacks(namespace)
    if not ns_data:
        raise HTTPException(404, "Not found")
    ns_obj = _Obj(ns_data)
    items = []
    for s in ns_data.get("stacks", []):
        if s.get("version") is not None:
            items.append({
                "namespace": s["namespace"], "owner": s.get("owner", s["namespace"]), "name": s["name"],
                "version": s["version"], "description": s.get("description", ""),
            })
    return templates.TemplateResponse(request, "namespace.html", {"ns": ns_obj, "stacks": items})
