---
name: folio-classify-asset
description: Classify an asset type using the FOLIO ontology's asset_types taxonomy (4 top-level categories — Tangible Assets, Intangible Assets, Financial Assets, Estate). Use when the user describes an asset and needs to classify it — for transactional work, estate planning, IP matters, financial disputes, property classification, or asset inventory in legal matters.
---

# Classify an Asset Type with FOLIO

Classify an asset against the FOLIO ontology's `asset_types` taxonomy branch.

## Workflow

Given a description of an asset, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the asset name or description to find candidate asset types in FOLIO.

2. **Browse the asset types taxonomy**: Use `folio:get_taxonomy_branch("asset_types")` to see the 4 top-level categories:
   - **Tangible Assets**: Physical assets (real property, equipment, inventory)
   - **Intangible Assets**: Non-physical assets (IP, goodwill, licenses)
   - **Financial Assets**: Economic resources (securities, accounts, derivatives)
   - **Estate**: All possessions, property, and rights of a person or entity

3. **Drill into the best category**: Use `folio:get_children(iri)` on the most promising category to find the specific asset type.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this asset type
- **Parent Category**: The top-level asset category
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If the asset could fall under multiple categories (e.g., a patent is both an Intangible Asset and potentially a Financial Asset), note both classifications.
