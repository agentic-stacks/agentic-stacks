"""SQLAlchemy models for the registry."""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from registry.database import Base

class Namespace(Base):
    __tablename__ = "namespaces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    github_org = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    stacks = relationship("Stack", back_populates="namespace")

class Stack(Base):
    __tablename__ = "stacks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    namespace_id = Column(Integer, ForeignKey("namespaces.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    namespace = relationship("Namespace", back_populates="stacks")
    versions = relationship("StackVersion", back_populates="stack", order_by="StackVersion.published_at")

class StackVersion(Base):
    __tablename__ = "stack_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stack_id = Column(Integer, ForeignKey("stacks.id"), nullable=False)
    version = Column(String, nullable=False)
    target_software = Column(String, default="")
    target_versions = Column(Text, default="[]")
    skills = Column(Text, default="[]")
    profiles = Column(Text, default="{}")
    depends_on = Column(Text, default="[]")
    deprecations = Column(Text, default="[]")
    requires = Column(Text, default="{}")
    digest = Column(String, nullable=False)
    registry_ref = Column(String, nullable=False)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)
    stack = relationship("Stack", back_populates="versions")
