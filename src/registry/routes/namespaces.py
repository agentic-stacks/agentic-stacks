"""Namespace API routes."""
from fastapi import APIRouter, Depends, HTTPException
from registry.app import get_db
from registry.schemas import NamespaceResponse, StackListItem

router = APIRouter(prefix="/api/v1")


@router.get("/namespaces/{namespace}", response_model=NamespaceResponse)
async def get_namespace(namespace: str, db=Depends(get_db)):
    ns_data = await db.get_namespace_with_stacks(namespace)
    if not ns_data:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    items = []
    for s in ns_data.get("stacks", []):
        if s.get("version") is not None:
            target_dict = {}
            if s.get("target_software") or s.get("target_versions"):
                target_dict = {"software": s.get("target_software", ""),
                               "versions": s.get("target_versions", [])}
            items.append(StackListItem(
                namespace=s["namespace"], owner=s.get("owner", s["namespace"]),
                name=s["name"],
                version=s["version"],
                description=s.get("description", ""),
                target=target_dict,
            ))
    return NamespaceResponse(
        name=ns_data["name"],
        github_org=ns_data.get("github_org"),
        verified=ns_data.get("verified", False),
        stacks=items,
    )
