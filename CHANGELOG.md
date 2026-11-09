# Changelog

## Unreleased

### Fixed

- A session cancelled mid-flight (idle timeout, server shutdown) never released its reference to a backend the server created itself. The cancellation fired at the lock acquire in the lifespan's cleanup, so that backend was never closed. The cleanup is now shielded. folio-api's injected backend was never affected.

### Changed

- Corrected the 0.4.3 note on thread offload: it does not free the event loop during fuzzy search (see below).

## 0.4.3 (2026-11-09)

### Fixed

- **Embedded server lost its shared graph after the first session.** Under streamable HTTP, FastMCP enters the server lifespan once per *session*. The lifespan cleared the backend that `set_shared_folio()` injected whenever any session ended, so every later session in folio-api fell back to an `APIBackend` that called the public REST API (the server calling itself, through its own rate limiter, which answered 429 under load). An injected backend is now never cleared or closed by a session.
- **One session closed the backend other sessions were using.** A backend the server creates itself is now shared by all live sessions, reference-counted, and closed only when the last session ends. Before, overlapping sessions failed with `Cannot send a request, as the client has been closed.`
- **Local-backend calls ran inline on the event loop.** folio-python's searches and traversals are synchronous. They now run in worker threads, as does the local-mode ontology load at first session. This frees the loop for the pure-Python tools (`query_concepts`, taxonomy traversal). It does **not** help `search_concepts` and `search_definitions`, which spend their time in a rapidfuzz call that holds the GIL. Freeing the loop during those needs a GIL-releasing search in folio-python.
- `test_query_has_children_filter` had been failing since browse responses went compact; it now checks the filter against the graph.

## 0.4.2 (2026-11-08)

### Fixed

- `uvx folio-mcp` crashed at startup with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` whenever the resolver picked `mcp` 2.x, which removed the FastMCP API this server uses. The dependency now reads `mcp[cli]>=1.26,<2`.

### Changed

- `manifest.json` and `smithery.yaml` versions now track the package version.

## 0.4.1 (2026-04-02)

### Added

- `--version` flag to the CLI

## 0.4.0 (2026-04-02)

### Added

- 8 new MCP prompt templates (slash commands) for legal classification workflows:
  - `classify-industry` — classify the industry sector for a matter or client (`industries` branch, 21 sectors)
  - `identify-legal-authority` — identify the type of legal authority such as statute, regulation, or case law (`legal_authorities` branch, 14 types)
  - `classify-event` — classify a legal event such as a dispute, transaction, or regulatory action (`events` branch, 14 categories)
  - `identify-service-type` — identify the type of legal service needed (`services` branch, 5 types)
  - `identify-forum-venue` — identify the appropriate forum, venue, or governmental body (`forum_venues` + `governmental_bodies` branches)
  - `identify-objective` — identify legal objectives for a matter (`objectives` branch, 13 categories)
  - `classify-asset` — classify an asset type (`asset_types` branch, 4 categories)
  - `identify-engagement-terms` — identify engagement terms for a legal services arrangement (`engagement_terms` branch, 14 categories)
- Skill metadata files (SKILL.md) for all 8 new prompts
- Updated server instructions to list all 11 slash commands

### Changed

- Server now exposes 11 prompt templates (up from 3)
- Updated main FOLIO skill metadata to reference all 11 classification workflows

## 0.3.1

- Add 3 MCP prompt templates: `classify-document`, `identify-area-of-law`, `classify-entity`
- Add classification skill metadata files
- Improve prompt discoverability in server instructions

## 0.3.0

- Compact browse responses (iri/label/definition only)
- Add `folio://branch/{name}` resource template
- Add translations, see_also, notes, source, country, preferred_label, identifier fields
- 12 tools, 3 resources

## 0.2.0

- Add public REST API backend (`--api-url`)
- Clarify IRI vs branch name usage in tool docs
- Cap max_depth at 3 with LLM guidance

## 0.1.0

- Initial release: MCP server for FOLIO legal ontology
- Local backend via folio-python
- Core search, browse, and export tools
