"""
Tests for FOLIO MCP server tools.

Tests exercise the backend logic directly (no MCP transport needed)
using a real FOLIO graph instance via the LocalBackend.
"""

import json

import pytest
from folio import FOLIO

from folio_mcp.backends._branch_data import BRANCH_METHODS, BRANCH_NAMES
from folio_mcp.backends.local import (
    LocalBackend,
    format_search_results,
    owl_class_to_dict,
    owl_property_to_dict,
    resolve_iri,
)


# ── IRI Resolution ─────────────────────────────────────────────────────


class TestResolveIri:
    def test_resolve_short_iri(self, folio_graph: FOLIO):
        """Short IRI (just the ID part) should resolve to a class."""
        entity, entity_type = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        assert entity_type == "class"
        assert entity.label is not None

    def test_resolve_full_iri(self, folio_graph: FOLIO):
        """Full FOLIO IRI should resolve to a class."""
        entity, entity_type = resolve_iri(
            folio_graph, "https://folio.openlegalstandard.org/RSYBzf149Mi5KE0YtmpUmr"
        )
        assert entity is not None
        assert entity_type == "class"

    def test_resolve_nonexistent(self, folio_graph: FOLIO):
        """Non-existent IRI should return None."""
        entity, entity_type = resolve_iri(folio_graph, "ZZZZ_nonexistent_iri_ZZZZ")
        assert entity is None
        assert entity_type is None


# ── Search ─────────────────────────────────────────────────────────────


class TestSearch:
    def test_search_by_label_returns_results(self, folio_graph: FOLIO):
        """Searching for 'bankruptcy' should return relevant results."""
        results = folio_graph.search_by_label("bankruptcy", limit=5)
        assert len(results) > 0
        formatted = format_search_results(results)
        parsed = json.loads(formatted)
        assert len(parsed) > 0
        assert all("iri" in r and "label" in r for r in parsed)

    def test_search_by_label_nonsense(self, folio_graph: FOLIO):
        """Searching for nonsense should return empty or low-quality results."""
        results = folio_graph.search_by_label("xyzzy_qqq_nonexistent_term", limit=5)
        formatted = format_search_results(results)
        parsed = json.loads(formatted)
        assert isinstance(parsed, list)

    def test_search_by_definition(self, folio_graph: FOLIO):
        """Definition search should return results."""
        results = folio_graph.search_by_definition("financial obligation", limit=5)
        assert len(results) > 0
        formatted = format_search_results(results)
        parsed = json.loads(formatted)
        assert len(parsed) > 0


# ── Concept Access ─────────────────────────────────────────────────────


class TestGetConcept:
    def test_get_concept_json(self, folio_graph: FOLIO):
        """Getting a concept should return valid JSON."""
        entity, _ = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        json_str = entity.to_json()
        parsed = json.loads(json_str)
        assert "iri" in parsed
        assert "label" in parsed

    def test_owl_class_to_dict(self, folio_graph: FOLIO):
        """Compact dict should contain essential fields."""
        entity, _ = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        d = owl_class_to_dict(entity)
        assert "iri" in d
        assert "label" in d


# ── Export Formats ─────────────────────────────────────────────────────


class TestExportConcept:
    def test_export_markdown(self, folio_graph: FOLIO):
        """Markdown export should contain the concept label."""
        entity, _ = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        md = entity.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_export_jsonld(self, folio_graph: FOLIO):
        """JSON-LD export should be a valid dict with @context."""
        entity, _ = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        jsonld = entity.to_jsonld()
        assert isinstance(jsonld, dict)
        assert "@context" in jsonld

    def test_export_owl_xml(self, folio_graph: FOLIO):
        """OWL XML export should contain XML markup."""
        entity, _ = resolve_iri(folio_graph, "RSYBzf149Mi5KE0YtmpUmr")
        assert entity is not None
        xml = entity.to_owl_xml()
        assert isinstance(xml, str)
        assert "<?xml" in xml or "<owl:Class" in xml or "<Class" in xml


# ── Branches ───────────────────────────────────────────────────────────


