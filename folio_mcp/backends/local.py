"""
Local backend — loads the full FOLIO ontology in-process via folio-python.

Used when running with --local flag or when a shared FOLIO instance is provided
(e.g., when mounted inside folio-api).
"""

# imports
import json
from typing import List, Optional, Tuple

# packages
from folio import FOLIO, OWLClass, OWLObjectProperty

# project
from folio_mcp.backends._branch_data import BRANCH_METHODS, BRANCH_NAMES


def resolve_iri(folio: FOLIO, iri: str) -> Tuple[Optional[OWLClass | OWLObjectProperty], Optional[str]]:
    """Resolve an IRI to either a class or property using multiple strategies.

    Strategy 1: Direct lookup
    Strategy 2: Extract ID from full IRI
    Strategy 3: Prepend FOLIO prefix
    Strategy 4: Suffix scan
    """
    # Strategy 1: Direct lookup
    owl_class = folio[iri]
    if owl_class:
        return owl_class, "class"

    prop = folio.get_property(iri)
    if prop:
        return prop, "property"

    # Strategy 2: Extract ID from full IRI
    if iri.startswith("http"):
        parts = iri.rstrip("/").split("/")
        if parts:
            id_part = parts[-1]
            owl_class = folio[id_part]
            if owl_class:
                return owl_class, "class"
            prop = folio.get_property(id_part)
            if prop:
                return prop, "property"

    # Strategy 3: Prepend FOLIO prefix
    if not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        owl_class = folio[full_iri]
        if owl_class:
            return owl_class, "class"
        prop = folio.get_property(full_iri)
        if prop:
            return prop, "property"

    # Strategy 4: Scan all for suffix match
    for cls in folio.classes:
        if hasattr(cls, "iri") and (cls.iri.endswith(iri) or iri.endswith(cls.iri)):
            return cls, "class"
    for p in folio.object_properties:
        if p.iri.endswith(iri) or iri.endswith(p.iri):
            return p, "property"

    return None, None


def owl_class_to_dict(cls: OWLClass) -> dict:
    """Serialize an OWLClass, including all non-empty fields."""
    result: dict = {
        "iri": cls.iri,
        "label": cls.label,
    }
    if cls.definition:
        result["definition"] = cls.definition
    if cls.alternative_labels:
        result["alternative_labels"] = cls.alternative_labels
    if cls.translations:
        result["translations"] = cls.translations
    if cls.examples:
        result["examples"] = cls.examples
    if cls.sub_class_of:
        result["parent_iris"] = cls.sub_class_of
    if cls.parent_class_of:
        result["child_iris"] = cls.parent_class_of
    if cls.see_also:
        result["see_also"] = cls.see_also
    if cls.notes:
        result["notes"] = cls.notes
    if cls.comment:
        result["comment"] = cls.comment
    if cls.source:
        result["source"] = cls.source
    if cls.country:
        result["country"] = cls.country
    if cls.deprecated:
        result["deprecated"] = True
    return result


def owl_property_to_dict(prop: OWLObjectProperty) -> dict:
    """Compact serialization of an OWLObjectProperty."""
    result = {
        "iri": prop.iri,
        "label": prop.label,
    }
    if prop.definition:
        result["definition"] = prop.definition
    if prop.domain:
        result["domain"] = prop.domain
    if prop.range:
        result["range"] = prop.range
    if prop.inverse_of:
        result["inverse_of"] = prop.inverse_of
    if prop.sub_property_of:
        result["sub_property_of"] = prop.sub_property_of
    return result


def format_search_results(results: List[Tuple[OWLClass, int | float]]) -> str:
    """Format search result tuples as a JSON string."""
    formatted = []
    for cls, score in results:
        formatted.append({
            "iri": cls.iri,
            "label": cls.label,
            "definition": cls.definition,
            "score": score,
        })
    return json.dumps(formatted, indent=2)


