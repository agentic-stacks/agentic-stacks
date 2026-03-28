from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from registry.database import Base
from registry.models import Namespace, Stack, StackVersion

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)

def test_create_namespace():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks", verified=True)
    session.add(ns)
    session.commit()
    loaded = session.query(Namespace).filter_by(name="agentic-stacks").first()
    assert loaded.name == "agentic-stacks"
    assert loaded.verified is True
    assert loaded.created_at is not None

def test_create_stack():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack deployment")
    session.add(stack)
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert loaded.name == "openstack"
    assert loaded.namespace_id == ns.id

def test_create_stack_version():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.flush()
    sv = StackVersion(
        stack_id=stack.id, version="1.3.0", target_software="openstack",
        target_versions='["2024.2", "2025.1"]',
        skills='[{"name": "deploy", "description": "Deploy"}]',
        profiles='{"categories": ["security"]}',
        depends_on="[]", deprecations="[]", requires='{"tools": ["kolla-ansible"]}',
        digest="sha256:abc123", registry_ref="ghcr.io/agentic-stacks/openstack:1.3.0",
    )
    session.add(sv)
    session.commit()
    loaded = session.query(StackVersion).filter_by(version="1.3.0").first()
    assert loaded.digest == "sha256:abc123"

def test_stack_namespace_relationship():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert loaded.namespace.name == "agentic-stacks"

def test_stack_versions_relationship():
    session = _make_session()
    ns = Namespace(name="agentic-stacks", github_org="agentic-stacks")
    session.add(ns)
    session.flush()
    stack = Stack(namespace_id=ns.id, name="openstack", description="OpenStack")
    session.add(stack)
    session.flush()
    sv1 = StackVersion(stack_id=stack.id, version="1.0.0", digest="sha256:aaa",
                       registry_ref="ghcr.io/agentic-stacks/openstack:1.0.0")
    sv2 = StackVersion(stack_id=stack.id, version="1.1.0", digest="sha256:bbb",
                       registry_ref="ghcr.io/agentic-stacks/openstack:1.1.0")
    session.add_all([sv1, sv2])
    session.commit()
    loaded = session.query(Stack).filter_by(name="openstack").first()
    assert len(loaded.versions) == 2