class TestBranches:
    def test_list_branches_has_24_entries(self):
        """BRANCH_METHODS should have 24 entries."""
        assert len(BRANCH_METHODS) == 24

    def test_branch_names_match(self):
        """BRANCH_NAMES list should match BRANCH_METHODS keys."""
        assert set(BRANCH_NAMES) == set(BRANCH_METHODS.keys())

    def test_branch_methods_exist(self, folio_graph: FOLIO):
        """Every branch method in the dispatch map should exist on FOLIO."""
        for branch_name, method_name in BRANCH_METHODS.items():
            assert hasattr(folio_graph, method_name), f"Missing method: {method_name} for branch {branch_name}"

    def test_get_taxonomy_branch_valid(self, folio_graph: FOLIO):
        """Getting a valid branch should return concepts."""
        method = getattr(folio_graph, BRANCH_METHODS["areas_of_law"])
        concepts = method(max_depth=1)
        assert len(concepts) > 0
        d = owl_class_to_dict(concepts[0])
        assert "iri" in d
        assert "label" in d

    def test_branch_counts_positive(self, folio_graph: FOLIO):
        """Each branch should have at least one concept."""
        for branch_name, method_name in BRANCH_METHODS.items():
            method = getattr(folio_graph, method_name)
            concepts = method(max_depth=1)
            assert len(concepts) > 0, f"Branch {branch_name} has no concepts"


# ── Children/Parents ──────────────────────────────────────────────────


class TestTraversal:
    def test_get_children(self, folio_graph: FOLIO):
        """Getting children of a known parent should return results."""
        children = folio_graph.get_children("RSYBzf149Mi5KE0YtmpUmr", max_depth=1)
        assert len(children) > 0

    def test_get_parents(self, folio_graph: FOLIO):
        """Getting parents of a known child should return results."""
        children = folio_graph.get_children("RSYBzf149Mi5KE0YtmpUmr", max_depth=1)
        assert len(children) > 0
        child_iri = children[0].iri
        parents = folio_graph.get_parents(child_iri, max_depth=1)
        assert len(parents) > 0


# ── Properties ─────────────────────────────────────────────────────────


class TestProperties:
    def test_get_all_properties(self, folio_graph: FOLIO):
        """Getting all properties should return a non-empty list."""
        props = folio_graph.get_all_properties()
        assert len(props) > 0
        d = owl_property_to_dict(props[0])
        assert "iri" in d
        assert "label" in d

    def test_property_resolution(self, folio_graph: FOLIO):
        """Resolving a property IRI should work."""
        props = folio_graph.get_all_properties()
        assert len(props) > 0
        prop_iri = props[0].iri
        entity, entity_type = resolve_iri(folio_graph, prop_iri)
        assert entity is not None
        assert entity_type == "property"


# ── Connections ────────────────────────────────────────────────────────


class TestConnections:
    def test_find_connections(self, folio_graph: FOLIO):
        """Finding connections for a known subject should return triples."""
        connections = folio_graph.find_connections(
            subject_class="RSYBzf149Mi5KE0YtmpUmr"
        )
        assert isinstance(connections, list)


