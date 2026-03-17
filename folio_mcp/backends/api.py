"""
API backend — thin httpx client that calls the public FOLIO REST API.

Default backend for instant startup with no local ontology loading.
"""

# imports
import json
from typing import Optional

# packages
import httpx

# project
from folio_mcp.backends._branch_data import BRANCH_API_PATHS, BRANCH_NAMES


def _summary_class(d: dict) -> dict:
    """Compact summary for browse/list — iri, label, definition only."""
    result = {"iri": d.get("iri", ""), "label": d.get("label", "")}
    if d.get("definition"):
        result["definition"] = d["definition"]
    return result


def _compact_class(d: dict) -> dict:
    """Full serialization — all non-empty fields."""
    result = {"iri": d.get("iri", ""), "label": d.get("label", "")}
    if d.get("definition"):
        result["definition"] = d["definition"]
    if d.get("alternative_labels"):
        result["alternative_labels"] = d["alternative_labels"]
    if d.get("translations"):
        result["translations"] = d["translations"]
    if d.get("examples"):
        result["examples"] = d["examples"]
    if d.get("sub_class_of"):
        result["parent_iris"] = d["sub_class_of"]
    if d.get("parent_class_of"):
        result["child_iris"] = d["parent_class_of"]
    if d.get("preferred_label") and d.get("preferred_label") != d.get("label"):
        result["preferred_label"] = d["preferred_label"]
    if d.get("identifier"):
        result["identifier"] = d["identifier"]
    if d.get("hidden_label"):
        result["hidden_label"] = d["hidden_label"]
    if d.get("see_also"):
        result["see_also"] = d["see_also"]
    if d.get("is_defined_by"):
        result["is_defined_by"] = d["is_defined_by"]
    if d.get("notes"):
        result["notes"] = d["notes"]
    if d.get("comment"):
        result["comment"] = d["comment"]
    if d.get("source"):
        result["source"] = d["source"]
    if d.get("country"):
        result["country"] = d["country"]
    if d.get("deprecated"):
        result["deprecated"] = True
    return result


def _compact_property(d: dict) -> dict:
    """Compact an API response property dict."""
    result = {"iri": d.get("iri", ""), "label": d.get("label", "")}
    if d.get("definition"):
        result["definition"] = d["definition"]
    if d.get("domain"):
        result["domain"] = d["domain"]
    if d.get("range"):
        result["range"] = d["range"]
    if d.get("inverse_of"):
        result["inverse_of"] = d["inverse_of"]
    if d.get("sub_property_of"):
        result["sub_property_of"] = d["sub_property_of"]
    return result


def _extract_iri_id(iri: str) -> str:
    """Extract the ID portion from a full FOLIO IRI, or return as-is."""
    if iri.startswith("https://folio.openlegalstandard.org/"):
        return iri.replace("https://folio.openlegalstandard.org/", "", 1)
    if iri.startswith("http"):
        parts = iri.rstrip("/").split("/")
        return parts[-1] if parts else iri
    return iri


