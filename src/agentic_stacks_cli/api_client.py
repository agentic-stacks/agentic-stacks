"""Registry API client."""

import httpx


class RegistryClient:
    def __init__(self, api_url: str, token: str | None = None):
        self._api_url = api_url.rstrip("/")
        self._token = token
        headers = {"User-Agent": "agentic-stacks-cli"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(headers=headers, timeout=30.0)

    def search(self, query: str) -> list[dict]:
        resp = self._client.get(f"{self._api_url}/stacks", params={"q": query})
        resp.raise_for_status()
        return resp.json().get("stacks", [])

    def get_stack(self, namespace: str, name: str, version: str | None = None) -> dict:
        if version:
            url = f"{self._api_url}/stacks/{namespace}/{name}/{version}"
        else:
            url = f"{self._api_url}/stacks/{namespace}/{name}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    def register_stack(self, metadata: dict) -> dict:
        if not self._token:
            raise RuntimeError("Authentication required. Run 'agentic-stacks login' first.")
        resp = self._client.post(f"{self._api_url}/stacks", json=metadata)
        resp.raise_for_status()
        return resp.json()
