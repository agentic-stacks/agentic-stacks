from tests.helpers import create_test_client


def test_browse_then_detail():
    client = create_test_client()
    resp = client.get("/stacks")
    assert resp.status_code == 200
    assert "openstack-kolla" in resp.text
    resp = client.get("/stacks/agentic-stacks/openstack-kolla")
    assert resp.status_code == 200
    assert "deploy" in resp.text.lower()
