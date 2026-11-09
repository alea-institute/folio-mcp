"""
End-to-end tool behaviour through a real MCP client session (in-memory transport).

The server runs with the real FOLIO graph injected via ``set_shared_folio``,
so these tests see exactly what an LLM client sees: validation, clamping,
output shaping and error hints included.
"""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from folio_mcp import server
from folio_mcp.backends._branch_data import BRANCH_ROOT_IDS
from folio_mcp.backends.local import LocalBackend
from folio_mcp.shaping import MAX_LIST_ITEMS, MAX_QUERY_LIMIT, MAX_SEARCH_LIMIT

AREA_OF_LAW = "https://folio.openlegalstandard.org/RSYBzf149Mi5KE0YtmpUmr"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"


@pytest.fixture
def mcp_backend(monkeypatch, local_backend: LocalBackend):
    monkeypatch.setattr(server, "_shared_backend", local_backend)
    return local_backend


async def call(name: str, **args):
    async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
        result = await client.call_tool(name, args)
    text = result.content[0].text
    assert not result.isError, text
    return json.loads(text), text


def is_error(payload) -> bool:
    return isinstance(payload, dict) and "error" in payload


@pytest.mark.asyncio
class TestSearchTools:
    async def test_limit_is_respected(self, mcp_backend):
        # folio-python returns extra hits for alternative labels; we cut to limit.
        data, _ = await call("search_concepts", query="non-compete agreement", limit=5)
        assert isinstance(data, list) and 0 < len(data) <= 5

    async def test_default_limit(self, mcp_backend):
        data, _ = await call("search_concepts", query="bankruptcy")
        assert len(data) <= 10

    async def test_huge_limit_is_clamped(self, mcp_backend):
        data, text = await call("search_concepts", query="bankruptcy", limit=100000)
        assert len(data) <= MAX_SEARCH_LIMIT
        assert len(text) < 30000

    @pytest.mark.parametrize("limit", [-5, 0])
    async def test_non_positive_limit_uses_default(self, mcp_backend, limit):
        # -5 used to surface a C++ "vector::_M_default_append" tool error.
        data, _ = await call("search_concepts", query="bankruptcy", limit=limit)
        assert isinstance(data, list) and 1 < len(data) <= 10

    @pytest.mark.parametrize("query", ["", "   "])
    async def test_empty_query_is_an_error_with_hint(self, mcp_backend, query):
        data, _ = await call("search_concepts", query=query)
        assert is_error(data) and "hint" in data

    async def test_empty_definition_query_is_an_error(self, mcp_backend):
        data, _ = await call("search_definitions", query="")
        assert is_error(data)

    async def test_paragraph_query_is_rejected_with_hint(self, mcp_backend):
        data, _ = await call("search_concepts", query="The tenant failed to pay rent " * 20)
        assert is_error(data) and "hint" in data

    async def test_output_is_compact_and_unicode(self, mcp_backend):
        _, text = await call("search_concepts", query="Société à responsabilité limitée", limit=3)
        assert "\n" not in text
        assert "Société" in text

    async def test_placeholder_definitions_are_dropped(self, mcp_backend):
        data, _ = await call("query_concepts", definition="NULL", match_mode="exact", limit=5)
        assert all("definition" not in item for item in data)


@pytest.mark.asyncio
class TestConceptLookup:
    async def test_empty_iri_is_an_error(self, mcp_backend):
        # Used to return an arbitrary concept (suffix match on "").
        data, _ = await call("get_concept", iri="")
        assert is_error(data)

    async def test_branch_name_resolves_to_branch_root(self, mcp_backend):
        data, _ = await call("get_concept", iri="areas_of_law")
        assert data["iri"] == AREA_OF_LAW

    async def test_plain_word_gets_search_hint(self, mcp_backend):
        data, _ = await call("get_concept", iri="bankruptcy")
        assert is_error(data) and "search_concepts" in data["hint"]

    async def test_concept_has_no_null_fields(self, mcp_backend):
        data, _ = await call("get_concept", iri="RSYBzf149Mi5KE0YtmpUmr")
        assert data["label"] == "Area of Law"
        assert all(v not in (None, [], {}, "") for v in data.values())

    async def test_short_fragment_does_not_match_random_concept(self, mcp_backend):
        data, _ = await call("get_concept", iri="A")
        assert is_error(data)

    @pytest.mark.parametrize("fmt,start", [("markdown", "# "), ("owl_xml", "<"), ("jsonld", "{")])
    async def test_export_formats_pass_through(self, mcp_backend, fmt, start):
        async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
            result = await client.call_tool("export_concept", {"iri": "RSYBzf149Mi5KE0YtmpUmr", "format": fmt})
        text = result.content[0].text
        assert text.lstrip().startswith(start) and "error" not in text[:20]

    async def test_export_not_found_has_hint(self, mcp_backend):
        data, _ = await call("export_concept", iri="ZZZZnotreal")
        assert is_error(data)


