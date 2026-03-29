"""Pydantic request/response schemas."""
from pydantic import BaseModel

class SkillInfo(BaseModel):
    name: str
    description: str = ""

class DependencyInfo(BaseModel):
    name: str
    namespace: str = ""
    owner: str = ""
    version: str

class DeprecationInfo(BaseModel):
    skill: str
    since: str
    removal: str
    replacement: str
    reason: str = ""

class StackRegisterRequest(BaseModel):
    namespace: str = ""
    owner: str = ""
    name: str
    version: str
    description: str = ""
    target: dict = {}
    skills: list[SkillInfo] = []
    profiles: dict = {}
    depends_on: list[DependencyInfo] = []
    deprecations: list[DeprecationInfo] = []
    requires: dict = {}
    digest: str
    registry_ref: str

class StackVersionResponse(BaseModel):
    namespace: str
    owner: str = ""
    name: str
    version: str
    description: str = ""
    target: dict = {}
    skills: list[dict] = []
    profiles: dict = {}
    depends_on: list[dict] = []
    deprecations: list[dict] = []
    requires: dict = {}
    digest: str
    registry_ref: str
    published_at: str | None = None

class StackListItem(BaseModel):
    namespace: str
    owner: str = ""
    name: str
    version: str
    description: str = ""
    target: dict = {}

class StackListResponse(BaseModel):
    stacks: list[StackListItem]
    total: int
    page: int
    per_page: int

class NamespaceResponse(BaseModel):
    name: str
    github_org: str | None = None
    verified: bool = False
    stacks: list[StackListItem] = []
