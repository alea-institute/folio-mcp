"""
Legal citation extraction mapped to FOLIO legal authority types.

Optional: needs the ``kaos`` extra (``kaos-citations``, Python >= 3.13).
Import of this module is always safe; ``kaos_citations`` is imported lazily
inside :func:`extract_citations`.
"""

# imports
import importlib.util
from typing import Dict, List, Optional, Tuple

_FOLIO = "https://folio.openlegalstandard.org/"

# FOLIO legal_authorities concepts: (short IRI id, label)
_US_CODE = ("RGSYEjChlHNtLNr8xML1Y1", "U.S. Code")
_STATUTES = ("RHagFJXtPsCCn5dbENWLNR", "Statutes")
_CFR = ("R9H2moSYZ56RmnlXQ06F6gY", "U.S. Code of Federal Regulations")
_REGULATIONS = ("RrECTdM9f5ml4sac9MFrSC", "Regulations")
_CASELAW = ("RM6KeGyv1uH0zuGDufnxkw", "Caselaw and Common Law")
_CONSTITUTIONS = ("R7ThXbAhhJvDfLZDgWWqPJz", "Constitutions")
_EXEC_ORDERS = ("R34OeWRUurl4TJP99m6uiC", "Executive Orders")
_SECONDARY = ("RSEc3J4h5XdVfKKWBG7u08", "Secondary Legal Authorities")
_TREATISE = ("R9twyHb3yZtdEWn4hwBuoLk", "Treatise")
_LEGISLATION = ("RDEUUJX38pZaHpn7lXM0GIV", "Legislation")
_SENTENCING = ("RB7BbLR5TMwSkGVKHVSs4Ng", "Sentencing Guidelines")
_TREATIES = ("RBW9y6esXubLJl4QMtm0Y70", "Treaties")
_LOCAL_RULES = ("RCUIlUpsVsyQs46CyHTJLMq", "Local Ruleset")
_PROF_CONDUCT = ("RCh6DNVTpKuGNGUFfysj3uD", "Rules of Professional Conduct")

_FED_RULE_SETS: Dict[str, Tuple[str, str]] = {
    "FRCP": ("RCYvQpgG6Mv1JOAf7tSjjgV", "Federal Rules of Civil Procedure"),
    "FRE": ("R9sYB6Cf3u3k5hxxUFJyJHA", "Federal Rules of Evidence"),
    "FRCRMP": ("RBFBw7fG6mULNtDPzoDp3Vz", "Federal Rules of Criminal Procedure"),
    "FRAP": ("RWI3FSZADDKSQNARn0Im4m", "Federal Rules of Appellate Procedure"),
    "FRBP": ("RMuijAVect7dn58aEHA3KD", "Federal Rules of Bankruptcy Procedure"),
}

# kaos-citations kind -> FOLIO legal authority
_KIND_AUTHORITY: Dict[str, Tuple[str, str]] = {
    "statute": _STATUTES,
    "state_session_law": _STATUTES,
    "cfr": _CFR,
    "treas_reg": _CFR,
    "fed_register": _REGULATIONS,
    "sec_reg": _REGULATIONS,
    "fed_reserve_reg": _REGULATIONS,
    "case": _CASELAW,
    "case_short": _CASELAW,
    "case_ref": _CASELAW,
    "const": _CONSTITUTIONS,
    "exec_action": _EXEC_ORDERS,
    "restatement": _SECONDARY,
    "journal": _SECONDARY,
    "treatise": _TREATISE,
    "public_law": _LEGISLATION,
    "legislative": _LEGISLATION,
    "uniform_act": _LEGISLATION,
    "ussg": _SENTENCING,
    "treaty": _TREATIES,
    "local_rule": _LOCAL_RULES,
    "pro_conduct": _PROF_CONDUCT,
}

