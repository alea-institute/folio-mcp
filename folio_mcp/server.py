"""
MCP server for FOLIO, the Federated Open Legal Information Ontology.

Provides 12 tools, 3 resources, and 11 prompt templates for searching,
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
import anyio
import anyio.to_thread
from mcp.server.fastmcp import Context, FastMCP

# project imports
from folio_mcp import __version__
from folio_mcp.backends._branch_data import BRANCH_API_PATHS, resolve_branch_name
from folio_mcp.backends.protocol import FOLIOBackend
from folio_mcp.shaping import (
    DEFAULT_SEARCH_LIMIT,
    MAX_DEPTH,
    MAX_QUERY_LIMIT,
    MAX_SEARCH_LIMIT,
    OWL_THING,
    clamp,
    dumps,
    error,
    resolve_iri_argument,
    shape_concept,
    shape_error_passthrough,
    shape_list,
    unknown_branch,
    validate_match_mode,
    validate_query,
)

# Module-level config and backend
_config = {
    "local": False,
    "api_url": "https://folio.openlegalstandard.org",
}
# Backend set by an embedding host via set_shared_folio() (e.g. folio-api).
# The host owns it: session lifespans use it but never clear or close it.
_shared_backend: Optional[FOLIOBackend] = None

# Backend this module creates itself when nothing was injected. Under
# streamable HTTP, FastMCP enters app_lifespan once per *session*, so it is
# created by the first live session, shared by all of them, and closed only
# when the last one ends.
_owned_backend: Optional[FOLIOBackend] = None
_owned_refs = 0
_owned_lock = anyio.Lock()


def set_shared_folio(folio_instance) -> None:
    """Set a shared FOLIO instance for use by the MCP server.

    Call this before starting the server to share a FOLIO graph
    (e.g., when mounting inside folio-api to avoid double-loading).
    """
    global _shared_backend
    from folio_mcp.backends.local import LocalBackend
    _shared_backend = LocalBackend(folio_instance)


def _create_backend() -> FOLIOBackend:
    if _config["local"] or os.environ.get("FOLIO_MCP_LOCAL", "").strip() in ("1", "true", "yes"):
        from folio_mcp.backends.local import LocalBackend
        backend = LocalBackend()
        # Eagerly load the graph
        _ = backend.folio
        return backend
    from folio_mcp.backends.api import APIBackend
    return APIBackend(base_url=_config["api_url"])


def _current_backend() -> FOLIOBackend:
    """Backend for handlers without a request context (static resources).

    FastMCP treats resource handlers with any parameter (including ctx) as
    templates, so static resources like folio://branches must be zero-arg.
    """
    backend = _shared_backend or _owned_backend
    if backend is None:
        raise RuntimeError("FOLIO backend is not initialized (no active MCP session)")
    return backend


@asynccontextmanager
async def app_lifespan(server):
    """Provide the backend to one MCP session (entered once per session)."""
    global _owned_backend, _owned_refs

    if _shared_backend is not None:
        yield {"backend": _shared_backend}
        return

    async with _owned_lock:
        if _owned_backend is None:
            # Local mode loads the ontology (~10s); keep the event loop free.
            _owned_backend = await anyio.to_thread.run_sync(_create_backend)
        _owned_refs += 1
        backend = _owned_backend
    try:
        yield {"backend": backend}
    finally:
        # Shielded: a cancelled session (idle timeout, shutdown) would
        # otherwise raise at the lock acquire and never release its ref.
        with anyio.CancelScope(shield=True):
            async with _owned_lock:
                _owned_refs -= 1
                if _owned_refs == 0 and _owned_backend is backend:
                    _owned_backend = None
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
        "1. search_concepts(query) — START HERE: find concepts by name or synonym. "
        "Use short legal terms ('noncompete agreement', 'motion to dismiss'), not sentences; "
        "for a paragraph of facts, search its key terms one at a time.\n"
        "2. get_concept(iri) — full record for one concept "
        "(definition, synonyms, translations, parents/children, identifiers).\n"
        "3. list_branches() / get_taxonomy_branch(branch_name) — browse a branch by name "
        "(e.g., 'areas_of_law', 'document_artifacts').\n"
        "4. get_children(iri) / get_parents(iri) — navigate the hierarchy one level at a time.\n"
        "5. query_concepts(...) — exact filters (label/definition substring, branch, parent).\n"
        "search_definitions is a loose fallback; verify its hits by reading the definitions.\n\n"
        "IRIs look like 'https://folio.openlegalstandard.org/R07tQM...' or short IDs like 'R07tQM...'. "
        "Never invent IRIs; get them from search results. Branch names like 'areas_of_law' "
        "are accepted wherever an IRI is (they mean the branch's root concept).\n\n"
        "List results are compact {iri, label, definition} with long definitions shortened; "
        "use get_concept(iri) for the full record. Errors come back as {error, hint}.\n\n"
        "When citing a concept, give its label and IRI.\n\n"
        "Classification workflows (available as slash commands):\n"
        "- /folio:classify-document — classify a legal document against the document_artifacts taxonomy\n"
        "- /folio:identify-area-of-law — identify areas of law for a legal situation\n"
        "- /folio:classify-entity — classify a legal entity against actors_players and legal_entities\n"
        "- /folio:classify-industry — classify the industry sector for a matter or client\n"
        "- /folio:identify-legal-authority — identify the type of legal authority (statute, regulation, etc.)\n"
        "- /folio:classify-event — classify a legal event (dispute, transaction, regulatory, etc.)\n"
        "- /folio:identify-service-type — identify the type of legal service needed\n"
        "- /folio:identify-forum-venue — identify the appropriate forum, venue, or governmental body\n"
        "- /folio:identify-objective — identify legal objectives for a matter\n"
        "- /folio:classify-asset — classify an asset type (tangible, intangible, financial, estate)\n"
        "- /folio:identify-engagement-terms — identify engagement terms for a legal services arrangement\n"
        "Suggest these when users need to classify, categorize, or identify legal concepts."
    ),
    lifespan=app_lifespan,
)


def _get_backend(ctx: Context) -> FOLIOBackend:
    """Extract the backend from the MCP context."""
    return ctx.request_context.lifespan_context["backend"]


# ── Tools ──────────────────────────────────────────────────────────────

_BROWSE_TRUNCATED_HINT = (
    "Result capped. Use max_depth=1 and drill down with get_children(iri) on the "
    "relevant concept, or query_concepts(parent_iri=..., label=...) to filter."
)


@mcp.tool()
async def search_concepts(ctx: Context, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> str:
    """Find FOLIO concepts by name. START HERE for almost every question.

    Fuzzy-matches the query against concept labels and synonyms (alternative
    labels, abbreviations, translations of names). Works best with a short
    legal term or noun phrase, not a sentence: "noncompete agreement",
    "motion to dismiss", "landlord tenant", "LLC", "breach of contract".
    For a paragraph of facts, pick out the key legal terms and search each one.

    Args:
        query: A short concept name (2-6 words).
        limit: Maximum results (default 10, max 50).

    Returns:
        JSON array of {iri, label, definition, score}; score is 0-100, higher is
        better. Pass an iri to get_concept for the full record.
    """
    invalid = validate_query(query, "search_concepts")
    if invalid:
        return invalid
    limit = clamp(limit, 1, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT)
    raw = await _get_backend(ctx).search_by_label(query.strip(), limit)
    return shape_list(raw, limit=limit)


@mcp.tool()
async def search_definitions(ctx: Context, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> str:
    """Fuzzy search over concept DEFINITIONS. Fallback only — use search_concepts first.

    Ranking is loose: results often share only a few common words with the
    query, so read each definition before relying on a hit. For an exact word
    or phrase inside definitions, query_concepts(definition="...") is more
    precise.

    Args:
        query: A short descriptive phrase (e.g. "duty of loyalty to beneficiaries").
        limit: Maximum results (default 10, max 50).

    Returns:
        JSON array of {iri, label, definition, score}.
    """
    invalid = validate_query(query, "search_definitions")
    if invalid:
        return invalid
    limit = clamp(limit, 1, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT)
    raw = await _get_backend(ctx).search_by_definition(query.strip(), limit)
    return shape_list(raw, limit=limit)


@mcp.tool()
async def get_concept(ctx: Context, iri: str) -> str:
    """Get the full record for one FOLIO concept: definition, synonyms,
    translations, examples, parent/child IRIs, identifiers and cross-references.

    Args:
        iri: A full IRI ("https://folio.openlegalstandard.org/RSYBzf149Mi5KE0YtmpUmr"),
            a short ID ("RSYBzf149Mi5KE0YtmpUmr"), or a branch name such as
            "areas_of_law" (returns that branch's root concept). Not a free-text
            name — use search_concepts to find the IRI first.

    Returns:
        JSON object with all non-empty fields, or {error, hint}.
    """
    resolved, invalid = resolve_iri_argument(iri)
    if invalid:
        return invalid
    return shape_concept(await _get_backend(ctx).get_concept(resolved), iri)


@mcp.tool()
async def export_concept(ctx: Context, iri: str, format: str = "markdown") -> str:
    """Export one FOLIO concept as Markdown, JSON-LD or OWL/XML (for documents or
    other systems). For reading a concept yourself, get_concept is more compact.

    Args:
        iri: The concept IRI or short ID.
        format: "markdown" (default), "jsonld", or "owl_xml".

    Returns:
        The concept in the requested format, or {error, hint}.
    """
    resolved, invalid = resolve_iri_argument(iri)
    if invalid:
        return invalid
    return shape_error_passthrough(await _get_backend(ctx).export_concept(resolved, format), iri)


@mcp.tool()
async def list_branches(ctx: Context) -> str:
    """List the 24 top-level FOLIO taxonomy branches with their number of
    top-level concepts (e.g. areas_of_law, document_artifacts, legal_entities,
    actors_players, industries, locations).

    Returns:
        JSON object mapping branch name to top-level concept count.
    """
    return shape_list(await _get_backend(ctx).list_branches())


@mcp.tool()
async def get_taxonomy_branch(ctx: Context, branch_name: str, max_depth: int = 1) -> str:
    """Browse the top-level concepts of a FOLIO taxonomy branch.

    Args:
        branch_name: A branch name from list_branches(), e.g. "areas_of_law",
            "document_artifacts", "actors_players". Close variants such as
            "Areas of Law" or "AREA_OF_LAW" are accepted.
        max_depth: 1 (default) = top level only. Up to 3, but deeper levels can be
            large; prefer get_children(iri) on the relevant concept.

    Returns:
        JSON array of {iri, label, definition} (definitions shortened; use
        get_concept for full text). Large results are capped at 100 items and
        returned as {results, truncated, total, note}.
    """
    canonical = resolve_branch_name(branch_name)
    if canonical is None:
        return unknown_branch(branch_name)
    max_depth = clamp(max_depth, 1, MAX_DEPTH, 1)
    raw = await _get_backend(ctx).get_taxonomy_branch(canonical, max_depth)
    return shape_list(raw, truncated_hint=_BROWSE_TRUNCATED_HINT)


@mcp.tool()
async def get_children(ctx: Context, iri: str, max_depth: int = 1) -> str:
    """Get the narrower (child) concepts of a FOLIO concept.

    Args:
        iri: A concept IRI or short ID. A branch name such as "areas_of_law" is
            also accepted and returns that branch's top-level concepts.
        max_depth: 1 (default) = direct children. Up to 3; prefer drilling down
            one level at a time.

    Returns:
        JSON array of {iri, label, definition}; capped at 100 items as
        {results, truncated, total, note}.
    """
    resolved, invalid = resolve_iri_argument(iri)
    if invalid:
        return invalid
    max_depth = clamp(max_depth, 1, MAX_DEPTH, 1)
    raw = await _get_backend(ctx).get_children(resolved, max_depth)
    return shape_list(raw, iri=iri, exclude_iris=(resolved,), truncated_hint=_BROWSE_TRUNCATED_HINT)


@mcp.tool()
async def get_parents(ctx: Context, iri: str, max_depth: int = 1) -> str:
    """Get the broader (parent) concepts of a FOLIO concept. A concept can have
    several parents (FOLIO is a polyhierarchy).

    Args:
        iri: A concept IRI or short ID.
        max_depth: 1 (default) = direct parents; up to 3 for grandparents etc.

    Returns:
        JSON array of {iri, label, definition}. Empty for a branch root.
    """
    resolved, invalid = resolve_iri_argument(iri)
    if invalid:
        return invalid
    max_depth = clamp(max_depth, 1, MAX_DEPTH, 1)
    raw = await _get_backend(ctx).get_parents(resolved, max_depth)
    return shape_list(raw, iri=iri, exclude_iris=(resolved, OWL_THING), truncated_hint=_BROWSE_TRUNCATED_HINT)


@mcp.tool()
async def get_properties(ctx: Context) -> str:
    """List all FOLIO object properties (relationship types such as
    "folio:advised", "folio:drafted", "folio:isGovernedBy", "oasis:hasActor").

    Compact listing: iri, label and short definition only. For domain/range
    details, or to filter, use query_properties.

    Returns:
        JSON array of {iri, label, definition}.
    """
    raw = await _get_backend(ctx).get_properties()
    data = json.loads(raw) if raw.lstrip().startswith("[") else None
    if isinstance(data, list):
        raw = json.dumps([
            {k: p.get(k) for k in ("iri", "label", "definition")}
            for p in data
            if not str(p.get("label", "")).startswith("DEPRECATED")
        ])
    return shape_list(raw, max_items=1000, max_definition_chars=100)


@mcp.tool()
async def find_connections(
    ctx: Context,
    subject_iri: str,
    property_name: Optional[str] = None,
    object_iri: Optional[str] = None,
) -> str:
    """Find explicit property links (subject -> property -> object triples) from
    a FOLIO concept, e.g. Actor / Player -folio:drafted-> Document / Artifact.

    FOLIO records only a small number of these links (mostly on top-level
    classes), so most concepts have none. For broader/narrower relationships use
    get_parents/get_children; for related concepts see "see_also" in get_concept.

    Args:
        subject_iri: IRI or short ID of the subject concept (branch names accepted).
        property_name: Optional property label (e.g. "folio:drafted") or IRI.
        object_iri: Optional object concept IRI to filter by.

    Returns:
        JSON array of {subject, property, object} (each {iri, label}), or
        {results: [], note} when the concept has no recorded links.
    """
    resolved, invalid = resolve_iri_argument(subject_iri)
    if invalid:
        return invalid
    if object_iri:
        object_iri, invalid = resolve_iri_argument(object_iri)
        if invalid:
            return invalid
    raw = await _get_backend(ctx).find_connections(resolved, property_name or None, object_iri or None)
    return shape_list(
        raw,
        iri=subject_iri,
        empty_note=(
            "No explicit property links are recorded for this concept (common in FOLIO). "
            "Use get_parents/get_children for the hierarchy, or get_concept for see_also."
        ),
    )


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
    """Filter FOLIO concepts by exact field matches and structure (not ranked).

    Use this for precise filters, e.g. every area of law whose label contains
    "tax", or concepts whose definition mentions "fiduciary". For "find the
    concept called X", search_concepts ranks better. All filters are ANDed;
    give at least one.

    Text filters:
        label: Match the primary label.
        definition: Match the definition text.
        alt_label: Match alternative labels / synonyms.
        example: Match examples.
        any_text: Match any text field (label, definition, synonyms, examples, notes).

    Structural filters:
        branch: Branch name from list_branches(), e.g. "areas_of_law" (also
            accepts "AREA_OF_LAW").
        parent_iri: Only descendants of this concept (IRI, short ID or branch name).
        has_children: True = non-leaf concepts only, False = leaf concepts only.
        deprecated: Include deprecated concepts (default False).
        country: Match the country field.

    Control:
        match_mode: "substring" (default, case-insensitive), "exact", "regex", or "fuzzy".
        limit: Maximum results (default 20, max 100).

    Returns:
        JSON array of {iri, label, definition}.
    """
    text_filters = (label, definition, alt_label, example, any_text, country)
    if all(f is None or f == "" for f in text_filters) and not branch and not parent_iri:
        return error(
            "Give at least one filter (label, definition, any_text, branch, parent_iri, ...).",
            hint="To find a concept by name, use search_concepts(query=...).",
        )
    invalid = validate_match_mode(match_mode, text_filters)
    if invalid:
        return invalid
    folio_branch = None
    if branch:
        canonical = resolve_branch_name(branch)
        if canonical is None:
            return unknown_branch(branch)
        folio_branch = BRANCH_API_PATHS[canonical].upper()
    if parent_iri:
        parent_iri, invalid = resolve_iri_argument(parent_iri)
        if invalid:
            return invalid
    limit = clamp(limit, 1, MAX_QUERY_LIMIT, 20)
    raw = await _get_backend(ctx).query_concepts(
        label=label or None,
        definition=definition or None,
        alt_label=alt_label or None,
        example=example or None,
        any_text=any_text or None,
        branch=folio_branch,
        parent_iri=parent_iri,
        has_children=has_children,
        deprecated=deprecated,
        country=country or None,
        match_mode=match_mode,
        limit=limit,
    )
    return shape_list(raw, limit=limit, iri=parent_iri)


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
    """Filter FOLIO object properties (relationship types), with full domain/range detail.

    Text filters:
        label: Match the property label, e.g. "advised", "drafted", "governed", "hasActor".
        definition: Match the property definition.

    Structural filters:
        domain_iri: Only properties whose domain includes this class IRI.
        range_iri: Only properties whose range includes this class IRI.
        has_inverse: True = only properties with inverses, False = only without.

    Control:
        match_mode: "substring" (default), "exact", "regex", or "fuzzy".
        limit: Maximum results (default 20, max 100).

    Returns:
        JSON array of {iri, label, definition, domain, range, inverse_of, sub_property_of}.
    """
    invalid = validate_match_mode(match_mode, (label, definition))
    if invalid:
        return invalid
    for name, value in (("domain_iri", domain_iri), ("range_iri", range_iri)):
        if value:
            resolved, invalid = resolve_iri_argument(value)
            if invalid:
                return invalid
            if name == "domain_iri":
                domain_iri = resolved
            else:
                range_iri = resolved
    limit = clamp(limit, 1, MAX_QUERY_LIMIT, 20)
    raw = await _get_backend(ctx).query_properties(
        label=label or None,
        definition=definition or None,
        domain_iri=domain_iri or None,
        range_iri=range_iri or None,
        has_inverse=has_inverse,
        match_mode=match_mode,
        limit=limit,
    )
    return shape_list(raw, limit=limit)


# Pasted documents can be long; cap the work one call can trigger.
MAX_EXTRACT_CHARS = 100_000
MAX_EXTRACT_LIMIT = 200


@mcp.tool()
async def extract_concepts(ctx: Context, text: str, limit: int = 50, branch: Optional[str] = None) -> str:
    """Tag a passage of text with the FOLIO concepts it mentions.

    Paste a fact pattern, clause, email, or brief excerpt; returns every FOLIO
    concept whose label or synonym appears in it (e.g., "tenant", "eviction",
    "temporary restraining order", "Bankruptcy Court", "EEOC"), with its
    branch. Dictionary matching, not inference: use it as a fast first pass,
    then get_concept(iri) or the classification prompts for judgment calls.
    The first call builds the label index (about 2s).

    Args:
        text: The text to tag (up to 100,000 characters).
        limit: Maximum concepts to return, in order of first mention (default 50).
        branch: Optional branch filter, e.g. "areas_of_law", "document_artifacts",
            "actors_players", "forum_venues" (see list_branches).

    Returns:
        JSON {"count", "concepts": [{iri, label, branch, match_type,
        matched_text, count, first_offset}]}.
    """
    if not isinstance(text, str) or not text.strip():
        return error("text must not be empty.", hint="Paste the passage to tag with FOLIO concepts.")
    canonical = None
    if branch is not None and str(branch).strip():
        canonical = resolve_branch_name(branch)
        if canonical is None:
            return unknown_branch(branch)
    if len(text) > MAX_EXTRACT_CHARS:
        return error(
            f"Text is {len(text)} characters; the limit is {MAX_EXTRACT_CHARS}.",
            hint="Split the document and call extract_concepts on each part.",
        )
    limit = clamp(limit, 1, MAX_EXTRACT_LIMIT, 50)
    return await _get_backend(ctx).extract_concepts(text, limit, canonical)


def _register_citation_tool() -> None:
    """Register extract_citations only when the optional kaos extra is installed."""
    from folio_mcp.citations import citations_available, extract_citations as _extract

    if not citations_available():
        return

    @mcp.tool()
    async def extract_citations(text: str, limit: int = 100) -> str:
        """Find legal citations in text and map each to FOLIO concepts.

        Recognizes case law, U.S.C. and state statutes, C.F.R., Federal Register,
        federal rules (FRCP, FRE, ...), constitutions, executive orders,
        public laws, restatements, sentencing guidelines and more. Each citation
        gets its FOLIO legal authority type (e.g., "U.S. Code", "Federal Rules
        of Civil Procedure", "Caselaw and Common Law") and, for federal
        appellate and Supreme Court cases, the FOLIO court (forum) concept.

        Args:
            text: Text containing citations (up to 100,000 characters).
            limit: Maximum citations to return (default 100).

        Returns:
            JSON {"count", "citations": [{text, kind, start, end, case_name?,
            folio_authority?: {iri, label}, folio_forum?: {iri, label}}]}.
        """
        if not isinstance(text, str) or not text.strip():
            return error("text must not be empty.", hint="Paste the passage containing citations.")
        if len(text) > MAX_EXTRACT_CHARS:
            return error(
                f"Text is {len(text)} characters; the limit is {MAX_EXTRACT_CHARS}.",
                hint="Split the document and call extract_citations on each part.",
            )
        capped = clamp(limit, 1, MAX_EXTRACT_LIMIT, 100)
        result = await anyio.to_thread.run_sync(lambda: _extract(text, capped))
        return dumps(result)


_register_citation_tool()


@mcp.tool()
async def search_expanded(
    ctx: Context,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    include_definitions: bool = False,
) -> str:
    """Search FOLIO with a plain-English question or fact pattern.

    An LLM rewrites the query into synonyms and legal terms of art (e.g.
    "my landlord won't fix the heat" -> "Implied Warranty of Habitability",
    "Constructive Eviction"), searches each, and merges the results by rank.
    Use this for natural-language or situational queries; use search_concepts
    when you already know the concept's name. The first call for a query takes
    a few seconds; repeats are cached. If the LLM is unavailable it returns
    plain label-search results with an empty expansions list.

    Args:
        query: Natural-language description (e.g., "fired for reporting safety violations").
        limit: Maximum results (default 10, max 50).
        include_definitions: Also match concept definitions (default false).

    Returns:
        JSON object: query, expansions, expansion_source ("llm", "cache" or "none"),
        and results [{iri, label, definition, score, matched_via}].
    """
    invalid = validate_query(query, "search_expanded")
    if invalid:
        return invalid
    limit = clamp(limit, 1, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT)
    return await _get_backend(ctx).search_expanded(
        query.strip(), limit, bool(include_definitions)
    )

# ── Resources ──────────────────────────────────────────────────────────


@mcp.resource("folio://branches")
async def branches_resource() -> str:
    """FOLIO taxonomy branch names with concept counts."""
    return shape_list(await _current_backend().get_branches_resource())


@mcp.resource("folio://stats")
async def stats_resource() -> str:
    """FOLIO ontology statistics."""
    return await _current_backend().get_stats_resource()


@mcp.resource(
    "folio://branch/{branch_name}",
    description="Top-level concepts in a FOLIO taxonomy branch. "
    "Use folio://branches to see available branch names.",
)
async def branch_resource(branch_name: str) -> str:
    """Get top-level concepts for a specific FOLIO taxonomy branch."""
    canonical = resolve_branch_name(branch_name)
    if canonical is None:
        return unknown_branch(branch_name)
    return shape_list(await _current_backend().get_taxonomy_branch(canonical, max_depth=1))


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
            f"get_taxonomy_branch to see the top-level document categories\n"
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


@mcp.prompt(
    name="classify-industry",
    description="Classify the industry for a legal matter, client, or company "
    "using the FOLIO ontology's industries taxonomy (21 sectors).",
)
def classify_industry(description: str) -> list:
    """Classify a matter or client by industry sector."""
    return [
        UserMessage(
            f"Classify the industry for this matter or client "
            f"using the FOLIO ontology:\n\n"
            f'"{description}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching industry types\n"
            f"2. Browse the industries branch with get_taxonomy_branch "
            f"to review all 21 top-level industry sectors\n"
            f"3. Use get_children on the best sector to find sub-industries\n"
            f"4. Use get_concept on the best match for full details\n\n"
            f"Return the classification as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Parent sector (if sub-industry)\n"
            f"- Confidence (high/medium/low)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="identify-legal-authority",
    description="Identify the type of legal authority (statute, regulation, case law, "
    "treaty, executive order, etc.) using the FOLIO ontology's legal_authorities taxonomy.",
)
def identify_legal_authority(authority: str) -> list:
    """Identify the type of a legal authority or source of law."""
    return [
        UserMessage(
            f"Identify the type of legal authority using the FOLIO ontology:\n\n"
            f'"{authority}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching authority types\n"
            f"2. Browse the legal_authorities branch with get_taxonomy_branch "
            f"to review all 14 top-level authority types\n"
            f"3. Use get_children on the best category to find specific subtypes\n"
            f"4. Use get_concept on the best match for full details\n\n"
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
    name="classify-event",
    description="Classify a legal event (dispute, transaction, regulatory action, "
    "bankruptcy filing, employment action, etc.) using the FOLIO ontology's events taxonomy.",
)
def classify_event(event: str) -> list:
    """Classify a legal event against the FOLIO events taxonomy."""
    return [
        UserMessage(
            f"Classify this legal event using the FOLIO ontology:\n\n"
            f'"{event}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching event types\n"
            f"2. Browse the events branch with get_taxonomy_branch "
            f"to review all 14 top-level event categories\n"
            f"3. Use get_children on the best category to find the specific event type\n"
            f"4. Use get_concept on the best match for full details\n\n"
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
    name="identify-service-type",
    description="Identify the type of legal service needed for a matter — advisory, "
    "transactional, dispute, regulatory, or bankruptcy/restructuring.",
)
def identify_service_type(matter: str) -> list:
    """Identify the legal service type for a matter."""
    return [
        UserMessage(
            f"Identify the type of legal service needed for this matter "
            f"using the FOLIO ontology:\n\n"
            f'"{matter}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching service types\n"
            f"2. Browse the services branch with get_taxonomy_branch "
            f"to review all 5 top-level service categories "
            f"(Advisory, Transactional, Dispute, Regulatory, Bankruptcy/Restructuring)\n"
            f"3. Use get_children on the best match to find specific service subtypes\n"
            f"4. Use get_concept on the best match for full details\n\n"
            f"Return each applicable service type as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Relevance (primary/secondary)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="identify-forum-venue",
    description="Identify the appropriate forum, venue, or governmental body for a "
    "legal dispute or regulatory matter using the FOLIO ontology.",
)
def identify_forum_venue(matter: str) -> list:
    """Identify the forum, venue, or governmental body for a matter."""
    return [
        UserMessage(
            f"Identify the appropriate forum, venue, or governmental body "
            f"for this matter using the FOLIO ontology:\n\n"
            f'"{matter}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching forums, venues, or bodies\n"
            f"2. Browse the forum_venues branch with get_taxonomy_branch "
            f"to see dispute forums, stock exchanges, and dispute venues\n"
            f"3. Also browse the governmental_bodies branch with get_taxonomy_branch "
            f"to see federal, state, local, regulatory, and multinational bodies\n"
            f"4. Use get_children on the best matches to find specific subtypes\n"
            f"5. Use get_concept on each match for full details\n\n"
            f"Return each applicable forum or body as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Branch (forum_venues or governmental_bodies)\n"
            f"- Relevance (primary/secondary)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="identify-objective",
    description="Identify the legal objectives for a matter — litigation claims/defenses, "
    "transactional goals, regulatory filings, risk management, etc.",
)
def identify_objective(matter: str) -> list:
    """Identify legal objectives for a matter."""
    return [
        UserMessage(
            f"Identify the legal objectives for this matter "
            f"using the FOLIO ontology:\n\n"
            f'"{matter}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching legal objectives\n"
            f"2. Browse the objectives branch with get_taxonomy_branch "
            f"to review all 13 top-level objective categories\n"
            f"3. Use get_children on the most relevant categories "
            f"to find specific objectives\n"
            f"4. Use get_concept on each match for full details\n\n"
            f"Return each applicable objective as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Parent category\n"
            f"- Relevance (primary/secondary)\n"
            f"- Brief reasoning"
        ),
    ]


@mcp.prompt(
    name="classify-asset",
    description="Classify an asset as tangible, intangible, financial, or estate "
    "using the FOLIO ontology's asset_types taxonomy.",
)
def classify_asset(asset: str) -> list:
    """Classify an asset against the FOLIO asset types taxonomy."""
    return [
        UserMessage(
            f"Classify this asset using the FOLIO ontology:\n\n"
            f'"{asset}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching asset types\n"
            f"2. Browse the asset_types branch with get_taxonomy_branch "
            f"to see the 4 top-level categories "
            f"(Tangible Assets, Intangible Assets, Financial Assets, Estate)\n"
            f"3. Use get_children on the best category to find the specific asset type\n"
            f"4. Use get_concept on the best match for full details\n\n"
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
    name="identify-engagement-terms",
    description="Identify the engagement terms for a legal services arrangement — "
    "fee model, invoice terms, engagement type, and billing details.",
)
def identify_engagement_terms(arrangement: str) -> list:
    """Identify engagement terms for a legal services arrangement."""
    return [
        UserMessage(
            f"Identify the engagement terms for this legal services arrangement "
            f"using the FOLIO ontology:\n\n"
            f'"{arrangement}"\n\n'
            f"Steps:\n"
            f"1. Use search_concepts to find matching engagement terms\n"
            f"2. Browse the engagement_terms branch with get_taxonomy_branch "
            f"to review all 14 top-level categories "
            f"(fee models, invoice terms, engagement arrangements, etc.)\n"
            f"3. Use get_children on the most relevant categories "
            f"to find specific terms\n"
            f"4. Use get_concept on each match for full details\n\n"
            f"Return each applicable term as:\n"
            f"- FOLIO Label\n"
            f"- FOLIO IRI\n"
            f"- Definition\n"
            f"- Parent category\n"
            f"- Relevance (primary/secondary)\n"
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
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
