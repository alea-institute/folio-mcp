"""search_expanded tool: local + API backends, without network or an LLM."""

import json
from types import SimpleNamespace

import httpx
import pytest

from folio_mcp.backends.api import APIBackend
from folio_mcp.backends.local import LocalBackend
from folio_mcp.backends.protocol import FOLIOBackend
from folio_mcp.server import mcp

IRI = "https://folio.openlegalstandard.org/RBRosNDPt8cNUuRnoPqYufN"
LABEL = "Breach of Implied Warranty of Habitability"


def _owl_class():
    return SimpleNamespace(iri=IRI, label=LABEL, definition="A tenant claim.")


class ExpandingFolio:
    def __init__(self):
        self.calls = []

    async def search_expanded(self, query, limit=10, include_definitions=False):
        self.calls.append((query, limit, include_definitions))
        hit = SimpleNamespace(
            owl_class=_owl_class(), score=0.0491803, matched_via=["Implied Warranty of Habitability"]
        )
        return SimpleNamespace(
            query=query,
            expansions=["Implied Warranty of Habitability", "Constructive Eviction"],
            expansion_source="llm",
            hits=[hit],
        )


class LegacyFolio:
    """folio-python releases without FOLIO.search_expanded."""

    def search_by_label(self, query, limit=10):
        return [(_owl_class(), 90)]


@pytest.mark.asyncio
async def test_local_backend_search_expanded():
    folio = ExpandingFolio()
    payload = json.loads(
        await LocalBackend(folio).search_expanded("my landlord won't fix the heat", 5, True)
    )
    assert folio.calls == [("my landlord won't fix the heat", 5, True)]
    assert payload["expansions"] == ["Implied Warranty of Habitability", "Constructive Eviction"]
    assert payload["expansion_source"] == "llm"
    assert payload["results"] == [
        {
            "iri": IRI,
            "label": LABEL,
            "definition": "A tenant claim.",
            "score": 0.04918,
            "matched_via": ["Implied Warranty of Habitability"],
        }
    ]


@pytest.mark.asyncio
async def test_local_backend_falls_back_without_search_expanded():
    payload = json.loads(await LocalBackend(LegacyFolio()).search_expanded("habitability", 3))
    assert payload["expansions"] == []
    assert payload["expansion_source"] == "none"
    assert payload["results"][0]["iri"] == IRI
    assert payload["results"][0]["matched_via"] == ["habitability"]


@pytest.mark.asyncio
async def test_api_backend_search_expanded():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "query": "my landlord won't fix the heat",
                "expansions": ["Implied Warranty of Habitability"],
                "expansion_source": "cache",
                "results": [
                    {
                        "owl_class": {"iri": IRI, "label": LABEL, "definition": None},
                        "score": 0.03,
                        "matched_via": ["Implied Warranty of Habitability"],
                    }
                ],
            },
        )

    backend = APIBackend("https://folio.example")
    backend._client = httpx.AsyncClient(
        base_url="https://folio.example", transport=httpx.MockTransport(handler)
    )
    try:
        payload = json.loads(await backend.search_expanded("my landlord won't fix the heat", 5))
    finally:
        await backend.close()
    assert seen["path"] == "/search/llm/expanded"
    assert seen["params"] == {
        "query": "my landlord won't fix the heat",
        "limit": "5",
        "include_definitions": "false",
    }
    assert payload["expansion_source"] == "cache"
    assert payload["results"][0] == {
        "iri": IRI,
        "label": LABEL,
        "definition": None,
        "score": 0.03,
        "matched_via": ["Implied Warranty of Habitability"],
    }


@pytest.mark.asyncio
async def test_api_backend_search_expanded_http_error():
    backend = APIBackend("https://folio.example")
    backend._client = httpx.AsyncClient(
        base_url="https://folio.example",
        transport=httpx.MockTransport(lambda request: httpx.Response(429)),
    )
    try:
        payload = json.loads(await backend.search_expanded("heat", 5))
    finally:
        await backend.close()
    assert "error" in payload


def test_backends_satisfy_protocol():
    assert isinstance(LocalBackend(ExpandingFolio()), FOLIOBackend)
    assert isinstance(APIBackend(), FOLIOBackend)


@pytest.mark.asyncio
async def test_search_expanded_tool_registered():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert "search_expanded" in tools
    description = tools["search_expanded"].description
    assert "natural-language" in description
    assert "search_concepts" in description


@pytest.mark.asyncio
async def test_search_expanded_tool_end_to_end(monkeypatch):
    from mcp.shared.memory import create_connected_server_and_client_session

    from folio_mcp import server

    folio = ExpandingFolio()
    monkeypatch.setattr(server, "_shared_backend", LocalBackend(folio))
    async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
        ok = await client.call_tool(
            "search_expanded", {"query": "  my landlord won't fix the heat ", "limit": 100000}
        )
        bad = await client.call_tool("search_expanded", {"query": " "})
    payload = json.loads(ok.content[0].text)
    assert not ok.isError
    assert payload["results"][0]["iri"] == IRI
    assert folio.calls == [("my landlord won't fix the heat", 50, False)]
    assert "error" in json.loads(bad.content[0].text)