class LocalBackend:
    """Backend that uses a local folio-python FOLIO graph instance."""

    def __init__(self, folio: Optional[FOLIO] = None):
        self._folio = folio

    @property
    def folio(self) -> FOLIO:
        if self._folio is None:
            self._folio = FOLIO()
        return self._folio

    @folio.setter
    def folio(self, value: FOLIO) -> None:
        self._folio = value

    async def search_by_label(self, query: str, limit: int) -> str:
        results = self.folio.search_by_label(query, limit=limit)
        return format_search_results(results)

    async def search_by_definition(self, query: str, limit: int) -> str:
        results = self.folio.search_by_definition(query, limit=limit)
        return format_search_results(results)

    async def get_concept(self, iri: str) -> str:
        entity, entity_type = resolve_iri(self.folio, iri)
        if entity is None:
            return json.dumps({"error": f"Concept not found: {iri}"})
        if entity_type == "class":
            return entity.to_json()
        return json.dumps(owl_property_to_dict(entity))

    async def export_concept(self, iri: str, fmt: str) -> str:
        entity, entity_type = resolve_iri(self.folio, iri)
        if entity is None:
            return json.dumps({"error": f"Concept not found: {iri}"})

        if entity_type == "property":
            return json.dumps(owl_property_to_dict(entity))

        if fmt == "markdown":
            return entity.to_markdown()
        elif fmt == "jsonld":
            return json.dumps(entity.to_jsonld(), indent=2)
        elif fmt == "owl_xml":
            return entity.to_owl_xml()
        else:
            return json.dumps({"error": f"Unsupported format: {fmt}. Use 'markdown', 'jsonld', or 'owl_xml'."})

    async def list_branches(self) -> str:
        result = {}
        for branch_name, method_name in BRANCH_METHODS.items():
            method = getattr(self.folio, method_name)
            concepts = method(max_depth=1)
            result[branch_name] = len(concepts)
        return json.dumps(result, indent=2)

    async def get_taxonomy_branch(self, branch_name: str, max_depth: int) -> str:
        if branch_name not in BRANCH_METHODS:
            return json.dumps({
                "error": f"Unknown branch: {branch_name}",
                "available_branches": BRANCH_NAMES,
            })

        method = getattr(self.folio, BRANCH_METHODS[branch_name])
        concepts = method(max_depth=max_depth)
        return json.dumps([owl_class_to_dict(c) for c in concepts], indent=2)

    async def get_children(self, iri: str, max_depth: int) -> str:
        entity, entity_type = resolve_iri(self.folio, iri)
        if entity is None:
            return json.dumps({"error": f"Concept not found: {iri}"})

        children = self.folio.get_children(entity.iri, max_depth=max_depth)
        return json.dumps([owl_class_to_dict(c) for c in children], indent=2)

    async def get_parents(self, iri: str, max_depth: int) -> str:
        entity, entity_type = resolve_iri(self.folio, iri)
        if entity is None:
            return json.dumps({"error": f"Concept not found: {iri}"})

        parents = self.folio.get_parents(entity.iri, max_depth=max_depth)
        return json.dumps([owl_class_to_dict(c) for c in parents], indent=2)

    async def get_properties(self) -> str:
        props = self.folio.get_all_properties()
        return json.dumps([owl_property_to_dict(p) for p in props], indent=2)

    async def find_connections(
        self,
        subject_iri: str,
        property_name: Optional[str],
        object_iri: Optional[str],
    ) -> str:
        entity, entity_type = resolve_iri(self.folio, subject_iri)
        if entity is None:
            return json.dumps({"error": f"Subject not found: {subject_iri}"})

        connections = self.folio.find_connections(
            subject_class=entity.iri,
            property_name=property_name,
            object_class=object_iri,
        )

        result = []
        for subj, prop, obj in connections:
            result.append({
                "subject": {"iri": subj.iri, "label": subj.label},
                "property": {"iri": prop.iri, "label": prop.label},
                "object": {"iri": obj.iri, "label": obj.label},
            })
        return json.dumps(result, indent=2)

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
        results = self.folio.query(
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
        return json.dumps([owl_class_to_dict(c) for c in results], indent=2)

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
        results = self.folio.query_properties(
            label=label,
            definition=definition,
            domain_iri=domain_iri,
            range_iri=range_iri,
            has_inverse=has_inverse,
            match_mode=match_mode,
            limit=limit,
        )
        return json.dumps([owl_property_to_dict(p) for p in results], indent=2)

    async def get_branches_resource(self) -> str:
        return await self.list_branches()

    async def get_stats_resource(self) -> str:
        folio = self.folio
        return json.dumps({
            "version": getattr(folio, "version", None),
            "title": getattr(folio, "title", None),
            "num_classes": len(folio.classes),
            "num_properties": len(folio.object_properties),
            "source": "https://openlegalstandard.org/",
            "license": "CC-BY 4.0",
        }, indent=2)
