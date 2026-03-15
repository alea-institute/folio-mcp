---
name: folio
description: Search and browse FOLIO, the open legal ontology with 18,000+ concepts covering areas of law, document types, legal entities, and more. Use when classifying legal concepts, finding document types, identifying areas of law, or mapping legal entity structures.
---

# FOLIO Legal Ontology Skill

## When to Use

Use the FOLIO MCP tools when you need to:

- **Classify legal concepts**: Find the correct ontology term for a legal concept
- **Identify document types**: Look up legal document classifications (contracts, filings, opinions)
- **Find areas of law**: Determine which legal practice area applies
- **Map entity types**: Identify types of legal entities (corporations, trusts, partnerships)
- **Explore relationships**: Find how legal concepts relate to each other
- **Export definitions**: Get formal definitions in markdown, JSON-LD, or OWL XML

## How to Search

Follow this 4-step workflow:

1. **Search by name**: Start with `search_concepts(query)` to find concepts by label
2. **Refine by definition**: If name search is too broad, use `search_definitions(query)`
3. **Browse branches**: Use `list_branches()` then `get_taxonomy_branch(branch_name)` to explore a category
4. **Navigate hierarchy**: Use `get_children(iri)` and `get_parents(iri)` to explore up/down the taxonomy

## Branch Reference

| Branch Key | Description |
|------------|-------------|
| `actors_players` | Parties, roles, participants |
| `areas_of_law` | Practice areas, specializations |
| `asset_types` | Property, IP, financial assets |
| `communication_modalities` | Communication channels |
| `currencies` | Monetary currencies |
| `data_formats` | Data and file formats |
| `document_artifacts` | Legal documents, contracts |
| `engagement_terms` | Fee arrangements, engagement terms |
| `events` | Legal events, milestones |
| `forum_venues` | Courts, tribunals, venues |
| `governmental_bodies` | Government agencies |
| `industries` | Industry sectors |
| `languages` | Natural languages |
| `folio_types` | Internal FOLIO types |
| `legal_authorities` | Statutes, regulations, case law |
| `legal_entities` | Corporations, LLCs, trusts |
| `locations` | Geographic locations |
| `matter_narratives` | Matter descriptions |
| `matter_narrative_formats` | Narrative formats |
| `objectives` | Legal objectives |
| `services` | Legal services |
| `standards_compatibilities` | Standards mappings |
| `statuses` | Status values |
| `system_identifiers` | External identifiers |

## Example Workflow

**Task**: Find the FOLIO classification for a "software licensing agreement"

```
1. search_concepts("software licensing agreement")
   → Finds candidates like "Software License Agreement", "License Agreement"

2. get_concept(iri)
   → Gets full details including definition, parent/child concepts

3. get_parents(iri)
   → Shows taxonomy: Software License Agreement → License Agreement → Contract → Document/Artifact

4. export_concept(iri, format="markdown")
   → Gets a clean markdown export for documentation
```
