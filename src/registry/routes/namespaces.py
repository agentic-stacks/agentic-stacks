"""Namespace API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from registry.database import get_db
from registry.models import Namespace, Stack, StackVersion
from registry.schemas import NamespaceResponse, StackListItem

router = APIRouter(prefix="/api/v1")


@router.get("/namespaces/{namespace}", response_model=NamespaceResponse)
def get_namespace(namespace: str, db: Session = Depends(get_db)):
    ns = db.query(Namespace).filter_by(name=namespace).first()
    if not ns:
        raise HTTPException(404, f"Namespace '{namespace}' not found")
    stacks = db.query(Stack).filter_by(namespace_id=ns.id).all()
    items = []
    for stack in stacks:
        latest = db.query(StackVersion).filter_by(stack_id=stack.id)\
            .order_by(StackVersion.published_at.desc()).first()
        if latest:
            items.append(StackListItem(
                namespace=ns.name, name=stack.name, version=latest.version,
                description=stack.description,
                target={"software": latest.target_software,
                        "versions": json.loads(latest.target_versions)},
            ))
    return NamespaceResponse(name=ns.name, github_org=ns.github_org,
                             verified=ns.verified, stacks=items)
