<!-- mcp-name: io.github.alea-institute/folio -->

# folio-mcp

MCP server for [FOLIO](https://openlegalstandard.org/), the **F**ederated **O**pen **L**egal **I**nformation **O**ntology.

FOLIO is an open-source legal ontology with 18,000+ concepts covering areas of law, document types, legal entities, governmental bodies, and more. This MCP server makes the full ontology available to AI agents as searchable, browsable tools.

A public REST API is already available at **https://folio.openlegalstandard.org/** with interactive Swagger documentation at [/docs](https://folio.openlegalstandard.org/docs). This MCP server wraps the same ontology for native use in AI coding assistants and agent frameworks.

**License:** MIT (server code) / CC-BY 4.0 (ontology data)

## Backends

folio-mcp supports two interchangeable backends:

| Mode | Startup | Dependencies | Use case |
|------|---------|-------------|----------|
| **API** (default) | Instant | `httpx` only | Normal usage — calls the public FOLIO REST API |
| **Local** (`--local`) | ~10s | `folio-python[search]` | Offline use or when mounting inside folio-api |

### API mode (default)

The server starts instantly and delegates all queries to the public API at `https://folio.openlegalstandard.org/`. No local ontology loading required.

### Local mode

Loads the full FOLIO ontology in-process (~18k classes). Useful for offline work or when embedded in folio-api.

```bash
# Install with local dependencies
pip install folio-mcp[local]

# Run in local mode
folio-mcp --local

# Or via environment variable
FOLIO_MCP_LOCAL=1 folio-mcp
```

### Custom API URL

Point to a different FOLIO API instance:

```bash
folio-mcp --api-url https://my-folio-instance.example.com
```

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

## Tools (12)

| Tool | Description |
|------|-------------|
| `search_concepts(query, limit=10)` | Search concepts by label/name using fuzzy matching |
| `search_definitions(query, limit=10)` | Search concepts by definition text |
| `query_concepts(...)` | Advanced query with composable text and structural filters |
| `query_properties(...)` | Query OWL object properties by label, domain, range |
| `get_concept(iri)` | Get full details for a concept by IRI |
| `export_concept(iri, format)` | Export a concept as markdown, JSON-LD, or OWL XML |
| `list_branches()` | List all 24 taxonomy branches with concept counts |
| `get_taxonomy_branch(branch_name, max_depth)` | Get concepts in a taxonomy branch |
| `get_children(iri, max_depth)` | Get child concepts |
| `get_parents(iri, max_depth)` | Get parent concepts |
| `get_properties()` | Get all OWL object properties (relationships) |
| `find_connections(subject_iri, property_name, object_iri)` | Find semantic triples |

Browse operations return compact summaries (iri, label, definition). Use `get_concept(iri)` for full details including translations (31% of concepts, 10+ languages), preferred labels, external identifiers, and cross-references.

## Prompts (3)

| Prompt | Description | Argument |
|---|---|---|
| `classify-document` | Classify a legal document against the FOLIO taxonomy | `description` |
| `identify-area-of-law` | Identify applicable areas of law for a situation | `situation` |
| `classify-entity` | Classify a legal entity (person, org, role) | `entity` |

Each prompt guides the LLM through the correct tool workflow and returns structured output (FOLIO label, IRI, definition, confidence, reasoning).

## Resources (3)

| Resource URI | Description |
|---|---|
| `folio://branches` | Branch names with concept counts (564 bytes) |
| `folio://stats` | Ontology statistics — version, class/property counts, license |
| `folio://branch/{name}` | Top-level concepts in a specific branch (on-demand) |

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

# Run tests (requires folio-python for local backend tests)
uv sync --extra local
uv run pytest tests/

# Run with MCP Inspector
uv run mcp dev folio_mcp/server.py

# Run locally for Claude Code
claude mcp add folio-dev -- uv run --directory /path/to/folio-mcp folio-mcp
```

## Links

- [FOLIO Website](https://openlegalstandard.org/)
- [FOLIO REST API](https://folio.openlegalstandard.org/) — public API for direct HTTP access
- [FOLIO API Docs (Swagger)](https://folio.openlegalstandard.org/docs) — interactive API documentation
- [folio-python](https://github.com/alea-institute/folio-python) — Python client library
- [folio-api](https://github.com/alea-institute/folio-api) — REST API server
- [ALEA Institute](https://aleainstitute.ai/)
