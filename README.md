<!-- mcp-name: io.github.alea-institute/folio -->

# folio-mcp

MCP server for [FOLIO](https://openlegalstandard.org/), the **F**ederated **O**pen **L**egal **I**nformation **O**ntology.

FOLIO is an open-source legal ontology with 18,000+ concepts covering areas of law, document types, legal entities, governmental bodies, and more. This MCP server makes the full ontology available to AI agents as searchable, browsable tools.

**License:** MIT (server code) / CC-BY 4.0 (ontology data)

## Installation

### Claude Code

```bash
claude mcp add folio -- uvx folio-mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "folio": {
      "command": "uvx",
      "args": ["folio-mcp"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "folio": {
      "command": "uvx",
      "args": ["folio-mcp"]
    }
  }
}
```

### VS Code

Add to your User Settings (JSON):

```json
{
  "mcp": {
    "servers": {
      "folio": {
        "command": "uvx",
        "args": ["folio-mcp"]
      }
    }
  }
}
```

### Remote (Streamable HTTP)

Connect to the hosted endpoint:

```
https://folio.openlegalstandard.org/mcp
```

### Manual (pip)

```bash
pip install folio-mcp
folio-mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `search_concepts(query, limit=10)` | Search concepts by label/name using fuzzy matching |
| `search_definitions(query, limit=10)` | Search concepts by definition text |
| `get_concept(iri)` | Get full details for a concept by IRI |
| `export_concept(iri, format)` | Export a concept as markdown, JSON-LD, or OWL XML |
| `list_branches()` | List all 24 taxonomy branches with concept counts |
| `get_taxonomy_branch(branch_name, max_depth)` | Get concepts in a taxonomy branch |
| `get_children(iri, max_depth)` | Get child concepts |
| `get_parents(iri, max_depth)` | Get parent concepts |
| `get_properties()` | Get all OWL object properties (relationships) |
| `find_connections(subject_iri, property_name, object_iri)` | Find semantic triples |

## Resources

| Resource URI | Description |
|---|---|
| `folio://branches` | Branch names with concept counts |
| `folio://stats` | Ontology statistics (version, class/property counts) |

## Taxonomy Branches

The FOLIO ontology is organized into 24 top-level branches:

| Branch | Description |
|--------|-------------|
| `actors_players` | Parties, roles, and participants in legal matters |
| `areas_of_law` | Legal practice areas and specializations |
| `asset_types` | Types of assets (real property, intellectual property, etc.) |
| `communication_modalities` | Communication channels and methods |
| `currencies` | Monetary currencies |
| `data_formats` | Data and file formats |
| `document_artifacts` | Legal documents, contracts, filings |
| `engagement_terms` | Terms of engagement and fee arrangements |
| `events` | Legal events and milestones |
| `forum_venues` | Courts, tribunals, and dispute resolution venues |
| `governmental_bodies` | Government agencies and departments |
| `industries` | Industry sectors and classifications |
| `languages` | Natural languages |
| `folio_types` | FOLIO internal type classifications |
| `legal_authorities` | Statutes, regulations, case law |
| `legal_entities` | Entity types (corporations, LLCs, trusts, etc.) |
| `locations` | Geographic locations and jurisdictions |
| `matter_narratives` | Matter descriptions and narratives |
| `matter_narrative_formats` | Formats for matter narratives |
| `objectives` | Legal objectives and goals |
| `services` | Legal services and service types |
| `standards_compatibilities` | Standards and compatibility mappings |
| `statuses` | Status values for matters, documents, etc. |
| `system_identifiers` | System and external identifiers |

## Development

```bash
# Clone and install
git clone https://github.com/alea-institute/folio-mcp.git
cd folio-mcp
uv sync

# Run tests
uv run pytest tests/

# Run with MCP Inspector
uv run mcp dev folio_mcp/server.py

# Run locally for Claude Code
claude mcp add folio-dev -- uv run --directory /path/to/folio-mcp folio-mcp
```

## Links

- [FOLIO Website](https://openlegalstandard.org/)
- [FOLIO API](https://folio.openlegalstandard.org/)
- [folio-python](https://github.com/alea-institute/folio-python)
- [ALEA Institute](https://aleainstitute.ai/)
