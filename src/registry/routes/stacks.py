"""Stack API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion
from registry.schemas import (
    StackRegisterRequest, StackVersionResponse, StackListItem, StackListResponse,
)
from registry.auth import verify_github_token, get_github_orgs, AuthError

router = APIRouter(prefix="/api/v1")


@router.get("/stacks", response_model=StackListResponse)
def list_stacks(
    q: str | None = None, target: str | None = None, namespace: str | None = None,
    sort: str = "updated", page: int = 1, per_page: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Stack).join(Namespace)
    if q:
        query = query.filter(Stack.name.contains(q) | Stack.description.contains(q))
    if namespace:
        query = query.filter(Namespace.name == namespace)
    if target:
        query = query.join(StackVersion).filter(StackVersion.target_software.contains(target))
    total = query.count()
    if sort == "name":
        query = query.order_by(Stack.name)
    else:
        query = query.order_by(Stack.updated_at.desc())
    stacks = query.offset((page - 1) * per_page).limit(per_page).all()
    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        items.append(StackListItem(
            namespace=stack.namespace.name, name=stack.name,
            version=latest.version if latest else "0.0.0",
            description=stack.description,
            target={"software": latest.target_software,
                    "versions": json.loads(latest.target_versions)} if latest else {},
        ))
    return StackListResponse(stacks=items, total=total, page=page, per_page=per_page)


@router.get("/stacks/{namespace}/{name}", response_model=StackVersionResponse)
def get_stack(namespace: str, name: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
        .order_by(StackVersion.published_at.desc()).first()
    if not latest:
        raise HTTPException(404, f"No versions published for '{namespace}/{name}'")
    return _version_response(ns.name, stack, latest)


@router.get("/stacks/{namespace}/{name}/{version}", response_model=StackVersionResponse)
def get_stack_version(namespace: str, name: str, version: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=name).first()
    if not stack:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    sv = db.query(StackVersion).filter_by(stack_id=stack.id, version=version).first()
    if not sv:
        raise HTTPException(404, f"Version '{version}' not found for '{namespace}/{name}'")
    return _version_response(ns.name, stack, sv)


@router.post("/stacks", response_model=StackVersionResponse, status_code=201)
def register_stack(
    body: StackRegisterRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header required")
    token = authorization.split(" ", 1)[1]
    try:
        username = verify_github_token(token)
    except AuthError:
        raise HTTPException(401, "Invalid GitHub token")
    user_orgs = get_github_orgs(token, include_user=True)
    if body.namespace not in user_orgs:
        raise HTTPException(403, f"You don't have access to namespace '{body.namespace}'")

    ns = db.query(Namespace).filter_by(name=body.namespace).first()
    if not ns:
        ns = Namespace(name=body.namespace, github_org=body.namespace)
        db.add(ns)
        db.flush()

    stack = db.query(Stack).filter_by(namespace_id=ns.id, name=body.name).first()
    if not stack:
        stack = Stack(namespace_id=ns.id, name=body.name, description=body.description)
        db.add(stack)
        db.flush()
    else:
        stack.description = body.description

    existing = db.query(StackVersion).filter_by(stack_id=stack.id, version=body.version).first()
    if existing:
        raise HTTPException(409, f"Version '{body.version}' already exists for '{body.namespace}/{body.name}'")

    sv = StackVersion(
        stack_id=stack.id, version=body.version,
        target_software=body.target.get("software", ""),
        target_versions=json.dumps(body.target.get("versions", [])),
        skills=json.dumps([s.model_dump() for s in body.skills]),
        profiles=json.dumps(body.profiles),
        depends_on=json.dumps([d.model_dump() for d in body.depends_on]),
        deprecations=json.dumps([d.model_dump() for d in body.deprecations]),
        requires=json.dumps(body.requires),
        digest=body.digest, registry_ref=body.registry_ref,
    )
    db.add(sv)
    db.commit()
    return _version_response(ns.name, stack, sv)


def _version_response(namespace: str, stack: Stack, sv: StackVersion) -> StackVersionResponse:
    return StackVersionResponse(
        namespace=namespace, name=stack.name, version=sv.version,
        description=stack.description,
        target={"software": sv.target_software, "versions": json.loads(sv.target_versions)},
        skills=json.loads(sv.skills), profiles=json.loads(sv.profiles),
        depends_on=json.loads(sv.depends_on), deprecations=json.loads(sv.deprecations),
        requires=json.loads(sv.requires),
        digest=sv.digest, registry_ref=sv.registry_ref,
        published_at=sv.published_at.isoformat() if sv.published_at else None,
    )
