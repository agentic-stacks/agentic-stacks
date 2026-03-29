"""Stack API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from registry.app import get_db
from registry.schemas import (
    StackRegisterRequest, StackVersionResponse, StackListItem, StackListResponse,
)
from registry.auth import verify_github_token, get_github_orgs, AuthError

router = APIRouter(prefix="/api/v1")


@router.get("/stacks", response_model=StackListResponse)
async def list_stacks(
    q: str | None = None, target: str | None = None,
    namespace: str | None = None, owner: str | None = None,
    sort: str = "updated", page: int = 1, per_page: int = 20,
    db=Depends(get_db),
):
    # Accept 'owner' as preferred alias for 'namespace'
    ns_filter = owner or namespace
    items, total = await db.list_stacks(q=q, namespace=ns_filter, target=target,
                                  sort=sort, page=page, per_page=per_page)
    stack_items = []
    for item in items:
        target_dict = {}
        if item.get("target_software") or item.get("target_versions"):
            target_dict = {"software": item.get("target_software", ""),
                           "versions": item.get("target_versions", [])}
        stack_items.append(StackListItem(
            namespace=item["namespace"], owner=item.get("owner", item["namespace"]),
            name=item["name"],
            version=item.get("version") or "0.0.0",
            description=item.get("description", ""),
            target=target_dict,
        ))
    return StackListResponse(stacks=stack_items, total=total, page=page, per_page=per_page)


@router.get("/stacks/{namespace}/{name}", response_model=StackVersionResponse)
async def get_stack(namespace: str, name: str, db=Depends(get_db)):
    result = await db.get_stack(namespace, name)
    if result is None:
        raise HTTPException(404, f"Stack '{namespace}/{name}' not found")
    return _to_version_response(result)


@router.get("/stacks/{namespace}/{name}/{version}", response_model=StackVersionResponse)
async def get_stack_version(namespace: str, name: str, version: str, db=Depends(get_db)):
    result = await db.get_stack_version(namespace, name, version)
    if result is None:
        raise HTTPException(404, f"Version '{version}' not found for '{namespace}/{name}'")
    return _to_version_response(result)


@router.post("/stacks", response_model=StackVersionResponse, status_code=201)
async def register_stack(
    body: StackRegisterRequest,
    authorization: str | None = Header(None),
    db=Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header required")
    token = authorization.split(" ", 1)[1]
    try:
        username = verify_github_token(token)
    except AuthError:
        raise HTTPException(401, "Invalid GitHub token")
    # Accept 'owner' as preferred alias for 'namespace'
    ns = body.owner or body.namespace
    if not ns:
        raise HTTPException(422, "Either 'owner' or 'namespace' is required")

    user_orgs = get_github_orgs(token, include_user=True)
    if ns not in user_orgs:
        raise HTTPException(403, f"You don't have access to namespace '{ns}'")

    ns_data = await db.get_namespace_with_stacks(ns)
    if not ns_data:
        await db.create_namespace(ns, ns)

    stack_data = await db.get_stack(ns, body.name)
    if not stack_data:
        await db.create_stack(ns, body.name, body.description)

    if await db.version_exists(ns, body.name, body.version):
        raise HTTPException(409, f"Version '{body.version}' already exists for '{ns}/{body.name}'")

    version_data = {
        "version": body.version,
        "target_software": body.target.get("software", ""),
        "target_versions": json.dumps(body.target.get("versions", [])),
        "skills": json.dumps([s.model_dump() for s in body.skills]),
        "profiles": json.dumps(body.profiles),
        "depends_on": json.dumps([d.model_dump() for d in body.depends_on]),
        "deprecations": json.dumps([d.model_dump() for d in body.deprecations]),
        "requires": json.dumps(body.requires),
        "digest": body.digest,
        "registry_ref": body.registry_ref,
    }
    result = await db.create_version(ns, body.name, version_data)
    return _to_version_response(result)


def _to_version_response(d: dict) -> StackVersionResponse:
    return StackVersionResponse(
        namespace=d["namespace"], owner=d.get("owner", d["namespace"]),
        name=d["name"], version=d["version"],
        description=d.get("description", ""),
        target={"software": d.get("target_software", ""),
                "versions": d.get("target_versions", [])},
        skills=d.get("skills", []),
        profiles=d.get("profiles", {}),
        depends_on=d.get("depends_on", []),
        deprecations=d.get("deprecations", []),
        requires=d.get("requires", {}),
        digest=d.get("digest", ""),
        registry_ref=d.get("registry_ref", ""),
        published_at=d.get("published_at"),
    )
