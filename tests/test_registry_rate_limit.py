from tests.helpers import create_test_client


def test_rate_limit_allows_normal_usage():
    client = create_test_client()
    for _ in range(5):
        resp = client.get("/api/v1/stacks")
        assert resp.status_code == 200
