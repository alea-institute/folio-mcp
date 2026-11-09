"""
Tests for the optional extract_citations tool (kaos extra, Python >= 3.13).
"""

import json
import sys
from types import SimpleNamespace

import pytest

from folio_mcp import citations, server


class TestAuthorityMapping:
    """Mapping logic only; runs without kaos-citations."""

    def test_usc_statute_maps_to_us_code(self):
        assert citations.authority_for("statute", SimpleNamespace(code="U.S.C."))[1] == "U.S. Code"

    def test_state_statute_maps_to_statutes(self):
        assert citations.authority_for("statute", SimpleNamespace(code="Cal. Gov. Code"))[1] == "Statutes"

    def test_federal_rule_sets(self):
        assert citations.authority_for("fed_rule", SimpleNamespace(rule_set="FRCP"))[1] == (
            "Federal Rules of Civil Procedure"
        )
        assert citations.authority_for("fed_rule", SimpleNamespace(rule_set="FRE"))[1] == "Federal Rules of Evidence"

    def test_unknown_kind(self):
        assert citations.authority_for("doi", SimpleNamespace()) is None


def test_missing_extra_returns_error_and_hint(monkeypatch):
    monkeypatch.setitem(sys.modules, "kaos_citations", None)  # makes the import fail
    out = citations.extract_citations("42 U.S.C. § 1983")
    assert set(out) == {"error", "hint"}
    assert "kaos" in out["hint"]


kaos_citations = pytest.importorskip("kaos_citations")


class TestExtractCitations:
    def test_statute_rule_and_case(self):
        text = (
            "Plaintiff sues under 42 U.S.C. § 1983. Defendant moves under Fed. R. Civ. P. 12(b)(6). "
            "See Bell Atlantic Corp. v. Twombly, 550 U.S. 544, 570 (2007); "
            "Smith v. Jones, 123 F.3d 456 (9th Cir. 1997)."
        )
        out = citations.extract_citations(text)
        got = [(c["kind"], c["folio_authority"]["label"], c.get("folio_forum", {}).get("label")) for c in out["citations"]]
        assert got == [
            ("statute", "U.S. Code", None),
            ("fed_rule", "Federal Rules of Civil Procedure", None),
            ("case", "Caselaw and Common Law", "U.S. Supreme Court"),
            ("case", "Caselaw and Common Law", "U.S. Ct. App. - 9th Circuit"),
        ]
        first = out["citations"][0]
        assert text[first["start"]:first["end"]] == "42 U.S.C. § 1983"
        assert first["folio_authority"]["iri"].startswith("https://folio.openlegalstandard.org/")

    def test_mapped_iris_exist_in_folio(self, folio_graph):
        refs = list(citations._KIND_AUTHORITY.values()) + list(citations._FED_RULE_SETS.values())
        refs += list(citations._COURTS.values()) + [citations._US_CODE]
        for iri_id, label in refs:
            cls = folio_graph[iri_id]
            assert cls is not None, iri_id
            assert cls.label == label

    @pytest.mark.asyncio
    async def test_tool_registered_and_returns_json(self):
        names = {t.name for t in await server.mcp.list_tools()}
        assert "extract_citations" in names
        result = await server.mcp.call_tool("extract_citations", {"text": "See 11 U.S.C. § 362(a)."})
        content = result[0] if isinstance(result, tuple) else result
        out = json.loads(content[0].text)
        assert out["count"] == 1
        assert out["citations"][0]["folio_authority"]["label"] == "U.S. Code"
