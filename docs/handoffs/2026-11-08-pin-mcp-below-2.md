---
session: "99e13b54-da76-5dcf-a0cb-87248aa9ce3b"
written_at: "2026-11-08T12:49:30.783Z"
head: "03438098d730665807c135f2a8210c0551a3e984"
worktree: "/home/damienriehl/Coding Projects/folio-mcp"
branch: "fix/pin-mcp-below-2"
---
# Handoff: folio-mcp crashes on mcp 2.x — pin it, then release

## Goal

Make `uvx folio-mcp` start again for everyone. Today it exits on import
whenever the resolver picks `mcp` 2.x, which an unpinned install now does.

## Evidence (reproduced 2026-11-08)

- `uvx folio-mcp` (0.4.1 from PyPI) fails at startup:
  `ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x,
  where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import
  MCPServer) ...`
- `uvx --with 'mcp<2' folio-mcp` starts and answers `initialize` with
  `serverInfo.name = "FOLIO Legal Ontology"`.
- Root cause: `pyproject.toml` declares `mcp[cli]>=1.26` with no upper bound.
  `folio_mcp/server.py` imports `mcp.server.fastmcp` (line 21) and
  `mcp.server.fastmcp.prompts.base` (line 416); mcp 2.x removed both.
- Downstream workaround already shipped: the openlegalstandard.org repo's
  `.mcp.json` now runs `uvx --with "mcp<2" folio-mcp` (branch
  `feat/folio-tools-showcase`, commit `3572cea`).

## Work, in order

1. **Pin (the fix that ships first).** On this branch (`fix/pin-mcp-below-2`),
   change the dependency to `mcp[cli]>=1.26,<2`, refresh `uv.lock`, bump the
   version to 0.4.2 everywhere it appears (`pyproject.toml`,
   `folio_mcp/__init__.py` / `--version`, `server.json`, `manifest.json`,
   `glama.json`, `smithery.yaml` as applicable), and add a CHANGELOG entry.
2. **Regression test.** Add a test that fails if the declared `mcp`
   requirement allows a major version above 1 (parse `pyproject.toml`), plus
   run the existing suite (`uv run pytest`).
3. **Live check.** Build the wheel and run it with a fresh resolver:
   `uvx --from dist/<wheel> folio-mcp` must answer an `initialize` JSON-RPC
   request on stdin. Also confirm `uvx --from dist/<wheel> --with 'mcp>=2'
   folio-mcp` is refused by the resolver (proves the pin binds).
4. **Ship.** Push the branch, open a PR, merge it after the checks pass
   (Damien's standing authorization covers push, PR, and merge).
5. **Release to PyPI.** Find how earlier versions were published (git tags,
   CHANGELOG, any workflow or local build notes). Search for an existing
   PyPI credential *location* per the Decision Bar (list paths, never print
   values). If a publish path exists, release 0.4.2 and verify
   `uvx folio-mcp@0.4.2 --version`. If none exists, do not invent one: file a
   `cockpit-decide` ask (repo `folio-mcp`) and stop at a merged, unreleased
   fix.
6. **Follow-up, separate PR (optional, do not block the release).** Port to
   the mcp 2.x API (`MCPServer` from `mcp.server.mcpserver`, prompt message
   types) per the migration guide named in the error, then widen the pin. Only
   start this if the pin is released; otherwise record it as next work.

## After release

- The downstream pin in openlegalstandard.org can stay; note in that repo's PR
  #2 that it is redundant once 0.4.2 is on PyPI.
- `folio-api` depends on `folio-mcp>=0.2.0`; check whether its lock already
  holds mcp 1.x and note whether it needs a lock refresh.

## Done when

- The pin is merged, tests pass (including the new one), and the live wheel
  check shows the server answering.
- 0.4.2 is on PyPI, or a filed ask explains why it is not.
- This handoff file is deleted in the final commit, naming what absorbed it.
