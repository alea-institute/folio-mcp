---
name: folio-identify-objective
description: Identify the legal objectives for a matter using the FOLIO ontology's objectives taxonomy (13 top-level categories including Litigation Objectives, Transactional Objectives, Regulatory Objectives, Risk Management, Fiduciary Duty, and more). Use when the user describes a legal matter and needs to identify the strategic goals, claims, defenses, remedies, or regulatory filings involved — for matter strategy, case planning, or objective tracking.
---

# Identify Legal Objectives with FOLIO

Identify the legal objectives for a matter using the FOLIO ontology's `objectives` taxonomy branch.

## Workflow

Given a description of a legal matter, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with key legal terms from the matter to find candidate objectives in FOLIO.

2. **Browse the objectives taxonomy**: Use `folio:get_taxonomy_branch("objectives")` to review all 13 top-level objective categories (e.g., Litigation Objectives, Transactional Objectives, Regulatory Objectives, Risk Management, Fiduciary Duty, etc.).

3. **Drill into relevant categories**: Use `folio:get_children(iri)` on the most relevant categories to find specific objectives (e.g., specific claims, defenses, remedies, or filing types).

4. **Get full details**: Use `folio:get_concept(iri)` on each match for the complete definition, translations, identifiers, and cross-references.

## Output Format

Return each applicable objective as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this objective
- **Parent Category**: The top-level objective category
- **Relevance**: primary (central to the matter) or secondary (supporting or related)
- **Reasoning**: Brief explanation of why this objective applies

Most matters involve 2-5 objectives across one or more categories. List primary objectives first, then secondary ones.
