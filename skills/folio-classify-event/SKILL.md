---
name: folio-classify-event
description: Classify a legal event using the FOLIO ontology's events taxonomy (14 top-level categories including Dispute Events, Transaction Events, Bankruptcy Events, Regulatory Events, Employment Events, and more). Use when the user describes something that happened in a legal context and needs to classify the event type — filings, hearings, closings, settlements, terminations, regulatory actions, or any legal milestone or occurrence.
---

# Classify a Legal Event with FOLIO

Classify a legal event against the FOLIO ontology's `events` taxonomy branch.

## Workflow

Given a description of a legal event, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the event description or key terms to find candidate event types in FOLIO.

2. **Browse the events taxonomy**: Use `folio:get_taxonomy_branch("events")` to review all 14 top-level event categories (e.g., Dispute Events, Transaction Events, Bankruptcy and Restructuring Events, Regulatory Events, Employment Events, etc.).

3. **Drill into the best category**: Use `folio:get_children(iri)` on the most promising category to find the specific event type.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this event type
- **Parent Category**: The parent event category in the taxonomy hierarchy
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If the event spans multiple categories (e.g., a bankruptcy-related dispute hearing), list all applicable types with primary/secondary relevance.
