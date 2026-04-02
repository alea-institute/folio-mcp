---
name: folio-identify-engagement-terms
description: Identify the engagement terms for a legal services arrangement using the FOLIO ontology's engagement_terms taxonomy (14 top-level categories including Fee Models, Invoice Terms, Engagement Arrangements, Source of Business, and more). Use when the user describes a billing arrangement, fee structure, or engagement setup and needs to classify the terms — for legal operations, outside counsel management, billing review, or engagement scoping.
---

# Identify Engagement Terms with FOLIO

Identify the engagement terms for a legal services arrangement using the FOLIO ontology's `engagement_terms` taxonomy branch.

## Workflow

Given a description of a legal services arrangement or billing structure, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with terms describing the fee structure, billing arrangement, or engagement type to find candidates in FOLIO.

2. **Browse the engagement terms taxonomy**: Use `folio:get_taxonomy_branch("engagement_terms")` to review all 14 top-level categories (e.g., Engagement Fee Model, Engagement Fee Detail, Invoice Terms, Engagement Arrangements, Source of Business, etc.).

3. **Drill into relevant categories**: Use `folio:get_children(iri)` on the most relevant categories to find specific terms (e.g., hourly rates, fixed fees, contingency fees, blended rates).

4. **Get full details**: Use `folio:get_concept(iri)` on each match for the complete definition, translations, identifiers, and cross-references.

## Output Format

Return each applicable engagement term as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this term
- **Parent Category**: The top-level engagement terms category
- **Relevance**: primary (directly describes the arrangement) or secondary (related or implied)
- **Reasoning**: Brief explanation of why this term applies

Most arrangements involve terms from multiple categories (e.g., a fee model plus invoice terms plus engagement arrangement). List all applicable terms grouped by category.
