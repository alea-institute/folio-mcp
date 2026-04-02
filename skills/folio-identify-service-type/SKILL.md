---
name: folio-identify-service-type
description: Identify the type of legal service needed for a matter using the FOLIO ontology's services taxonomy (5 top-level types — Advisory, Transactional, Dispute, Regulatory, Bankruptcy/Restructuring). Use when the user describes a legal matter and needs to determine what category of legal service applies — for engagement scoping, matter intake, practice group routing, or legal operations classification.
---

# Identify a Legal Service Type with FOLIO

Identify the type of legal service needed using the FOLIO ontology's `services` taxonomy branch.

## Workflow

Given a description of a legal matter, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with key terms from the matter to find candidate service types in FOLIO.

2. **Browse the services taxonomy**: Use `folio:get_taxonomy_branch("services")` to review all 5 top-level service categories:
   - **Advisory Service**: Advice to a single party without adversarial event
   - **Transactional Practice**: Two or more parties creating a contract
   - **Dispute Service**: Conflict/adversarial event
   - **Regulatory Services**: Filing with a governmental entity
   - **Bankruptcy and Financial Restructuring**: Liquidation or restructuring

3. **Drill into the best match**: Use `folio:get_children(iri)` on the most promising service category to find specific service subtypes.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return each applicable service type as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this service type
- **Relevance**: primary (main service needed) or secondary (may also be involved)
- **Reasoning**: Brief explanation of why this service type applies

Most matters map to a single primary service type, but complex matters may involve multiple (e.g., a merger with regulatory approval involves both Transactional and Regulatory).
