---
name: folio-identify-area-of-law
description: Identify areas of law applicable to a legal situation using the FOLIO ontology's areas_of_law taxonomy (31 top-level areas, hundreds of sub-specialties). Use when the user describes a legal situation, dispute, matter, or scenario and needs to know which area(s) of law apply. Also use when classifying legal matters by practice area, mapping cases to legal disciplines, or determining which legal specialization is relevant — tort law, contract law, criminal law, intellectual property, etc.
---

# Identify Areas of Law with FOLIO

Identify the area(s) of law that apply to a legal situation using the FOLIO ontology's `areas_of_law` taxonomy branch.

## Workflow

Given a description of a legal situation or matter, follow these steps:

1. **Search for relevant areas**: Use `folio:search_concepts` with key legal terms from the situation to find candidate areas of law.

2. **Browse all areas of law**: Use `folio:get_taxonomy_branch("areas_of_law")` to review all 31 top-level areas of law. This ensures you do not miss a relevant area that the search might not surface.

3. **Check sub-specialties**: Use `folio:get_children(iri)` on promising top-level areas to see if a more specific sub-specialty applies.

4. **Get full details**: Use `folio:get_concept(iri)` on each matching area for the complete definition, translations, and cross-references.

## Output Format

Return each applicable area of law as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this area of law
- **Relevance**: primary (directly applicable) or secondary (tangentially related)
- **Reasoning**: Brief explanation of why this area applies to the situation

List primary areas first, then secondary areas. Most situations involve 1-3 primary areas and 0-2 secondary areas.
