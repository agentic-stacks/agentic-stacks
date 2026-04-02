from tests.helpers import create_test_client


def test_full_browse_workflow():
    """Browse stacks, view detail, check versions."""
    client = create_test_client()
    # List
    resp = client.get("/api/v1/stacks")
    assert resp.status_code == 200
    stacks = resp.json()["stacks"]
    assert len(stacks) == 3
    # Detail
    resp = client.get("/api/v1/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    assert resp.json()["name"] == "openstack-kolla"
    # Search
    resp = client.get("/api/v1/stacks?q=RAID")
    assert resp.status_code == 200
    assert any(s["name"] == "hardware-dell" for s in resp.json()["stacks"])
