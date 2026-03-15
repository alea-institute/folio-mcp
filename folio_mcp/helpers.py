"""
Helper functions for the FOLIO MCP server.

Includes IRI resolution, compact serialization, and search result formatting.
"""

# imports
import json
from typing import List, Optional, Tuple

# packages
from folio import FOLIO, OWLClass, OWLObjectProperty


def resolve_iri(folio: FOLIO, iri: str) -> Tuple[Optional[OWLClass | OWLObjectProperty], Optional[str]]:
    """Resolve an IRI to either a class or property using multiple strategies.

    Strategy 1: Direct lookup
    Strategy 2: Extract ID from full IRI
    Strategy 3: Prepend FOLIO prefix
    Strategy 4: Suffix scan

    Args:
        folio: The FOLIO graph instance.
        iri: The IRI string to resolve.

    Returns:
        Tuple of (entity, entity_type) where entity_type is "class", "property", or None.
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
    """Compact serialization of an OWLClass.

    Args:
        cls: The OWLClass instance.

    Returns:
        A compact dictionary representation.
    """
    result = {
        "iri": cls.iri,
        "label": cls.label,
    }
    if cls.definition:
        result["definition"] = cls.definition
    if cls.alternative_labels:
        result["alternative_labels"] = cls.alternative_labels
    if cls.examples:
        result["examples"] = cls.examples
    if cls.sub_class_of:
        result["parent_iris"] = cls.sub_class_of
    if cls.parent_class_of:
        result["child_iris"] = cls.parent_class_of
    return result


def owl_property_to_dict(prop: OWLObjectProperty) -> dict:
    """Compact serialization of an OWLObjectProperty.

    Args:
        prop: The OWLObjectProperty instance.

    Returns:
        A compact dictionary representation.
    """
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
    """Format search result tuples as a JSON string.

    Args:
        results: List of (OWLClass, score) tuples from search methods.

    Returns:
        JSON-formatted string of search results.
    """
    formatted = []
    for cls, score in results:
        formatted.append({
            "iri": cls.iri,
            "label": cls.label,
            "definition": cls.definition,
            "score": score,
        })
    return json.dumps(formatted, indent=2)
