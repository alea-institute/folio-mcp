"""
Helper functions for the FOLIO MCP server.

DEPRECATED: This module is retained for backward compatibility.
All logic has moved to folio_mcp.backends.local.
"""

# Re-export from the local backend for any external code that imported from here
from folio_mcp.backends.local import (
    format_search_results,
    owl_class_to_dict,
    owl_property_to_dict,
    resolve_iri,
)

__all__ = [
    "resolve_iri",
    "owl_class_to_dict",
    "owl_property_to_dict",
    "format_search_results",
]