class APIBackend:
    """Backend that calls the public FOLIO REST API via httpx."""

    def __init__(self, base_url: str = "https://folio.openlegalstandard.org"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, **params) -> httpx.Response:
        """Make a GET request, returning the response."""
        client = await self._get_client()
        try:
            resp = await client.get(path, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            raise e
        except httpx.HTTPError as e:
            raise e

    async def search_by_label(self, query: str, limit: int) -> str:
        try:
            resp = await self._get("/search/label", query=query, limit=limit)
            data = resp.json()
            results = data.get("results", [])
            formatted = []
            for item in results:
                if isinstance(item, list) and len(item) == 2:
                    cls_data, score = item
                    formatted.append({
                        "iri": cls_data.get("iri", ""),
                        "label": cls_data.get("label", ""),
                        "definition": cls_data.get("definition"),
                        "score": score,
                    })
            return json.dumps(formatted, indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def search_by_definition(self, query: str, limit: int) -> str:
        try:
            resp = await self._get("/search/definition", query=query, limit=limit)
            data = resp.json()
            results = data.get("results", [])
            formatted = []
            for item in results:
                if isinstance(item, list) and len(item) == 2:
                    cls_data, score = item
                    formatted.append({
                        "iri": cls_data.get("iri", ""),
                        "label": cls_data.get("label", ""),
                        "definition": cls_data.get("definition"),
                        "score": score,
                    })
            return json.dumps(formatted, indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_concept(self, iri: str) -> str:
        iri_id = _extract_iri_id(iri)
        try:
            resp = await self._get(f"/{iri_id}")
            return resp.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps({"error": f"Concept not found: {iri}"})
            return json.dumps({"error": f"API error: {e.response.status_code}"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def export_concept(self, iri: str, fmt: str) -> str:
        iri_id = _extract_iri_id(iri)
        fmt_map = {
            "markdown": "markdown",
            "jsonld": "jsonld",
            "owl_xml": "xml",
        }
        path_suffix = fmt_map.get(fmt)
        if path_suffix is None:
            return json.dumps({"error": f"Unsupported format: {fmt}. Use 'markdown', 'jsonld', or 'owl_xml'."})

        try:
            resp = await self._get(f"/{iri_id}/{path_suffix}")
            return resp.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps({"error": f"Concept not found: {iri}"})
            return json.dumps({"error": f"API error: {e.response.status_code}"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def list_branches(self) -> str:
        try:
            resp = await self._get("/taxonomy/branches")
            return resp.text
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_taxonomy_branch(self, branch_name: str, max_depth: int) -> str:
        if branch_name not in BRANCH_API_PATHS:
            return json.dumps({
                "error": f"Unknown branch: {branch_name}",
                "available_branches": BRANCH_NAMES,
            })

        api_path = BRANCH_API_PATHS[branch_name]
        try:
            resp = await self._get(f"/taxonomy/{api_path}", max_depth=max_depth)
            data = resp.json()
            classes = data.get("classes", [])
            return json.dumps([_summary_class(c) for c in classes], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_children(self, iri: str, max_depth: int) -> str:
        iri_id = _extract_iri_id(iri)
        try:
            resp = await self._get(f"/taxonomy/tree/node/{iri_id}")
            data = resp.json()
            children = data.get("children", [])
            return json.dumps([_summary_class(c) for c in children], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_parents(self, iri: str, max_depth: int) -> str:
        iri_id = _extract_iri_id(iri)
        try:
            resp = await self._get(f"/taxonomy/tree/node/{iri_id}")
            data = resp.json()
            parents = data.get("parents", [])
            return json.dumps([_summary_class(c) for c in parents], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_properties(self) -> str:
        try:
            resp = await self._get("/properties/all")
            data = resp.json()
            props = data.get("properties", [])
            return json.dumps([_compact_property(p) for p in props], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def find_connections(
        self,
        subject_iri: str,
        property_name: Optional[str],
        object_iri: Optional[str],
    ) -> str:
        params = {"subject": subject_iri}
        if property_name:
            params["property"] = property_name
        if object_iri:
            params["object"] = object_iri
        try:
            resp = await self._get("/connections", **params)
            return resp.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps({"error": f"Subject not found: {subject_iri}"})
            return json.dumps({"error": f"API error: {e.response.status_code}"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

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
    ) -> str:
        params = {}
        if label is not None:
            params["label"] = label
        if definition is not None:
            params["definition"] = definition
        if alt_label is not None:
            params["alt_label"] = alt_label
        if example is not None:
            params["example"] = example
        if any_text is not None:
            params["any_text"] = any_text
        if branch is not None:
            params["branch"] = branch
        if parent_iri is not None:
            params["parent_iri"] = parent_iri
        if has_children is not None:
            params["has_children"] = has_children
        if deprecated:
            params["deprecated"] = True
        if country is not None:
            params["country"] = country
        params["match_mode"] = match_mode
        params["limit"] = limit
        try:
            resp = await self._get("/search/query", **params)
            data = resp.json()
            classes = data.get("classes", [])
            return json.dumps([_summary_class(c) for c in classes], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def query_properties(
        self,
        label: Optional[str],
        definition: Optional[str],
        domain_iri: Optional[str],
        range_iri: Optional[str],
        has_inverse: Optional[bool],
        match_mode: str,
        limit: int,
    ) -> str:
        params = {}
        if label is not None:
            params["label"] = label
        if definition is not None:
            params["definition"] = definition
        if domain_iri is not None:
            params["domain_iri"] = domain_iri
        if range_iri is not None:
            params["range_iri"] = range_iri
        if has_inverse is not None:
            params["has_inverse"] = has_inverse
        params["match_mode"] = match_mode
        params["limit"] = limit
        try:
            resp = await self._get("/search/query_properties", **params)
            data = resp.json()
            props = data.get("properties", [])
            return json.dumps([_compact_property(p) for p in props], indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})

    async def get_branches_resource(self) -> str:
        return await self.list_branches()

    async def get_stats_resource(self) -> str:
        try:
            resp = await self._get("/info/health")
            data = resp.json()
            graph = data.get("folio_graph", {})
            return json.dumps({
                "version": None,
                "title": graph.get("title"),
                "num_classes": graph.get("num_classes"),
                "num_properties": graph.get("num_properties"),
                "source": "https://openlegalstandard.org/",
                "license": "CC-BY 4.0",
            }, indent=2)
        except httpx.HTTPError as e:
            return json.dumps({"error": f"API error: {e}"})