# CourtListener-style court ids -> FOLIO forum_venues concepts
_COURTS: Dict[str, Tuple[str, str]] = {
    "scotus": ("RFE94c038Ce43B892dbECa17", "U.S. Supreme Court"),
    "ca1": ("R0E02e35EB9a13C61679Dd0c", "U.S. Ct. App. - 1st Circuit"),
    "ca2": ("RF27635F89fb52084fc5606d", "U.S. Ct. App. - 2nd Circuit"),
    "ca3": ("R3EFbb71D99d2A27e13E37d6", "U.S. Ct. App. - 3rd Circuit"),
    "ca4": ("R4293aeBB8388D571234B7ca", "U.S. Ct. App. - 4th Circuit"),
    "ca5": ("R89A53fB53f1d7B2486D6707", "U.S. Ct. App. - 5th Circuit"),
    "ca6": ("RE1D24dB13e494614587544e", "U.S. Ct. App. - 6th Circuit"),
    "ca7": ("R1D326471568c63Dee837290", "U.S. Ct. App. - 7th Circuit"),
    "ca8": ("R916aeb4C105741Dcd1DC34e", "U.S. Ct. App. - 8th Circuit"),
    "ca9": ("R92780f27E68cDE74a98665c", "U.S. Ct. App. - 9th Circuit"),
    "ca10": ("RF9733f9B078aEBC33900183", "U.S. Ct. App. - 10th Circuit"),
    "ca11": ("R360e3645285d9DDa3410d15", "U.S. Ct. App. - 11th Circuit"),
    "cadc": ("R55Ddd328Bad1BDDdb2CC71c", "U.S. Ct. App. - D.C. Circuit"),
    "cafc": ("RAC55f5599a3fA48ebe66163", "U.S. Ct. App. - Federal Circuit"),
}

_MISSING_HINT = (
    "Citation extraction needs the optional 'kaos' extra on Python >= 3.13: "
    "uvx --python 3.13 --from 'folio-mcp[kaos]' folio-mcp"
)


def citations_available() -> bool:
    """True when the optional kaos-citations package is importable."""
    try:
        return importlib.util.find_spec("kaos_citations") is not None
    except (ImportError, ValueError):
        return False


def _concept(ref: Tuple[str, str]) -> dict:
    return {"iri": _FOLIO + ref[0], "label": ref[1]}


def authority_for(kind: str, citation: object) -> Optional[Tuple[str, str]]:
    """FOLIO legal authority for one kaos-citations citation, if any."""
    if kind == "fed_rule":
        return _FED_RULE_SETS.get(str(getattr(citation, "rule_set", "") or "").upper())
    if kind == "statute" and str(getattr(citation, "code", "") or "").replace(" ", "") == "U.S.C.":
        return _US_CODE
    return _KIND_AUTHORITY.get(kind)


def extract_citations(text: str, limit: int = 100) -> dict:
    """Extract citations from text and map each to FOLIO concepts."""
    try:
        import kaos_citations  # pylint: disable=import-outside-toplevel
    except ImportError:
        return {"error": "kaos-citations is not installed", "hint": _MISSING_HINT}

    results: List[dict] = []
    for cite in kaos_citations.extract_citations(text)[:limit]:
        kind = str(getattr(cite, "kind", "") or "")
        span = getattr(cite, "span", None)
        item: dict = {
            "text": getattr(cite, "normalized", None) or getattr(cite, "raw", None),
            "kind": kind,
        }
        if isinstance(span, (tuple, list)) and len(span) == 2:
            item["start"], item["end"] = span[0], span[1]
        case_name = getattr(cite, "case_name", None)
        if case_name:
            item["case_name"] = case_name
        authority = authority_for(kind, cite)
        if authority:
            item["folio_authority"] = _concept(authority)
        court = _COURTS.get(str(getattr(cite, "court", "") or "").lower())
        if court:
            item["folio_forum"] = _concept(court)
        results.append(item)
    return {"count": len(results), "citations": results}
