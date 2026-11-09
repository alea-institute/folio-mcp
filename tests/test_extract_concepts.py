"""
Tests for extract_concepts: the stdlib dictionary tagger, both backends, and the tool.
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from folio_mcp import server
from folio_mcp.backends.api import APIBackend
from folio_mcp.backends.local import LocalBackend
from folio_mcp.tagger import ConceptTagger


def _rec(iri, label, branch="objectives", alts=None, pref=None, deprecated=False):
    return {
        "iri": iri,
        "label": label,
        "preferred_label": pref,
        "alternative_labels": alts or [],
        "deprecated": deprecated,
        "branch": branch,
    }


RECORDS = [
    _rec("T1", "Temporary Restraining Order", "document_artifacts"),
    _rec("T2", "Order", "document_artifacts"),
    _rec("C1", "Creditor", "actors_players"),
    _rec("C2", "Unsecured Creditor", "actors_players"),
    _rec("A1", "Agreements", "document_artifacts", alts=["Agreement"]),
    _rec("Q1", "Quiet Enjoyment Clause", "objectives"),
    _rec("N1", "Negligence Claims", "objectives"),
    _rec("S1", "U.S. Securities and Exchange Commission", "governmental_bodies", alts=["SEC"]),
    _rec("P1", "Spousal Support", "objectives", pref="Alimony"),
    _rec("L1", "Lease", "document_artifacts"),
    _rec("L2", "Leasing Practice", "services", alts=["Lease Practice", "Lease"]),
    _rec("D1", "Deprecated Thing", "objectives", deprecated=True),
    _rec("X1", "Invoice Line Item", "standards_compatibilities"),
    *[_rec(f"M{i}", f"Ambiguous {i}", "objectives", alts=["Shared Synonym"]) for i in range(4)],
]


@pytest.fixture(scope="module")
def tagger():
    return ConceptTagger(RECORDS)


def _labels(results):
    return [r["label"] for r in results]


class TestConceptTagger:
    def test_longest_match_wins(self, tagger):
        res = tagger.tag("They sought a temporary restraining order today.")
        assert _labels(res) == ["Temporary Restraining Order"]
        assert res[0]["matched_text"] == ["temporary restraining order"]

    def test_generic_single_word_label_is_skipped(self, tagger):
        assert tagger.tag("The court entered an order.") == []

    def test_plural_text_matches_singular_label(self, tagger):
        res = tagger.tag("Unsecured creditors objected; other creditors joined.")
        assert _labels(res) == ["Unsecured Creditor", "Creditor"]

    def test_plural_multiword_label_matches_singular_text(self, tagger):
        assert _labels(tagger.tag("a negligence claim")) == ["Negligence Claims"]

    def test_single_word_alt_label_is_dropped(self, tagger):
        assert tagger.tag("The agreement was signed.") == []

    def test_derived_form_strips_clause_suffix(self, tagger):
        res = tagger.tag("breach of the covenant of quiet enjoyment")
        assert _labels(res) == ["Quiet Enjoyment Clause"]
        assert res[0]["match_type"] == "derived"

    def test_acronym_is_case_sensitive(self, tagger):
        assert _labels(tagger.tag("The SEC sued.")) == ["U.S. Securities and Exchange Commission"]
        assert tagger.tag("Wait a sec.") == []

    def test_preferred_label_matches(self, tagger):
        assert _labels(tagger.tag("She seeks alimony.")) == ["Spousal Support"]

    def test_label_beats_alt_label(self, tagger):
        assert _labels(tagger.tag("The lease expired.")) == ["Lease"]

    def test_ambiguous_surface_form_is_dropped(self, tagger):
        assert tagger.tag("a shared synonym here") == []

    def test_deprecated_and_skipped_branches_excluded(self, tagger):
        assert tagger.tag("deprecated thing and invoice line item") == []

    def test_counts_and_offsets(self, tagger):
        text = "Lease terms. The LEASE ends."
        (res,) = tagger.tag(text)
        assert res["count"] == 2
        assert res["matched_text"] == ["Lease", "LEASE"]
        assert res["first_offset"] == 0

    def test_branch_filter_and_limit(self, tagger):
        text = "The lease and the temporary restraining order; creditors objected."
        assert _labels(tagger.tag(text, branch="actors_players")) == ["Creditor"]
        assert len(tagger.tag(text, limit=2)) == 2


LEASE_TEXT = (
    "Our client, a commercial tenant, received a notice of default from the landlord claiming "
    "unpaid rent under a ten-year lease. The landlord threatens eviction and to draw on the "
    "security deposit, and the tenant seeks a temporary restraining order in Illinois."
)


@pytest.mark.asyncio
class TestLocalExtractConcepts:
    async def test_lease_paragraph(self, local_backend: LocalBackend):
        data = json.loads(await local_backend.extract_concepts(LEASE_TEXT, 50, None))
        labels = {c["label"] for c in data["concepts"]}
        assert {"Tenant", "Landlord", "Lease", "Temporary Restraining Order", "Illinois"} <= labels
        assert data["count"] == len(data["concepts"])
        first = data["concepts"][0]
        assert set(first) >= {"iri", "label", "branch", "match_type", "matched_text", "count", "first_offset"}
        assert first["iri"].startswith("https://folio.openlegalstandard.org/")

    async def test_branch_filter(self, local_backend: LocalBackend):
        data = json.loads(await local_backend.extract_concepts(LEASE_TEXT, 50, "actors_players"))
        assert data["concepts"]
        assert {c["branch"] for c in data["concepts"]} == {"actors_players"}

    async def test_no_false_hit_on_boilerplate(self, local_backend: LocalBackend):
        data = json.loads(await local_backend.extract_concepts("The parties signed the agreement.", 50, None))
        assert data["concepts"] == []


def _taxonomy_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/taxonomy/actor_player":
        return httpx.Response(200, json={"classes": [
            {"iri": "https://folio.openlegalstandard.org/AP1", "label": "Landlord", "alternative_labels": ["Lessor"]},
        ]})
    if request.url.path == "/taxonomy/document_artifact":
        return httpx.Response(200, json={"classes": [
            {"iri": "https://folio.openlegalstandard.org/DA1", "label": "Lease"},
            {"iri": "https://folio.openlegalstandard.org/AP1", "label": "Landlord"},
        ]})
    if request.url.path.startswith("/taxonomy/"):
        return httpx.Response(200, json={"classes": []})
    return httpx.Response(404)


@pytest.mark.asyncio
class TestAPIExtractConcepts:
    async def test_builds_index_from_taxonomy(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            return _taxonomy_handler(request)

        backend = APIBackend(base_url="https://folio.test")
        backend._client = httpx.AsyncClient(base_url="https://folio.test", transport=httpx.MockTransport(handler))
        try:
            data = json.loads(await backend.extract_concepts("The landlord terminated the lease.", 50, None))
            assert [(c["label"], c["branch"]) for c in data["concepts"]] == [
                ("Landlord", "actors_players"),
                ("Lease", "document_artifacts"),
            ]
            n_calls = len(calls)
            assert "/taxonomy/standards_compatibility" not in calls
            await backend.extract_concepts("lease", 50, None)
            assert len(calls) == n_calls  # index is cached
        finally:
            await backend.close()

    async def test_api_error_returns_error_json(self):
        backend = APIBackend(base_url="https://folio.test")
        backend._client = httpx.AsyncClient(
            base_url="https://folio.test", transport=httpx.MockTransport(lambda r: httpx.Response(503))
        )
        try:
            data = json.loads(await backend.extract_concepts("lease", 50, None))
            assert "error" in data
        finally:
            await backend.close()


class _StubBackend:
    def __init__(self):
        self.calls = []

    async def extract_concepts(self, text, limit, branch):
        self.calls.append((text, limit, branch))
        return json.dumps({"count": 0, "concepts": []})


def _ctx(backend):
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context={"backend": backend}))


@pytest.mark.asyncio
class TestExtractConceptsTool:
    async def test_delegates_to_backend(self):
        stub = _StubBackend()
        out = json.loads(await server.extract_concepts(_ctx(stub), "text", limit=5, branch="events"))
        assert out == {"count": 0, "concepts": []}
        assert stub.calls == [("text", 5, "events")]

    async def test_unknown_branch(self):
        stub = _StubBackend()
        out = json.loads(await server.extract_concepts(_ctx(stub), "text", branch="nope"))
        assert "error" in out and "available_branches" in out
        assert stub.calls == []

    async def test_text_too_long(self):
        stub = _StubBackend()
        out = json.loads(await server.extract_concepts(_ctx(stub), "x" * (server.MAX_EXTRACT_CHARS + 1)))
        assert "error" in out and "hint" in out
        assert stub.calls == []

    async def test_tool_is_registered(self):
        names = {t.name for t in await server.mcp.list_tools()}
        assert "extract_concepts" in names
