"""
MCP server for FOLIO, the Federated Open Legal Information Ontology.

Provides 12 tools, 3 resources, and 3 prompt templates for searching,
browsing, and classifying concepts from the FOLIO legal ontology
(18,000+ concepts, CC-BY 4.0).

Supports two backends:
- API mode (default): Thin httpx client calling the public FOLIO REST API
- Local mode (--local): Loads full ontology in-process via folio-python
"""

# imports
import argparse
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

# packages
from mcp.server.fastmcp import Context, FastMCP

# project imports
from folio_mcp.backends._branch_data import BRANCH_METHODS, BRANCH_NAMES
from folio_mcp.backends.protocol import FOLIOBackend

# Module-level config and backend
_config = {
    "local": False,
    "api_url": "https://folio.openlegalstandard.org",
}
_shared_backend: Optional[FOLIOBackend] = None


def set_shared_folio(folio_instance) -> None:
    """Set a shared FOLIO instance for use by the MCP server.

    Call this before starting the server to share a FOLIO graph
    (e.g., when mounting inside folio-api to avoid double-loading).
    """
    global _shared_backend
    from folio_mcp.backends.local import LocalBackend
    _shared_backend = LocalBackend(folio_instance)


@asynccontextmanager
async def app_lifespan(server):
    """Initialize the backend at server startup."""
    global _shared_backend

    if _shared_backend is not None:
        backend = _shared_backend
    elif _config["local"] or os.environ.get("FOLIO_MCP_LOCAL", "").strip() in ("1", "true", "yes"):
        from folio_mcp.backends.local import LocalBackend
        backend = LocalBackend()
        # Eagerly load the graph
        _ = backend.folio
    else:
        from folio_mcp.backends.api import APIBackend
        backend = APIBackend(base_url=_config["api_url"])

    # Also store as _shared_backend so static resources (no ctx) can access it.
    # FastMCP treats resource handlers with any parameter (including ctx) as templates,
    # so static resources like folio://branches must be zero-arg functions.
    _shared_backend = backend

    try:
        yield {"backend": backend}
    finally:
        _shared_backend = None
        if hasattr(backend, "close"):
            await backend.close()


# Create the MCP server
mcp = FastMCP(
    "FOLIO Legal Ontology",
    instructions=(
        "Access FOLIO, the Federated Open Legal Information Ontology. "
        "Search, browse, and export 18,000+ legal concepts covering areas of law, "
        "document types, legal entities, and more.\n\n"
        "Workflow:\n"
        "1. search_concepts(query) — find concepts by name\n"
        "2. get_taxonomy_branch(branch_name) — browse a branch by name "
        "(e.g., 'areas_of_law', 'document_artifacts')\n"
        "3. get_concept(iri) — full details for a specific concept "
        "(translations, identifiers, cross-references)\n"
        "4. get_children(iri) / get_parents(iri) — navigate the taxonomy\n\n"
        "IRIs look like 'https://folio.openlegalstandard.org/R07tQM...' or short IDs like 'R07tQM...'. "
        "Branch names like 'areas_of_law' are NOT IRIs — use get_taxonomy_branch for those.\n\n"
        "Browse operations return compact summaries {iri, label, definition}. "
        "Use get_concept(iri) for the full record.\n\n"
        "Keep max_depth=1. Navigate incrementally with get_children instead of deep traversal.\n\n"
        "Classification workflows (available as slash commands):\n"
        "- /folio:classify-document — classify a legal document against the document_artifacts taxonomy\n"
        "- /folio:identify-area-of-law — identify areas of law for a legal situation\n"
        "- /folio:classify-entity — classify a legal entity against actors_players and legal_entities\n"
        "Suggest these when users need to classify, categorize, or identify legal concepts."
    ),
    lifespan=app_lifespan,
)


def _get_backend(ctx: Context) -> FOLIOBackend:
    """Extract the backend from the MCP context."""
    return ctx.request_context.lifespan_context["backend"]


# ── Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
async def search_concepts(ctx: Context, query: str, limit: int = 10) -> str:
    """Search FOLIO concepts by label (name).

    Finds legal concepts whose names match the query using fuzzy matching.
    Use this as the primary entry point for finding concepts.

    Args:
        query: Search term (e.g., "bankruptcy", "software license", "trust").
        limit: Maximum number of results to return (default 10).

    Returns:
        JSON array of matching concepts with iri, label, definition, and score.
    """
    return await _get_backend(ctx).search_by_label(query, limit)


@mcp.tool()
async def search_definitions(ctx: Context, query: str, limit: int = 10) -> str:
    """Search FOLIO concepts by definition text.

    Finds legal concepts whose definitions match the query. Use this when
    searching by name doesn't find what you need.

    Args:
        query: Search term to match against definitions.
        limit: Maximum number of results to return (default 10).

    Returns:
        JSON array of matching concepts with iri, label, definition, and score.
    """
    return await _get_backend(ctx).search_by_definition(query, limit)


@mcp.tool()
async def get_concept(ctx: Context, iri: str) -> str:
    """Get full details for a specific FOLIO concept by IRI.

    Accepts short IDs (e.g., "RSYBzf149Mi5KE0YtmpUmr"), full IRIs
    (e.g., "https://folio.openlegalstandard.org/RSYBzf149Mi5KE0YtmpUmr"),
    or partial matches.

    Args:
        iri: The concept IRI or identifier.

    Returns:
        Full JSON representation of the concept, or an error message.
    """
    return await _get_backend(ctx).get_concept(iri)


@mcp.tool()
async def export_concept(ctx: Context, iri: str, format: str = "markdown") -> str:
    """Export a FOLIO concept in a specific format.

    Args:
        iri: The concept IRI or identifier.
        format: Output format — "markdown", "jsonld", or "owl_xml".

    Returns:
        The concept in the requested format, or an error message.
    """
    return await _get_backend(ctx).export_concept(iri, format)


@mcp.tool()
async def list_branches(ctx: Context) -> str:
    """List all FOLIO taxonomy branches with concept counts.

    Returns the 24 top-level categories of the FOLIO ontology
    (e.g., areas_of_law, document_artifacts, legal_entities).

    Returns:
        JSON object mapping branch names to concept counts.
    """
    return await _get_backend(ctx).list_branches()


@mcp.tool()
async def get_taxonomy_branch(ctx: Context, branch_name: str, max_depth: int = 1) -> str:
    """Get concepts in a FOLIO taxonomy branch. Returns compact summaries.

    Args:
        branch_name: Branch name (e.g., "areas_of_law", "document_artifacts").
            Use list_branches() to see all available branch names.
        max_depth: Depth limit. Use 1 (default) for top-level only.
            WARNING: depth >2 can return very large results.
            Navigate incrementally with get_children() instead.

    Returns:
        JSON array of {iri, label, definition} summaries.
        Use get_concept(iri) for full details on a specific concept.
    """
    return await _get_backend(ctx).get_taxonomy_branch(branch_name, min(max_depth, 3))


@mcp.tool()
async def get_children(ctx: Context, iri: str, max_depth: int = 1) -> str:
    """Get child concepts of a FOLIO concept. Returns compact summaries.

    Args:
        iri: A concept IRI (e.g., "https://folio.openlegalstandard.org/R07tQM...")
            or short ID (e.g., "R07tQM..."). NOT a branch name — use
            get_taxonomy_branch for branch names like "areas_of_law".
        max_depth: Depth limit (default 1 for direct children).
            Keep at 1-2 to avoid large results.

    Returns:
        JSON array of {iri, label, definition} summaries.
        Use get_concept(iri) for full details on a specific child.
    """
    return await _get_backend(ctx).get_children(iri, min(max_depth, 3))


