"""
Protocol defining the contract for FOLIO MCP backends.

All methods are async and return JSON strings.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class FOLIOBackend(Protocol):
    """Protocol for FOLIO MCP backends.

    Both API and local backends implement this interface.
    All methods return JSON strings ready to be returned from MCP tools.
    """

    async def search_by_label(self, query: str, limit: int) -> str: ...

    async def search_by_definition(self, query: str, limit: int) -> str: ...

    async def get_concept(self, iri: str) -> str: ...

    async def export_concept(self, iri: str, fmt: str) -> str: ...

    async def list_branches(self) -> str: ...

    async def get_taxonomy_branch(self, branch_name: str, max_depth: int) -> str: ...

    async def get_children(self, iri: str, max_depth: int) -> str: ...

    async def get_parents(self, iri: str, max_depth: int) -> str: ...

    async def get_properties(self) -> str: ...

    async def find_connections(
        self,
        subject_iri: str,
        property_name: Optional[str],
        object_iri: Optional[str],
    ) -> str: ...

    async def query_concepts(
        self,
        label: Optional[str],
        definition: Optional[str],
        alt_label: Optional[str],
        example: Optional[str],
        any_text: Optional[str],
        branch: Optional[str],
        parent_iri: Optional[str],
        has_children: Optional[bool],
        deprecated: bool,
        country: Optional[str],
        match_mode: str,
        limit: int,
    ) -> str: ...

    async def query_properties(
        self,
        label: Optional[str],
        definition: Optional[str],
        domain_iri: Optional[str],
        range_iri: Optional[str],
        has_inverse: Optional[bool],
        match_mode: str,
        limit: int,
    ) -> str: ...

    async def get_branches_resource(self) -> str: ...

    async def get_stats_resource(self) -> str: ...
