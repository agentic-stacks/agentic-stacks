"""Web page routes — server-rendered HTML."""
import pathlib

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from registry.app import get_db
from registry.config import COMING_SOON

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
_loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
_env = jinja2.Environment(loader=_loader, autoescape=jinja2.select_autoescape(), cache_size=0)
templates = Jinja2Templates(env=_env)

router = APIRouter()


def _is_coming_soon(request: Request) -> bool:
    """Check if coming soon mode is active. Bypass with ?preview=1."""
    if not COMING_SOON:
        return False
    return request.query_params.get("preview") != "1"


def _coming_soon(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "coming_soon.html")


class _Obj:
    """Thin wrapper so templates can use attribute access on dicts."""
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db=Depends(get_db)):
    if _is_coming_soon(request):
        return _coming_soon(request)
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
    if _is_coming_soon(request):
        return _coming_soon(request)
    items, _ = await db.list_stacks(q=q or None, per_page=50)
    stacks_list = []
    for s in items:
        if s.get("version") is not None:
            stacks_list.append({
                "namespace": s["namespace"], "owner": s.get("owner", s["namespace"]), "name": s["name"],
                "version": s["version"], "description": s.get("description", ""),
            })
    return templates.TemplateResponse(request, "stacks.html", {"stacks": stacks_list, "query": q})


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
    if _is_coming_soon(request):
        return _coming_soon(request)
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
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack_obj, "version": version_obj,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })


@router.get("/stacks/{namespace}/{name}/{version}", response_class=HTMLResponse)
async def stack_version_page(request: Request, namespace: str, name: str, version: str,
                       db=Depends(get_db)):
    if _is_coming_soon(request):
        return _coming_soon(request)
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
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack_obj, "version": version_obj,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })


@router.get("/{namespace}", response_class=HTMLResponse)
async def namespace_page(request: Request, namespace: str, db=Depends(get_db)):
    if _is_coming_soon(request):
        return _coming_soon(request)
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
