"""GitHub token verification."""
import httpx
from registry.config import GITHUB_API_URL

class AuthError(Exception):
    pass

def verify_github_token(token: str) -> str:
    resp = httpx.get(f"{GITHUB_API_URL}/user",
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    if resp.status_code == 401:
        raise AuthError("Token is invalid or expired.")
    resp.raise_for_status()
    return resp.json()["login"]

def get_github_orgs(token: str, include_user: bool = False) -> list[str]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    orgs = []
    if include_user:
        user_resp = httpx.get(f"{GITHUB_API_URL}/user", headers=headers)
        user_resp.raise_for_status()
        orgs.append(user_resp.json()["login"])
    orgs_resp = httpx.get(f"{GITHUB_API_URL}/user/orgs", headers=headers)
    orgs_resp.raise_for_status()
    orgs.extend(org["login"] for org in orgs_resp.json())
    return orgs
