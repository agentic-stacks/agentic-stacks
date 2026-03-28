"""Web page routes — server-rendered HTML."""
import pathlib

import jinja2
from fastapi import APIRouter, Depends, Request
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
