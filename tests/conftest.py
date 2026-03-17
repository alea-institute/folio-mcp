"""
Shared fixtures for folio-mcp tests.
"""

import pytest
from folio import FOLIO

from folio_mcp.backends.local import LocalBackend


@pytest.fixture(scope="module")
def folio_graph():
    """Module-scoped FOLIO fixture — loads once, reused across all tests."""
    return FOLIO()


@pytest.fixture(scope="module")
def local_backend(folio_graph):
    """Module-scoped LocalBackend fixture backed by the shared FOLIO graph."""
    return LocalBackend(folio_graph)
