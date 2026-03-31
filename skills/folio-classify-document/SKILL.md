---
name: folio-classify-document
description: Classify a legal document using the FOLIO ontology's document_artifacts taxonomy (18,000+ legal concepts). Use when the user asks to classify, categorize, or identify the type of a legal document — contracts, filings, pleadings, opinions, agreements, deeds, briefs, memoranda, or any legal document type. Also use when the user has a document and needs to find its formal FOLIO classification, or when tagging documents with ontology terms.
---

# Classify a Legal Document with FOLIO

Classify a legal document against the FOLIO ontology's `document_artifacts` taxonomy branch.

## Workflow

Given a document name or description, follow these steps:

1. **Search for matches**: Use `folio:search_concepts` with the document name or key terms to find candidate document types in FOLIO.

2. **Browse the document taxonomy**: If no strong match is found, use `folio:get_taxonomy_branch("document_artifacts")` to see the top-level document categories (e.g., Contracts, Court Documents, Legislative Documents, etc.).

3. **Drill into the best category**: Use `folio:get_children(iri)` on the most promising top-level category to find the specific document type.

4. **Get full details**: Use `folio:get_concept(iri)` on the best match to retrieve the complete definition, translations, identifiers, and cross-references.

## Output Format

Return the classification as:

- **FOLIO Label**: The official FOLIO concept name
- **FOLIO IRI**: The concept's unique identifier (e.g., `https://folio.openlegalstandard.org/...`)
- **Definition**: The FOLIO definition of this document type
- **Parent Category**: The parent concept in the taxonomy hierarchy
- **Confidence**: high / medium / low
- **Reasoning**: Brief explanation of why this classification was chosen

If multiple classifications could apply, list the primary match first, then alternatives with their confidence levels.
