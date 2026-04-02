# Changelog

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