# ── Backend Integration ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestLocalBackend:
    async def test_search_by_label(self, local_backend: LocalBackend):
        result = await local_backend.search_by_label("bankruptcy", 5)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert all("iri" in r for r in parsed)

    async def test_search_by_definition(self, local_backend: LocalBackend):
        result = await local_backend.search_by_definition("financial obligation", 5)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_get_concept(self, local_backend: LocalBackend):
        result = await local_backend.get_concept("RSYBzf149Mi5KE0YtmpUmr")
        parsed = json.loads(result)
        assert "iri" in parsed
        assert "label" in parsed

    async def test_get_concept_not_found(self, local_backend: LocalBackend):
        result = await local_backend.get_concept("ZZZZ_nonexistent")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_export_markdown(self, local_backend: LocalBackend):
        result = await local_backend.export_concept("RSYBzf149Mi5KE0YtmpUmr", "markdown")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_export_jsonld(self, local_backend: LocalBackend):
        result = await local_backend.export_concept("RSYBzf149Mi5KE0YtmpUmr", "jsonld")
        parsed = json.loads(result)
        assert "@context" in parsed

    async def test_export_invalid_format(self, local_backend: LocalBackend):
        result = await local_backend.export_concept("RSYBzf149Mi5KE0YtmpUmr", "invalid")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_list_branches(self, local_backend: LocalBackend):
        result = await local_backend.list_branches()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert len(parsed) == 24

    async def test_get_taxonomy_branch(self, local_backend: LocalBackend):
        result = await local_backend.get_taxonomy_branch("areas_of_law", 1)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_get_taxonomy_branch_invalid(self, local_backend: LocalBackend):
        result = await local_backend.get_taxonomy_branch("nonexistent_branch", 1)
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_get_children(self, local_backend: LocalBackend):
        result = await local_backend.get_children("RSYBzf149Mi5KE0YtmpUmr", 1)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_get_parents(self, local_backend: LocalBackend):
        # Get a child first
        children_result = await local_backend.get_children("RSYBzf149Mi5KE0YtmpUmr", 1)
        children = json.loads(children_result)
        assert len(children) > 0
        child_iri = children[0]["iri"]
        result = await local_backend.get_parents(child_iri, 1)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_get_properties(self, local_backend: LocalBackend):
        result = await local_backend.get_properties()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_find_connections(self, local_backend: LocalBackend):
        result = await local_backend.find_connections("RSYBzf149Mi5KE0YtmpUmr", None, None)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    async def test_get_stats_resource(self, local_backend: LocalBackend):
        result = await local_backend.get_stats_resource()
        parsed = json.loads(result)
        assert "num_classes" in parsed
        assert "num_properties" in parsed
        assert parsed["num_classes"] > 0

    # ── query_concepts tests ──────────────────────────────────────────

    async def test_query_by_label_substring(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label="bankruptcy", definition=None, alt_label=None, example=None,
            any_text=None, branch=None, parent_iri=None, has_children=None,
            deprecated=False, country=None, match_mode="substring", limit=10,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert all("iri" in r and "label" in r for r in parsed)

    async def test_query_by_branch(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label=None, definition=None, alt_label=None, example=None,
            any_text="trust", branch="AREA_OF_LAW", parent_iri=None,
            has_children=None, deprecated=False, country=None,
            match_mode="substring", limit=10,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_query_by_regex(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label="^Contract", definition=None, alt_label=None, example=None,
            any_text=None, branch=None, parent_iri=None, has_children=None,
            deprecated=False, country=None, match_mode="regex", limit=5,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_query_has_children_filter(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label="law", definition=None, alt_label=None, example=None,
            any_text=None, branch=None, parent_iri=None, has_children=True,
            deprecated=False, country=None, match_mode="substring", limit=5,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        # All results should have children
        assert all("child_iris" in r for r in parsed)

    async def test_query_no_results(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label="xyzzy_nonexistent_zzzz", definition=None, alt_label=None,
            example=None, any_text=None, branch=None, parent_iri=None,
            has_children=None, deprecated=False, country=None,
            match_mode="exact", limit=5,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 0

    async def test_query_invalid_branch(self, local_backend: LocalBackend):
        result = await local_backend.query_concepts(
            label=None, definition=None, alt_label=None, example=None,
            any_text="test", branch="NONEXISTENT_BRANCH", parent_iri=None,
            has_children=None, deprecated=False, country=None,
            match_mode="substring", limit=5,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 0

    # ── query_properties tests ────────────────────────────────────────

    async def test_query_properties_by_label(self, local_backend: LocalBackend):
        result = await local_backend.query_properties(
            label="has", definition=None, domain_iri=None, range_iri=None,
            has_inverse=None, match_mode="substring", limit=10,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    async def test_query_properties_has_inverse(self, local_backend: LocalBackend):
        result = await local_backend.query_properties(
            label=None, definition=None, domain_iri=None, range_iri=None,
            has_inverse=True, match_mode="substring", limit=10,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        # All should have inverse_of
        for p in parsed:
            assert "inverse_of" in p
