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
