"""
Backend implementations for the FOLIO MCP server.

Two interchangeable backends behind the same tool signatures:
- APIBackend: Default, uses httpx to call the public FOLIO REST API
- LocalBackend: Uses folio-python to load the full ontology in-process
"""

from folio_mcp.backends.protocol import FOLIOBackend

__all__ = ["FOLIOBackend"]
