---
name: folio-classify-industry
description: Classify the industry sector for a legal matter, client, or company using the FOLIO ontology's industries taxonomy (21 sectors including Finance, Healthcare, Manufacturing, Technology, Energy, and more). Use when the user needs to identify which industry a client, matter, or company falls in — for client intake, matter classification, conflict checking, or industry-specific legal analysis.
---

# Classify an Industry with FOLIO

Classify the industry sector for a matter or client against the FOLIO ontology's `industries` taxonomy branch.

## Workflow

Given a company, client, or matter description, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the company name, industry terms, or business description to find candidate industry types in FOLIO.

2. **Browse the industry taxonomy**: Use `folio:get_taxonomy_branch("industries")` to review all 21 top-level industry sectors (e.g., Finance and Insurance, Health Care, Manufacturing, Professional Services, etc.).

3. **Drill into the best sector**: Use `folio:get_children(iri)` on the most promising top-level sector to find the specific sub-industry.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this industry
- **Parent Sector**: The parent industry sector (if classifying a sub-industry)
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If the matter spans multiple industries (e.g., a fintech company), list all applicable industries with primary/secondary relevance.
