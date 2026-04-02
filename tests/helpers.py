"""Shared test helpers for FormulaDB-backed tests."""
from fastapi.testclient import TestClient
from web.app import create_app
from web.db_formulas import FormulaDB

SAMPLE_FORMULAS = [
    {
        "name": "openstack-kolla",
        "owner": "agentic-stacks",
        "version": "0.0.1",
        "category": "platform",
        "repository": "https://github.com/agentic-stacks/openstack-kolla",
        "description": "OpenStack deployment via kolla-ansible",
        "target": {"software": "openstack", "versions": ["2025.1"]},
        "skills": [
            {"name": "deploy", "description": "Deploy OpenStack"},
            {"name": "health-check", "description": "Validate health"},
        ],
        "depends_on": [],
        "requires": {"tools": ["kolla-ansible"]},
    },
    {
        "name": "kubernetes-talos",
        "owner": "agentic-stacks",
        "version": "0.0.1",
        "category": "platform",
        "repository": "https://github.com/agentic-stacks/kubernetes-talos",
        "description": "Kubernetes on Talos Linux",
        "target": {"software": "talos-linux", "versions": ["1.9.x"]},
        "skills": [
            {"name": "bootstrap", "description": "Bootstrap cluster"},
            {"name": "networking", "description": "CNI setup"},
            {"name": "storage", "description": "CSI setup"},
        ],
        "depends_on": [],
        "requires": {"tools": ["talosctl", "kubectl"]},
    },
    {
        "name": "hardware-dell",
        "owner": "agentic-stacks",
        "version": "0.0.1",
        "category": "hardware",
        "repository": "https://github.com/agentic-stacks/hardware-dell",
        "description": "Dell PowerEdge server management",
        "target": {"software": "Dell PowerEdge", "versions": ["iDRAC9"]},
        "skills": [
            {"name": "bios", "description": "BIOS configuration"},
            {"name": "raid", "description": "RAID management"},
        ],
        "depends_on": [],
        "requires": {"tools": ["docker"]},
    },
]


def create_test_app(formulas=None):
    """Create a test app with FormulaDB."""
    if formulas is None:
        formulas = SAMPLE_FORMULAS

    def factory():
        return FormulaDB(formulas)

    return create_app(db_factory=factory, enable_rate_limit=False)


def create_test_client(formulas=None):
    """Create a TestClient with FormulaDB."""
    return TestClient(create_test_app(formulas))
