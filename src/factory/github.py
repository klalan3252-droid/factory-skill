"""Minimal GitHub REST client over httpx."""
from __future__ import annotations

from urllib.parse import quote

import httpx

from .config import redact

API_URL = "https://api.github.com"


class GitHubError(Exception):
    """Raised for failed GitHub API calls. Never contains the token."""


class GitHubClient:
    def __init__(self, token: str, repo: str, client: httpx.Client | None = None):
        self._token = token
        self.repo = repo
        self._http = client or httpx.Client(base_url=API_URL, timeout=30)

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.repo}.git"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            resp = self._http.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise GitHubError(f"{method} {path} failed: {type(exc).__name__}") from None
        if resp.status_code >= 400:
            try:
                detail = str(resp.json().get("message", ""))
            except Exception:
                detail = ""
            raise GitHubError(redact(
                f"{method} {path} failed with {resp.status_code}: {detail}", self._token))
        return resp

    def _repo_path(self, suffix: str = "") -> str:
        return f"/repos/{self.repo}{suffix}"

    def get_default_branch(self) -> str:
        return self._request("GET", self._repo_path()).json()["default_branch"]

    def get_branch_sha(self, branch: str) -> str:
        data = self._request("GET", self._repo_path(f"/git/ref/heads/{branch}")).json()
        return data["object"]["sha"]

    def list_issues(self, label: str | None = None) -> list[dict]:
        issues: list[dict] = []
        page = 1
        while True:
            params = {"state": "open", "per_page": 100, "page": page}
            if label:
                params["labels"] = label
            resp = self._request("GET", self._repo_path("/issues"), params=params)
            issues.extend(i for i in resp.json() if "pull_request" not in i)
            if "next" not in resp.links:
                return issues
            page += 1

    def get_issue(self, number: int) -> dict:
        return self._request("GET", self._repo_path(f"/issues/{number}")).json()

    def create_branch(self, name: str, sha: str) -> None:
        self._request("POST", self._repo_path("/git/refs"),
                      json={"ref": f"refs/heads/{name}", "sha": sha})

    def comment(self, number: int, body: str) -> None:
        self._request("POST", self._repo_path(f"/issues/{number}/comments"), json={"body": body})

    def add_label(self, number: int, label: str) -> None:
        self._request("POST", self._repo_path(f"/issues/{number}/labels"), json={"labels": [label]})

    def remove_label(self, number: int, label: str) -> None:
        try:
            self._request("DELETE", self._repo_path(f"/issues/{number}/labels/{quote(label, safe='')}"))
        except GitHubError as exc:
            if "failed with 404" not in str(exc):
                raise

    def create_pr(self, title: str, body: str, head: str, base: str, draft: bool = False) -> dict:
        return self._request("POST", self._repo_path("/pulls"), json={
            "title": title, "body": body, "head": head, "base": base, "draft": draft}).json()
