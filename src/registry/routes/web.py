"""Web page routes — server-rendered HTML."""
import json
import pathlib

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
_loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
_env = jinja2.Environment(loader=_loader, autoescape=jinja2.select_autoescape(), cache_size=0)
templates = Jinja2Templates(env=_env)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db)):
    stacks = db.query(Stack).join(Namespace).order_by(Stack.updated_at.desc()).limit(6).all()
    featured = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            featured.append({
                "namespace": stack.namespace.name, "name": stack.name,
                "version": latest.version, "description": stack.description,
            })
    return templates.TemplateResponse(request, "home.html", {"featured_stacks": featured})


@router.get("/stacks", response_class=HTMLResponse)
def stacks_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Stack).join(Namespace)
    if q:
        query = query.filter(Stack.name.contains(q) | Stack.description.contains(q))
    stacks_list = query.order_by(Stack.updated_at.desc()).limit(50).all()
    items = []
    for stack in stacks_list:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": stack.namespace.name, "name": stack.name,
                "version": latest.version, "description": stack.description,
            })
    return templates.TemplateResponse(request, "stacks.html", {"stacks": items, "query": q})


@router.get("/web/search", response_class=HTMLResponse)
def search_fragment(request: Request, q: str = "", db: Session = Depends(get_db)):
    if not q:
        return HTMLResponse("")
    query = db.query(Stack).join(Namespace).filter(
        Stack.name.contains(q) | Stack.description.contains(q)
    )
    stacks_list = query.order_by(Stack.updated_at.desc()).limit(10).all()
    items = []
    for stack in stacks_list:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": stack.namespace.name, "name": stack.name,
                "version": latest.version, "description": stack.description,
            })
    return templates.TemplateResponse(request, "_search_results.html", {"stacks": items, "query": q})


@router.get("/stacks/{namespace}/{name}", response_class=HTMLResponse)
def stack_detail_page(request: Request, namespace: str, name: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, "Not found")
    latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).first()
    if not latest:
        raise HTTPException(404, "Not found")
    all_versions = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).all()
    skills = json.loads(latest.skills)
    profiles = json.loads(latest.profiles)
    depends_on = json.loads(latest.depends_on)
    deprecations = json.loads(latest.deprecations)
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}
    versions_data = [{"version": v.version, "digest": v.digest,
                       "published_at": v.published_at.isoformat() if v.published_at else ""}
                      for v in all_versions]
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack, "version": latest,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })


@router.get("/stacks/{namespace}/{name}/{version}", response_class=HTMLResponse)
def stack_version_page(request: Request, namespace: str, name: str, version: str,
                       db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, "Not found")
    sv = db.query(StackVersion).filter_by(stack_id=stack.id, version=version).first()
    if not sv:
        raise HTTPException(404, "Not found")
    all_versions = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).all()
    skills = json.loads(sv.skills)
    profiles = json.loads(sv.profiles)
    depends_on = json.loads(sv.depends_on)
    deprecations = json.loads(sv.deprecations)
    deprecated_skills = {d["skill"]: d["replacement"] for d in deprecations}
    versions_data = [{"version": v.version, "digest": v.digest,
                       "published_at": v.published_at.isoformat() if v.published_at else ""}
                      for v in all_versions]
    return templates.TemplateResponse(request, "stack_detail.html", {
        "namespace": namespace, "stack": stack, "version": sv,
        "skills": skills, "profiles": profiles, "depends_on": depends_on,
        "deprecations": deprecations, "deprecated_skills": deprecated_skills,
        "all_versions": versions_data,
    })


@router.get("/{namespace}", response_class=HTMLResponse)
def namespace_page(request: Request, namespace: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, "Not found")
    stacks = db.query(Stack).filter_by(namespace_id=ns.id).all()
    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append({
                "namespace": ns.name, "name": stack.name,
                "version": latest.version, "description": stack.description,
            })
    return templates.TemplateResponse(request, "namespace.html", {"ns": ns, "stacks": items})
