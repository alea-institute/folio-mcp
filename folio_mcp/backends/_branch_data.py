"""
Static branch metadata shared by both backends.

Maps MCP branch names to API endpoint paths and FOLIO method names.
"""

# The 24 user-facing branch names
BRANCH_NAMES = [
    "actors_players",
    "areas_of_law",
    "asset_types",
    "communication_modalities",
    "currencies",
    "data_formats",
    "document_artifacts",
    "engagement_terms",
    "events",
    "forum_venues",
    "governmental_bodies",
    "industries",
    "languages",
    "folio_types",
    "legal_authorities",
    "legal_entities",
    "locations",
    "matter_narratives",
    "matter_narrative_formats",
    "objectives",
    "services",
    "standards_compatibilities",
    "statuses",
    "system_identifiers",
]

# MCP branch name → API taxonomy endpoint path segment
BRANCH_API_PATHS = {
    "actors_players": "actor_player",
    "areas_of_law": "area_of_law",
    "asset_types": "asset_type",
    "communication_modalities": "communication_modality",
    "currencies": "currency",
    "data_formats": "data_format",
    "document_artifacts": "document_artifact",
    "engagement_terms": "engagement_terms",
    "events": "event",
    "forum_venues": "forums_venues",
    "governmental_bodies": "governmental_body",
    "industries": "industry",
    "languages": "language",
    "folio_types": "folio_type",
    "legal_authorities": "legal_authorities",
    "legal_entities": "legal_entity",
    "locations": "location",
    "matter_narratives": "matter_narrative",
    "matter_narrative_formats": "matter_narrative_format",
    "objectives": "objectives",
    "services": "service",
    "standards_compatibilities": "standards_compatibility",
    "statuses": "status",
    "system_identifiers": "system_identifiers",
}

# MCP branch name → FOLIO method name (for local backend)
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

# MCP branch name → short ID of the branch's root concept (folio-python FOLIO_TYPE_IRIS)
BRANCH_ROOT_IDS = {
    "actors_players": "R8CdMpOM0RmyrgCCvbpiLS0",
    "areas_of_law": "RSYBzf149Mi5KE0YtmpUmr",
    "asset_types": "RCIwc6WJi6IT7xePURxsi4T",
    "communication_modalities": "R8qItBwG2pRMFhUq1HQEMnb",
    "currencies": "R767niCLQVC5zIcO5WDQMSl",
    "data_formats": "R79aItNTJQwHgR002wuX3iC",
    "document_artifacts": "RDt4vQCYDfY0R9fZ5FNnTbj",
    "engagement_terms": "R9kmGZf5FSmFdouXWQ1Nndm",
    "events": "R73hoH1RXYjBTYiGfolpsAF",
    "forum_venues": "RBjHwNNG2ASVmasLFU42otk",
    "governmental_bodies": "RBQGborh1CfXanGZipDL0Qo",
    "industries": "RDIwFaFcH4KY0gwEY0QlMTp",
    "languages": "RDOvAHsvY8TKJ1O1orXPM9o",
    "folio_types": "R8uI6AZ9vSgpAdKmfGZKfTZ",
    "legal_authorities": "RC1CZydjfH8oiM4W3rCkma3",
    "legal_entities": "R7L5eLIzH0CpOUE74uJvSjL",
    "locations": "R9aSzp9cEiBCzObnP92jYFX",
    "matter_narratives": "R7ReDY2v13rer1U8AyOj55L",
    "matter_narrative_formats": "R8ONVC8pLVJC5dD4eKqCiZL",
    "objectives": "RlNFgB3TQfMzV26V4V7u4E",
    "services": "RDK1QEdQg1T8B5HQqMK2pZN",
    "standards_compatibilities": "RB4cFSLB4xvycDlKv73dOg6",
    "statuses": "Rx69EnEj3H3TpcgTfUSoYx",
    "system_identifiers": "R8EoZh39tWmXCkmP2Xzjl6E",
}

# MCP branch name → label of the branch's root concept
BRANCH_LABELS = {
    "actors_players": "Actor / Player",
    "areas_of_law": "Area of Law",
    "asset_types": "Asset Type",
    "communication_modalities": "Communication Modality",
    "currencies": "Currency",
    "data_formats": "Data Format",
    "document_artifacts": "Document / Artifact",
    "engagement_terms": "Engagement Terms",
    "events": "Event",
    "forum_venues": "Forums and Venues",
    "governmental_bodies": "Governmental Body",
    "industries": "Industry",
    "languages": "Language",
    "folio_types": "FOLIO Type",
    "legal_authorities": "Legal Authorities",
    "legal_entities": "Legal Entity",
    "locations": "Location",
    "matter_narratives": "Matter Narrative",
    "matter_narrative_formats": "Matter Narrative Format",
    "objectives": "Objectives",
    "services": "Service",
    "standards_compatibilities": "Standards Compatibility",
    "statuses": "Status",
    "system_identifiers": "System Identifiers",
}

# Extra spellings LLMs and users commonly reach for.
_BRANCH_EXTRA_ALIASES = {
    "practice_area": "areas_of_law",
    "practice_areas": "areas_of_law",
    "legal_areas": "areas_of_law",
    "document_types": "document_artifacts",
    "documents": "document_artifacts",
    "actors": "actors_players",
    "players": "actors_players",
    "roles": "actors_players",
    "forums": "forum_venues",
    "venues": "forum_venues",
    "government_bodies": "governmental_bodies",
    "assets": "asset_types",
    "jurisdictions": "locations",
    "sectors": "industries",
}

_STOP_TOKENS = {"and", "the"}


def _branch_key(text: str) -> str:
    """Normalize a branch spelling: lowercase alphanumerics, minus filler words."""
    import re

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return "".join(t for t in tokens if t not in _STOP_TOKENS)


def _build_branch_aliases() -> dict:
    aliases = {}
    for name in BRANCH_NAMES:
        for spelling in (name, BRANCH_API_PATHS[name], BRANCH_LABELS[name]):
            aliases[_branch_key(spelling)] = name
    for spelling, name in _BRANCH_EXTRA_ALIASES.items():
        aliases[_branch_key(spelling)] = name
    return aliases


_BRANCH_ALIASES = _build_branch_aliases()


def resolve_branch_name(text) -> "str | None":
    """Map any reasonable branch spelling to its canonical MCP branch name.

    Accepts the canonical name ("areas_of_law"), folio-python enum names
    ("AREA_OF_LAW"), root-concept labels ("Area of Law", "Forums and Venues"),
    and a few common aliases ("practice areas"). Returns None if unknown.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    key = _branch_key(text)
    if key in _BRANCH_ALIASES:
        return _BRANCH_ALIASES[key]
    if key.endswith("s") and key[:-1] in _BRANCH_ALIASES:
        return _BRANCH_ALIASES[key[:-1]]
    if key + "s" in _BRANCH_ALIASES:
        return _BRANCH_ALIASES[key + "s"]
    return None
