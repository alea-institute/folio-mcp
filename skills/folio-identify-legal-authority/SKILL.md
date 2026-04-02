---
name: folio-identify-legal-authority
description: Identify the type of legal authority (statute, regulation, case law, treaty, executive order, constitution, directive, precedent, etc.) using the FOLIO ontology's legal_authorities taxonomy (14 top-level types). Use when the user has a legal citation, rule, regulation, or source of law and needs to classify what type of authority it represents — for legal research, citation analysis, authority hierarchy, or source-of-law classification.
---

# Identify a Legal Authority Type with FOLIO

Identify the type of legal authority using the FOLIO ontology's `legal_authorities` taxonomy branch.

## Workflow

Given a legal citation, rule, regulation, or source of law, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the authority name or type to find candidate authority types in FOLIO.

2. **Browse the authority taxonomy**: Use `folio:get_taxonomy_branch("legal_authorities")` to review all 14 top-level authority types (e.g., Statutes, Regulations, Caselaw, Treaties, Executive Orders, Constitutions, etc.).

3. **Drill into the best category**: Use `folio:get_children(iri)` on the most promising category to find the specific authority subtype.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this authority type
- **Parent Category**: The parent category in the taxonomy hierarchy
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If the authority could be classified under multiple types (e.g., an administrative regulation with statutory authority), note both classifications.
