"""
Shared fixtures for folio-mcp tests.
"""

import pytest
from folio import FOLIO


@pytest.fixture(scope="module")
def folio_graph():
    """Module-scoped FOLIO fixture — loads once, reused across all tests."""
    return FOLIO()
