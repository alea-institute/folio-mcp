"""
APIBackend error handling and traversal, against a mocked FOLIO REST API (no network).
"""

import json

import httpx
import pytest

from folio_mcp.backends.api import APIBackend

ROOT = "https://folio.openlegalstandard.org/ROOT"


def node(iri_id, children=(), parents=()):
    return {
        "children": [{"iri": f"https://folio.openlegalstandard.org/{c}", "label": c} for c in children],
        "parents": [{"iri": f"https://folio.openlegalstandard.org/{p}", "label": p} for p in parents],
    }


TREE = {
    "ROOT": node("ROOT", children=["A", "B"]),
    "A": node("A", children=["A1", "A2"], parents=["ROOT"]),
    "B": node("B", children=["B1"], parents=["ROOT"]),
    "A1": node("A1", parents=["A"]),
    "A2": node("A2", parents=["A"]),
    "B1": node("B1", parents=["B"]),
}


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.startswith("/taxonomy/tree/node/"):
        key = path.rsplit("/", 1)[-1]
        if key in TREE:
            return httpx.Response(200, json=TREE[key])
        return httpx.Response(404, json={"detail": "not found"})
    if path == "/":
        return httpx.Response(200, text="<!DOCTYPE html><html>home</html>", headers={"content-type": "text/html"})
    if path.startswith("/search/"):
        return httpx.Response(500, text="Internal Server Error")
    return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
def backend():
    b = APIBackend()
    b._client = httpx.AsyncClient(base_url=b.base_url, transport=httpx.MockTransport(handler))
    return b


@pytest.mark.asyncio
class TestAPIErrors:
    async def test_not_found_children_is_concise(self, backend):
        data = json.loads(await backend.get_children("ZZZZ", 1))
        assert data == {"error": "Concept not found: ZZZZ"}

    async def test_server_error_is_concise(self, backend):
        data = json.loads(await backend.search_by_label("x", 5))
        assert data["error"] == "FOLIO API error (HTTP 500)"
        assert "mozilla" not in json.dumps(data)

    async def test_unreachable_api(self):
        def boom(request):
            raise httpx.ConnectError("connection refused")

        b = APIBackend()
        b._client = httpx.AsyncClient(base_url=b.base_url, transport=httpx.MockTransport(boom))
        data = json.loads(await b.list_branches())
        assert data["error"].startswith("Could not reach the FOLIO API")

    async def test_html_page_is_never_returned_as_a_concept(self, backend):
        data = json.loads(await backend.get_concept(""))
        assert "error" in data


@pytest.mark.asyncio
class TestAPITraversal:
    async def test_children_depth_1(self, backend):
        data = json.loads(await backend.get_children(ROOT, 1))
        assert [c["label"] for c in data] == ["A", "B"]

    async def test_children_depth_2_matches_local_semantics(self, backend):
        data = json.loads(await backend.get_children(ROOT, 2))
        assert sorted(c["label"] for c in data) == ["A", "A1", "A2", "B", "B1"]

    async def test_parents_depth_2(self, backend):
        data = json.loads(await backend.get_parents("https://folio.openlegalstandard.org/A1", 2))
        assert [c["label"] for c in data] == ["A", "ROOT"]