@mcp.tool()
async def get_parents(ctx: Context, iri: str, max_depth: int = 1) -> str:
    """Get parent concepts of a FOLIO concept. Returns compact summaries.

    Args:
        iri: A concept IRI (e.g., "https://folio.openlegalstandard.org/R07tQM...")
            or short ID. NOT a branch name.
        max_depth: Depth limit (default 1 for direct parents).

    Returns:
        JSON array of {iri, label, definition} summaries.
        Use get_concept(iri) for full details on a specific parent.
    """
    return await _get_backend(ctx).get_parents(iri, max_depth)


@mcp.tool()
async def get_properties(ctx: Context) -> str:
    """Get all OWL object properties defined in the FOLIO ontology.

    Returns properties that describe relationships between concepts
    (e.g., "hasJurisdiction", "appliesTo", "governedBy").

    Returns:
        JSON array of properties with iri, label, definition, domain, and range.
    """
    return await _get_backend(ctx).get_properties()


@mcp.tool()
async def find_connections(
    ctx: Context,
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
    return await _get_backend(ctx).find_connections(subject_iri, property_name, object_iri)


@mcp.tool()
async def query_concepts(
    ctx: Context,
    label: Optional[str] = None,
    definition: Optional[str] = None,
    alt_label: Optional[str] = None,
    example: Optional[str] = None,
    any_text: Optional[str] = None,
    branch: Optional[str] = None,
    parent_iri: Optional[str] = None,
    has_children: Optional[bool] = None,
    deprecated: bool = False,
    country: Optional[str] = None,
    match_mode: str = "substring",
    limit: int = 20,
) -> str:
    """Query FOLIO concepts with composable text and structural filters.

    More powerful than search_concepts — supports field-specific matching,
    structural constraints, and multiple match modes. All specified filters
    must match (AND logic).

    Text filters:
        label: Match against the concept's primary label (rdfs:label).
        definition: Match against the concept's definition (skos:definition).
        alt_label: Match against alternative labels (skos:altLabel).
        example: Match against examples (skos:example).
        any_text: Match against ALL text fields (label, definition, alt_labels, examples, notes, comment).

    Structural filters:
        branch: Limit to a taxonomy branch (e.g., "AREA_OF_LAW", "CURRENCY", "LEGAL_ENTITY").
        parent_iri: Only descendants of this IRI (transitive subClassOf).
        has_children: True = non-leaf concepts only, False = leaf concepts only.
        deprecated: Include deprecated concepts (default False).
        country: Match against the country field.

    Control:
        match_mode: "substring" (default), "exact", "regex", or "fuzzy".
        limit: Maximum results (default 20).

    Returns:
        JSON array of matching concepts.
    """
    return await _get_backend(ctx).query_concepts(
        label=label,
        definition=definition,
        alt_label=alt_label,
        example=example,
        any_text=any_text,
        branch=branch,
        parent_iri=parent_iri,
        has_children=has_children,
        deprecated=deprecated,
        country=country,
        match_mode=match_mode,
        limit=limit,
    )


@mcp.tool()
async def query_properties(
    ctx: Context,
    label: Optional[str] = None,
    definition: Optional[str] = None,
    domain_iri: Optional[str] = None,
    range_iri: Optional[str] = None,
    has_inverse: Optional[bool] = None,
    match_mode: str = "substring",
    limit: int = 20,
) -> str:
    """Query FOLIO object properties with composable text and structural filters.

    Replaces get_properties() when you need filtered results instead of the full list.

    Text filters:
        label: Match against property label (e.g., "jurisdiction", "applies").
        definition: Match against property definition.

    Structural filters:
        domain_iri: Only properties whose domain includes this class IRI.
        range_iri: Only properties whose range includes this class IRI.
        has_inverse: True = only properties with inverses, False = only without.

    Control:
        match_mode: "substring" (default), "exact", "regex", or "fuzzy".
        limit: Maximum results (default 20).

    Returns:
        JSON array of matching properties with iri, label, definition, domain, range.
    """
    return await _get_backend(ctx).query_properties(
        label=label,
        definition=definition,
        domain_iri=domain_iri,
        range_iri=range_iri,
        has_inverse=has_inverse,
        match_mode=match_mode,
        limit=limit,
    )


# ── Resources ──────────────────────────────────────────────────────────


@mcp.resource("folio://branches")
async def branches_resource() -> str:
    """FOLIO taxonomy branch names with concept counts."""
    return await _shared_backend.get_branches_resource()


@mcp.resource("folio://stats")
async def stats_resource() -> str:
    """FOLIO ontology statistics."""
    return await _shared_backend.get_stats_resource()


@mcp.resource(
    "folio://branch/{branch_name}",
    description="Top-level concepts in a FOLIO taxonomy branch. "
    "Use folio://branches to see available branch names.",
)
async def branch_resource(branch_name: str) -> str:
    """Get top-level concepts for a specific FOLIO taxonomy branch."""
    return await _shared_backend.get_taxonomy_branch(branch_name, max_depth=1)


# ── Prompts ────────────────────────────────────────────────────────────


from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage


@mcp.prompt(
    name="classify-document",
    description="Classify a legal document using the FOLIO ontology. "
    "Provide a document name or description and get the best FOLIO classification.",
)
def classify_document(description: str) -> list:
    """Classify a legal document against the FOLIO document taxonomy."""
    return [
        UserMessage(
            f"Classify this legal document using the FOLIO ontology:\n\n"
            f'"{description}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching document types\n"
            f"2. If no good match, browse the document_artifacts branch with "
            f"get_taxonomy_branch to see the 8 top-level document categories\n"
            f"3. Use get_children on the best category to find the specific type\n"
            f"4. Use get_concept on the best match to get full details\n\n"
            f"Return the classification as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Parent category\n"
            f"- Confidence (high/medium/low)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="identify-area-of-law",
    description="Identify the area(s) of law that apply to a legal situation or matter.",
)
def identify_area_of_law(situation: str) -> list:
    """Identify areas of law for a legal situation."""
    return [
        UserMessage(
            f"Identify the area(s) of law that apply to this situation "
            f"using the FOLIO ontology:\n\n"
            f'"{situation}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find relevant areas of law\n"
            f"2. Also browse the areas_of_law branch with get_taxonomy_branch "
            f"to review all 31 top-level areas\n"
            f"3. Use get_children on promising areas to check sub-specialties\n"
            f"4. Use get_concept on each match for full details and translations\n\n"
            f"Return each applicable area as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Relevance (primary/secondary)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="classify-entity",
    description="Classify a legal entity (person, organization, role) using FOLIO.",
)
def classify_entity(entity: str) -> list:
    """Classify a legal entity against the FOLIO taxonomy."""
    return [
        UserMessage(
            f"Classify this legal entity using the FOLIO ontology:\n\n"
            f'"{entity}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching entity types\n"
            f"2. Check both the actors_players branch (roles/participants) "
            f"and legal_entities branch (organization types)\n"
            f"3. Use get_concept on the best match for full details\n\n"
            f"Return the classification as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Branch (actors_players or legal_entities)\n"
            f"- Confidence (high/medium/low)\n"
            f"- Brief reasoning"
        ),
    ]


# ── Entry point ────────────────────────────────────────────────────────


def main():
    """Run the FOLIO MCP server with stdio transport."""
    parser = argparse.ArgumentParser(
        description="FOLIO Legal Ontology MCP Server",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        default=False,
        help="Use local folio-python backend instead of the public API (requires folio-mcp[local])",
    )
    parser.add_argument(
        "--api-url",
        default="https://folio.openlegalstandard.org",
        help="Base URL for the FOLIO API (default: https://folio.openlegalstandard.org)",
    )
    args = parser.parse_args()

    _config["local"] = args.local
    _config["api_url"] = args.api_url

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
