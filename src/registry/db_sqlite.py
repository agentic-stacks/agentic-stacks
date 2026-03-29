"""SQLite implementation of StacksDB using SQLAlchemy ORM."""

import datetime
import json

from sqlalchemy.orm import Session

from registry.models import Namespace, Stack, StackVersion


class SQLiteDB:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _json_loads_safe(self, value, default):
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    def _version_to_dict(self, ns_name: str, stack: Stack, sv: StackVersion) -> dict:
        return {
            "namespace": ns_name,
            "owner": ns_name,
            "name": stack.name,
            "description": stack.description or "",
            "version": sv.version,
            "target_software": sv.target_software or "",
            "target_versions": self._json_loads_safe(sv.target_versions, []),
            "skills": self._json_loads_safe(sv.skills, []),
            "profiles": self._json_loads_safe(sv.profiles, {}),
            "depends_on": self._json_loads_safe(sv.depends_on, []),
            "deprecations": self._json_loads_safe(sv.deprecations, []),
            "requires": self._json_loads_safe(sv.requires, {}),
            "digest": sv.digest,
            "registry_ref": sv.registry_ref,
            "published_at": sv.published_at.isoformat() if sv.published_at else None,
            "updated_at": stack.updated_at.isoformat() if stack.updated_at else None,
            "created_at": stack.created_at.isoformat() if stack.created_at else None,
        }

    def _stack_summary(self, ns_name: str, stack: Stack, sv: StackVersion | None) -> dict:
        result = {
            "namespace": ns_name,
            "owner": ns_name,
            "name": stack.name,
            "description": stack.description or "",
            "updated_at": stack.updated_at.isoformat() if stack.updated_at else None,
            "created_at": stack.created_at.isoformat() if stack.created_at else None,
        }
        if sv is not None:
            result["version"] = sv.version
            result["target_software"] = sv.target_software or ""
            result["target_versions"] = self._json_loads_safe(sv.target_versions, [])
            result["digest"] = sv.digest
            result["registry_ref"] = sv.registry_ref
        else:
            result["version"] = None
            result["target_software"] = ""
            result["target_versions"] = []
            result["digest"] = None
            result["registry_ref"] = None
        return result

    def _latest_version(self, stack_id: int) -> StackVersion | None:
        return (
            self._session.query(StackVersion)
            .filter(StackVersion.stack_id == stack_id)
            .order_by(StackVersion.published_at.desc())
            .first()
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def list_stacks(
        self,
        q: str | None = None,
        namespace: str | None = None,
        target: str | None = None,
        sort: str = "updated",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        query = self._session.query(Stack, Namespace).join(
            Namespace, Stack.namespace_id == Namespace.id
        )

        if namespace:
            query = query.filter(Namespace.name == namespace)

        if q:
            like = f"%{q}%"
            query = query.filter(
                Stack.name.ilike(like) | Stack.description.ilike(like)
            )

        if target:
            # Filter stacks that have at least one version with this target_software
            sub = (
                self._session.query(StackVersion.stack_id)
                .filter(StackVersion.target_software == target)
                .subquery()
            )
            query = query.filter(Stack.id.in_(sub))

        if sort == "name":
            query = query.order_by(Stack.name.asc())
        else:
            query = query.order_by(Stack.updated_at.desc())

        total = query.count()
        offset = (page - 1) * per_page
        rows = query.offset(offset).limit(per_page).all()

        items = []
        for stack, ns in rows:
            sv = self._latest_version(stack.id)
            items.append(self._stack_summary(ns.name, stack, sv))

        return items, total

    async def get_stack(self, namespace: str, name: str) -> dict | None:
        row = (
            self._session.query(Stack, Namespace)
            .join(Namespace, Stack.namespace_id == Namespace.id)
            .filter(Namespace.name == namespace, Stack.name == name)
            .first()
        )
        if row is None:
            return None
        stack, ns = row
        sv = self._latest_version(stack.id)
        if sv is None:
            return None
        return self._version_to_dict(ns.name, stack, sv)

    async def get_stack_version(self, namespace: str, name: str, version: str) -> dict | None:
        row = (
            self._session.query(Stack, Namespace)
            .join(Namespace, Stack.namespace_id == Namespace.id)
            .filter(Namespace.name == namespace, Stack.name == name)
            .first()
        )
        if row is None:
            return None
        stack, ns = row
        sv = (
            self._session.query(StackVersion)
            .filter(
                StackVersion.stack_id == stack.id,
                StackVersion.version == version,
            )
            .first()
        )
        if sv is None:
            return None
        return self._version_to_dict(ns.name, stack, sv)

    async def get_namespace_with_stacks(self, namespace: str) -> dict | None:
        ns = (
            self._session.query(Namespace)
            .filter(Namespace.name == namespace)
            .first()
        )
        if ns is None:
            return None

        stacks = (
            self._session.query(Stack)
            .filter(Stack.namespace_id == ns.id)
            .order_by(Stack.updated_at.desc())
            .all()
        )

        stack_list = []
        for stack in stacks:
            sv = self._latest_version(stack.id)
            stack_list.append(self._stack_summary(ns.name, stack, sv))

        return {
            "name": ns.name,
            "github_org": ns.github_org,
            "verified": ns.verified,
            "created_at": ns.created_at.isoformat() if ns.created_at else None,
            "stacks": stack_list,
        }

    async def create_namespace(self, name: str, github_org: str) -> dict:
        ns = Namespace(name=name, github_org=github_org)
        self._session.add(ns)
        self._session.commit()
        self._session.refresh(ns)
        return {
            "name": ns.name,
            "github_org": ns.github_org,
            "verified": ns.verified,
            "created_at": ns.created_at.isoformat() if ns.created_at else None,
        }

    async def create_stack(self, namespace: str, name: str, description: str) -> dict:
        ns = self._session.query(Namespace).filter(Namespace.name == namespace).first()
        if ns is None:
            raise ValueError(f"Namespace '{namespace}' not found")
        stack = Stack(namespace_id=ns.id, name=name, description=description)
        self._session.add(stack)
        self._session.commit()
        self._session.refresh(stack)
        return {
            "namespace": namespace,
            "owner": namespace,
            "name": stack.name,
            "description": stack.description,
            "created_at": stack.created_at.isoformat() if stack.created_at else None,
            "updated_at": stack.updated_at.isoformat() if stack.updated_at else None,
        }

    async def create_version(self, namespace: str, name: str, version_data: dict) -> dict:
        ns = self._session.query(Namespace).filter(Namespace.name == namespace).first()
        if ns is None:
            raise ValueError(f"Namespace '{namespace}' not found")
        stack = (
            self._session.query(Stack)
            .filter(Stack.namespace_id == ns.id, Stack.name == name)
            .first()
        )
        if stack is None:
            raise ValueError(f"Stack '{namespace}/{name}' not found")

        sv = StackVersion(
            stack_id=stack.id,
            version=version_data.get("version", ""),
            target_software=version_data.get("target_software", ""),
            target_versions=version_data.get("target_versions", "[]"),
            skills=version_data.get("skills", "[]"),
            profiles=version_data.get("profiles", "{}"),
            depends_on=version_data.get("depends_on", "[]"),
            deprecations=version_data.get("deprecations", "[]"),
            requires=version_data.get("requires", "{}"),
            digest=version_data.get("digest", ""),
            registry_ref=version_data.get("registry_ref", ""),
        )
        self._session.add(sv)
        # Update stack's updated_at
        stack.updated_at = datetime.datetime.utcnow()
        self._session.commit()
        self._session.refresh(sv)
        return self._version_to_dict(namespace, stack, sv)

    async def version_exists(self, namespace: str, name: str, version: str) -> bool:
        row = (
            self._session.query(Stack, Namespace)
            .join(Namespace, Stack.namespace_id == Namespace.id)
            .filter(Namespace.name == namespace, Stack.name == name)
            .first()
        )
        if row is None:
            return False
        stack, _ = row
        sv = (
            self._session.query(StackVersion)
            .filter(
                StackVersion.stack_id == stack.id,
                StackVersion.version == version,
            )
            .first()
        )
        return sv is not None

    async def featured_stacks(self, limit: int = 6) -> list[dict]:
        stacks_with_ns = (
            self._session.query(Stack, Namespace)
            .join(Namespace, Stack.namespace_id == Namespace.id)
            .order_by(Stack.updated_at.desc())
            .limit(limit)
            .all()
        )
        result = []
        for stack, ns in stacks_with_ns:
            sv = self._latest_version(stack.id)
            result.append(self._stack_summary(ns.name, stack, sv))
        return result

    async def all_versions(self, namespace: str, name: str) -> list[dict]:
        row = (
            self._session.query(Stack, Namespace)
            .join(Namespace, Stack.namespace_id == Namespace.id)
            .filter(Namespace.name == namespace, Stack.name == name)
            .first()
        )
        if row is None:
            return []
        stack, ns = row
        versions = (
            self._session.query(StackVersion)
            .filter(StackVersion.stack_id == stack.id)
            .order_by(StackVersion.published_at.desc())
            .all()
        )
        return [self._version_to_dict(ns.name, stack, sv) for sv in versions]
