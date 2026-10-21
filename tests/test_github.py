import json

import httpx
import pytest

from factory.github import GitHubClient, GitHubError
from .conftest import TOKEN


def make_client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    return GitHubClient(token=TOKEN, repo="acme/widgets", client=http)


def test_list_issues_filters_label_skips_prs_and_paginates():
    seen = []

    def handler(req):
        seen.append(req)
        assert req.headers["authorization"].endswith(TOKEN)
        assert req.url.path == "/repos/acme/widgets/issues"
        assert req.url.params["labels"] == "factory"
        assert req.url.params["state"] == "open"
        page = int(req.url.params.get("page", "1"))
        if page == 1:
            items = [{"number": 1, "title": "a"}, {"number": 2, "title": "pr", "pull_request": {}}]
            return httpx.Response(200, json=items,
                                  headers={"Link": '<https://api.github.com/repos/acme/widgets/issues?page=2>; rel="next"'})
        return httpx.Response(200, json=[{"number": 3, "title": "c"}])

    issues = make_client(handler).list_issues("factory")
    assert [i["number"] for i in issues] == [1, 3]
    assert len(seen) == 2


def test_default_branch_and_sha():
    def handler(req):
        if req.url.path == "/repos/acme/widgets":
            return httpx.Response(200, json={"default_branch": "trunk"})
        if req.url.path == "/repos/acme/widgets/git/ref/heads/trunk":
            return httpx.Response(200, json={"object": {"sha": "abc"}})
        return httpx.Response(404)
    c = make_client(handler)
    assert c.get_default_branch() == "trunk"
    assert c.get_branch_sha("trunk") == "abc"


def test_writes():
    got = []

    def handler(req):
        got.append((req.method, req.url.path, json.loads(req.content or b"{}")))
        return httpx.Response(201, json={"number": 5, "html_url": "u"})
    c = make_client(handler)
    c.create_branch("factory/1-x", "abc")
    c.comment(1, "hi")
    c.add_label(1, "in-progress")
    c.create_pr(title="T", body="Closes #1", head="factory/1-x", base="main", draft=True)
    by_path = {p: (m, b) for m, p, b in got}
    assert by_path["/repos/acme/widgets/git/refs"][1] == {"ref": "refs/heads/factory/1-x", "sha": "abc"}
    assert by_path["/repos/acme/widgets/issues/1/comments"][1]["body"] == "hi"
    assert "in-progress" in json.dumps(by_path["/repos/acme/widgets/issues/1/labels"][1])
    pr = by_path["/repos/acme/widgets/pulls"][1]
    assert pr["head"] == "factory/1-x" and pr["base"] == "main" and pr["draft"] is True
    assert all(m == "POST" for m, _, _ in got)


def test_error_does_not_leak_token():
    def handler(req):
        return httpx.Response(401, json={"message": f"bad credentials {TOKEN}"})
    with pytest.raises(GitHubError) as e:
        make_client(handler).get_default_branch()
    assert TOKEN not in str(e.value) and TOKEN not in repr(e.value)
