"""Stack API routes."""
from fastapi import APIRouter, Depends, HTTPException
from web.app import get_db
from web.schemas import (
    StackVersionResponse, StackListItem, StackListResponse,
)

router = APIRouter(prefix="/api/v1")


@router.get("/stacks", response_model=StackListResponse)
async def list_stacks(
    q: str | None = None, target: str | None = None,
    namespace: str | None = None, owner: str | None = None,
    sort: str = "updated", page: int = 1, per_page: int = 20,
    db=Depends(get_db),
):
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
