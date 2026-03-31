---
name: folio-classify-entity
description: Classify a legal entity using the FOLIO ontology's actors_players and legal_entities taxonomy branches. Use when the user asks to classify, categorize, or identify the type of a legal entity — corporations, LLCs, trusts, partnerships, individuals, government agencies, courts, or any legal actor/role. Also use when the user needs to determine whether an entity is an actor/player (role or participant) or a legal entity (organization type), or when tagging entities with ontology terms.
---

# Classify a Legal Entity with FOLIO

Classify a legal entity against the FOLIO ontology's `actors_players` (roles and participants) and `legal_entities` (organization types) taxonomy branches.

## Workflow

Given an entity name or description, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the entity name or description to find candidate entity types in FOLIO.

2. **Check both branches**: Entities can appear in two branches:
   - Use `folio:get_taxonomy_branch("actors_players")` to check roles and participants (e.g., Plaintiff, Trustee, Shareholder)
   - Use `folio:get_taxonomy_branch("legal_entities")` to check organization types (e.g., Corporation, LLC, Trust)

3. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this entity type
- **Branch**: `actors_players` (role/participant) or `legal_entities` (organization type)
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If the entity could be classified in both branches (e.g., "Trustee" is both a role and relates to Trust as an entity type), note both classifications.
