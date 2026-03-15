"""
MCP server for FOLIO, the Federated Open Legal Information Ontology.

Provides 10 tools and 2 resources for searching, browsing, and exporting
concepts from the FOLIO legal ontology (18,000+ concepts, CC-BY 4.0).
"""

# imports
import json
from contextlib import asynccontextmanager
from typing import Optional

# packages
from folio import FOLIO
from mcp.server.fastmcp import FastMCP

# project imports
from folio_mcp.helpers import (
    format_search_results,
    owl_class_to_dict,
    owl_property_to_dict,
    resolve_iri,
)

# Module-level FOLIO instance (set during lifespan or externally)
_folio_instance: Optional[FOLIO] = None


def set_shared_folio(folio_instance: FOLIO) -> None:
    """Set a shared FOLIO instance for use by the MCP server.

    Call this before starting the server to share a FOLIO graph
    (e.g., when mounting inside folio-api to avoid double-loading).
    """
    global _folio_instance
    _folio_instance = folio_instance


@asynccontextmanager
async def app_lifespan(server):
    """Initialize FOLIO once at server startup."""
    global _folio_instance
    if _folio_instance is None:
        _folio_instance = FOLIO()
    yield {"folio": _folio_instance}


# Branch dispatch map: user-facing name -> FOLIO method name
BRANCH_METHODS = {
    "actors_players": "get_player_actors",
    "areas_of_law": "get_areas_of_law",
    "asset_types": "get_asset_types",
    "communication_modalities": "get_communication_modalities",
    "currencies": "get_currencies",
    "data_formats": "get_data_formats",
    "document_artifacts": "get_document_artifacts",
    "engagement_terms": "get_engagement_terms",
    "events": "get_events",
    "forum_venues": "get_forum_venues",
    "governmental_bodies": "get_governmental_bodies",
    "industries": "get_industries",
    "languages": "get_languages",
    "folio_types": "get_folio_types",
    "legal_authorities": "get_legal_authorities",
    "legal_entities": "get_legal_entities",
    "locations": "get_locations",
    "matter_narratives": "get_matter_narratives",
    "matter_narrative_formats": "get_matter_narrative_formats",
    "objectives": "get_objectives",
    "services": "get_services",
    "standards_compatibilities": "get_standards_compatibilities",
    "statuses": "get_statuses",
    "system_identifiers": "get_system_identifiers",
}

# Create the MCP server
mcp = FastMCP(
    "FOLIO Legal Ontology",
    instructions=(
        "Access FOLIO, the Federated Open Legal Information Ontology. "
        "Search, browse, and export 18,000+ legal concepts covering areas of law, "
        "document types, legal entities, and more."
    ),
    lifespan=app_lifespan,
)


def _get_folio(ctx) -> FOLIO:
    """Extract the FOLIO instance from the MCP context."""
    return ctx.request_context.lifespan_context["folio"]


# ── Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
def search_concepts(ctx, query: str, limit: int = 10) -> str:
    """Search FOLIO concepts by label (name).

    Finds legal concepts whose names match the query using fuzzy matching.
    Use this as the primary entry point for finding concepts.

    Args:
        query: Search term (e.g., "bankruptcy", "software license", "trust").
        limit: Maximum number of results to return (default 10).

    Returns:
        JSON array of matching concepts with iri, label, definition, and score.
    """
    folio = _get_folio(ctx)
    results = folio.search_by_label(query, limit=limit)
    return format_search_results(results)


@mcp.tool()
def search_definitions(ctx, query: str, limit: int = 10) -> str:
    """Search FOLIO concepts by definition text.

    Finds legal concepts whose definitions match the query. Use this when
    searching by name doesn't find what you need.

    Args:
        query: Search term to match against definitions.
        limit: Maximum number of results to return (default 10).

    Returns:
        JSON array of matching concepts with iri, label, definition, and score.
    """
    folio = _get_folio(ctx)
    results = folio.search_by_definition(query, limit=limit)
    return format_search_results(results)


@mcp.tool()
def get_concept(ctx, iri: str) -> str:
    """Get full details for a specific FOLIO concept by IRI.

    Accepts short IDs (e.g., "RSYBzf149Mi5KE0YtmpUmr"), full IRIs
    (e.g., "https://folio.openlegalstandard.org/RSYBzf149Mi5KE0YtmpUmr"),
    or partial matches.

    Args:
        iri: The concept IRI or identifier.

    Returns:
        Full JSON representation of the concept, or an error message.
    """
    folio = _get_folio(ctx)
    entity, entity_type = resolve_iri(folio, iri)
    if entity is None:
        return json.dumps({"error": f"Concept not found: {iri}"})
    if entity_type == "class":
        return entity.to_json()
    return json.dumps(owl_property_to_dict(entity))


@mcp.tool()
def export_concept(ctx, iri: str, format: str = "markdown") -> str:
    """Export a FOLIO concept in a specific format.

    Args:
        iri: The concept IRI or identifier.
        format: Output format — "markdown", "jsonld", or "owl_xml".

    Returns:
        The concept in the requested format, or an error message.
    """
    folio = _get_folio(ctx)
    entity, entity_type = resolve_iri(folio, iri)
    if entity is None:
        return json.dumps({"error": f"Concept not found: {iri}"})

    if entity_type == "property":
        # Properties only support JSON serialization
        return json.dumps(owl_property_to_dict(entity))

    if format == "markdown":
        return entity.to_markdown()
    elif format == "jsonld":
        return json.dumps(entity.to_jsonld(), indent=2)
    elif format == "owl_xml":
        return entity.to_owl_xml()
    else:
        return json.dumps({"error": f"Unsupported format: {format}. Use 'markdown', 'jsonld', or 'owl_xml'."})