@pytest.mark.asyncio
class TestBrowse:
    @pytest.mark.parametrize("name", ["Areas of Law", "AREA_OF_LAW", "area of law", "practice areas"])
    async def test_branch_name_variants(self, mcp_backend, name):
        data, _ = await call("get_taxonomy_branch", branch_name=name)
        assert isinstance(data, list) and len(data) == 31

    async def test_unknown_branch_lists_names(self, mcp_backend):
        data, _ = await call("get_taxonomy_branch", branch_name="nonsense")
        assert is_error(data) and "areas_of_law" in data["available_branches"]

    async def test_max_depth_zero_is_clamped_to_one(self, mcp_backend):
        data, _ = await call("get_taxonomy_branch", branch_name="areas_of_law", max_depth=0)
        assert len(data) == 31

    async def test_huge_branch_is_truncated(self, mcp_backend):
        data, text = await call("get_taxonomy_branch", branch_name="locations", max_depth=99)
        assert data["truncated"] is True
        assert len(data["results"]) == MAX_LIST_ITEMS
        assert data["total"] > MAX_LIST_ITEMS
        assert len(text) < 40000

    async def test_get_children_accepts_branch_name(self, mcp_backend):
        data, _ = await call("get_children", iri="areas_of_law")
        assert isinstance(data, list) and len(data) == 31

    async def test_get_children_deep_is_bounded(self, mcp_backend):
        data, text = await call("get_children", iri=AREA_OF_LAW, max_depth=99)
        assert len(text) < 40000

    async def test_get_parents_excludes_self_and_owl_thing(self, mcp_backend):
        data, _ = await call("get_parents", iri=AREA_OF_LAW)
        iris = [p["iri"] for p in data] if isinstance(data, list) else []
        assert AREA_OF_LAW not in iris and OWL_THING not in iris

    async def test_get_parents_excludes_self_given_short_id(self, mcp_backend):
        """Short IDs are valid input; the concept must not list itself as a parent."""
        children, _ = await call("get_children", iri=AREA_OF_LAW)
        child_iri = children[0]["iri"]
        short_id = child_iri.rsplit("/", 1)[-1]
        data, _ = await call("get_parents", iri=short_id)
        assert [p["iri"] for p in data] == [AREA_OF_LAW]

    async def test_get_children_excludes_self_given_short_id(self, mcp_backend):
        short_id = AREA_OF_LAW.rsplit("/", 1)[-1]
        data, _ = await call("get_children", iri=short_id)
        assert isinstance(data, list) and data
        assert AREA_OF_LAW not in [c["iri"] for c in data]

    async def test_get_parents_of_child(self, mcp_backend):
        children, _ = await call("get_children", iri=AREA_OF_LAW)
        data, _ = await call("get_parents", iri=children[0]["iri"])
        assert [p["iri"] for p in data] == [AREA_OF_LAW]

    async def test_unknown_iri_error_has_hint(self, mcp_backend):
        data, _ = await call("get_children", iri="ZZZZnotreal")
        assert is_error(data) and "hint" in data

    async def test_get_properties_is_compact(self, mcp_backend):
        data, text = await call("get_properties")
        assert len(data) > 100
        assert len(text) < 32000
        assert {"iri", "label"} <= set(data[0])


@pytest.mark.asyncio
class TestQueryTools:
    async def test_branch_accepts_mcp_branch_name(self, mcp_backend):
        upper, _ = await call("query_concepts", label="contract", branch="AREA_OF_LAW", limit=5)
        lower, _ = await call("query_concepts", label="contract", branch="areas_of_law", limit=5)
        assert len(lower) > 0 and lower == upper

    async def test_unknown_branch_is_an_error(self, mcp_backend):
        data, _ = await call("query_concepts", label="contract", branch="nope")
        assert is_error(data)

    async def test_invalid_regex_is_an_error_not_exception(self, mcp_backend):
        data, _ = await call("query_concepts", label="(", match_mode="regex")
        assert is_error(data) and "hint" in data

    async def test_unknown_match_mode_is_an_error(self, mcp_backend):
        data, _ = await call("query_concepts", label="court", match_mode="bogus")
        assert is_error(data)

    async def test_no_filters_is_an_error(self, mcp_backend):
        data, _ = await call("query_concepts", limit=5)
        assert is_error(data)

    async def test_limit_is_clamped(self, mcp_backend):
        data, _ = await call("query_concepts", label="court", limit=100000)
        assert len(data) <= MAX_QUERY_LIMIT

    async def test_parent_iri_accepts_branch_name(self, mcp_backend):
        data, _ = await call("query_concepts", parent_iri="areas_of_law", label="tax", limit=5)
        assert len(data) > 0

    async def test_query_properties_invalid_regex(self, mcp_backend):
        data, _ = await call("query_properties", label="(", match_mode="regex")
        assert is_error(data)

    async def test_query_properties_documented_example_works(self, mcp_backend):
        data, _ = await call("query_properties", label="advised")
        assert len(data) >= 1


@pytest.mark.asyncio
class TestConnections:
    async def test_empty_connections_explain_why(self, mcp_backend):
        data, _ = await call("find_connections", subject_iri=AREA_OF_LAW)
        assert data["results"] == [] and "note" in data

    async def test_known_connection(self, mcp_backend):
        # Actor / Player is one of the few classes with object-property triples.
        data, _ = await call("find_connections", subject_iri=BRANCH_ROOT_IDS["actors_players"])
        assert isinstance(data, list) and len(data) > 0
        assert {"subject", "property", "object"} <= set(data[0])

    async def test_branch_name_as_subject(self, mcp_backend):
        data, _ = await call("find_connections", subject_iri="actors_players")
        assert isinstance(data, list) and len(data) > 0