@mcp.tool()
def list_branches(ctx) -> str:
    """List all FOLIO taxonomy branches with concept counts.

    Returns the 24 top-level categories of the FOLIO ontology
    (e.g., areas_of_law, document_artifacts, legal_entities).

    Returns:
        JSON object mapping branch names to concept counts.
    """
    folio = _get_folio(ctx)
    result = {}
    for branch_name, method_name in BRANCH_METHODS.items():
        method = getattr(folio, method_name)
        concepts = method(max_depth=1)
        result[branch_name] = len(concepts)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_taxonomy_branch(ctx, branch_name: str, max_depth: int = 1) -> str:
    """Get all concepts in a specific FOLIO taxonomy branch.

    Args:
        branch_name: Branch name (e.g., "areas_of_law", "document_artifacts").
            Use list_branches() to see all available branch names.
        max_depth: Maximum depth to traverse (default 1 for direct children only).

    Returns:
        JSON array of concepts in the branch, or an error message.
    """
    if branch_name not in BRANCH_METHODS:
        return json.dumps({
            "error": f"Unknown branch: {branch_name}",
            "available_branches": list(BRANCH_METHODS.keys()),
        })

    folio = _get_folio(ctx)
    method = getattr(folio, BRANCH_METHODS[branch_name])
    concepts = method(max_depth=max_depth)
    return json.dumps([owl_class_to_dict(c) for c in concepts], indent=2)


@mcp.tool()
def get_children(ctx, iri: str, max_depth: int = 1) -> str:
    """Get child concepts of a given FOLIO concept.

    Args:
        iri: The parent concept IRI or identifier.
        max_depth: Maximum depth to traverse (default 1).

    Returns:
        JSON array of child concepts, or an error message.
    """
    folio = _get_folio(ctx)
    entity, entity_type = resolve_iri(folio, iri)
    if entity is None:
        return json.dumps({"error": f"Concept not found: {iri}"})

    children = folio.get_children(entity.iri, max_depth=max_depth)
    return json.dumps([owl_class_to_dict(c) for c in children], indent=2)


@mcp.tool()
def get_parents(ctx, iri: str, max_depth: int = 1) -> str:
    """Get parent concepts of a given FOLIO concept.

    Args:
        iri: The child concept IRI or identifier.
        max_depth: Maximum depth to traverse (default 1).

    Returns:
        JSON array of parent concepts, or an error message.
    """
    folio = _get_folio(ctx)
    entity, entity_type = resolve_iri(folio, iri)
    if entity is None:
        return json.dumps({"error": f"Concept not found: {iri}"})

    parents = folio.get_parents(entity.iri, max_depth=max_depth)
    return json.dumps([owl_class_to_dict(c) for c in parents], indent=2)


@mcp.tool()
def get_properties(ctx) -> str:
    """Get all OWL object properties defined in the FOLIO ontology.

    Returns properties that describe relationships between concepts
    (e.g., "hasJurisdiction", "appliesTo", "governedBy").

    Returns:
        JSON array of properties with iri, label, definition, domain, and range.
    """
    folio = _get_folio(ctx)
    props = folio.get_all_properties()
    return json.dumps([owl_property_to_dict(p) for p in props], indent=2)


@mcp.tool()
def find_connections(
    ctx,
    subject_iri: str,
    property_name: Optional[str] = None,
    object_iri: Optional[str] = None,
) -> str:
    """Find semantic connections (triples) between FOLIO concepts.

    Searches for subject-property-object triples. At minimum, provide a
    subject_iri. Optionally filter by property and/or object.

    Args:
        subject_iri: IRI of the subject concept.
        property_name: Optional property name or IRI to filter by.
        object_iri: Optional object concept IRI to filter by.

    Returns:
        JSON array of triples [{subject: {...}, property: {...}, object: {...}}].
    """
    folio = _get_folio(ctx)
    entity, entity_type = resolve_iri(folio, subject_iri)
    if entity is None:
        return json.dumps({"error": f"Subject not found: {subject_iri}"})

    connections = folio.find_connections(
        subject_class=entity.iri,
        property_name=property_name,
        object_class=object_iri,
    )

    result = []
    for subj, prop, obj in connections:
        result.append({
            "subject": {"iri": subj.iri, "label": subj.label},
            "property": {"iri": prop.iri, "label": prop.label},
            "object": {"iri": obj.iri, "label": obj.label},
        })
    return json.dumps(result, indent=2)


# ── Resources ──────────────────────────────────────────────────────────


@mcp.resource("folio://branches")
def branches_resource() -> str:
    """FOLIO taxonomy branch names with concept counts."""
    folio = _folio_instance
    result = {}
    for branch_name, method_name in BRANCH_METHODS.items():
        method = getattr(folio, method_name)
        concepts = method(max_depth=1)
        result[branch_name] = len(concepts)
    return json.dumps(result, indent=2)


@mcp.resource("folio://stats")
def stats_resource() -> str:
    """FOLIO ontology statistics."""
    folio = _folio_instance
    return json.dumps({
        "version": getattr(folio, "version", None),
        "title": getattr(folio, "title", None),
        "num_classes": len(folio.classes),
        "num_properties": len(folio.object_properties),
        "source": "https://openlegalstandard.org/",
        "license": "CC-BY 4.0",
    }, indent=2)


# ── Entry point ────────────────────────────────────────────────────────


def main():
    """Run the FOLIO MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
