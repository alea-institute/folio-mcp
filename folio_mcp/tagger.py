"""
Dictionary tagger: find FOLIO concepts mentioned in free text.

Pure standard library. Builds a token n-gram dictionary from FOLIO labels,
preferred labels and alternative labels, then scans text with greedy
leftmost-longest matching. Both backends feed it the same records, so the
tool behaves the same in API and local mode.

Matching rules (chosen to keep precision high on lawyer prose):
- text and labels are NFKC-normalized, split on word characters and
  casefolded; a plural last word in the text may match a singular label
  ("unsecured creditors" ~ "Unsecured Creditor"), and a plural multi-word
  label may match singular text ("negligence claim" ~ "Negligence Claims")
- primary labels win over alternative labels, which win over derived forms
  (a label with a trailing "Clause"/"Claim"/"Law", a leading "U.S." or a
  parenthetical stripped, e.g. "Quiet Enjoyment Clause" ~ "quiet enjoyment")
- single-word alternative labels and single-word derived forms are dropped
  (they caused most false positives, e.g. "agreement" -> "License (Agreement)")
- surface forms shared by more than three concepts are dropped as ambiguous
- short all-caps acronyms ("SEC", "EEOC") match case-sensitively only
"""

# imports
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

# Branches that hold data-exchange codes and field names, not legal concepts.
SKIP_BRANCHES = frozenset({
    "standards_compatibilities",
    "system_identifiers",
    "data_formats",
    "matter_narrative_formats",
    "folio_types",
})

# Single words that are FOLIO labels but too generic to tag on their own.
_STOP_SINGLE = frozenset({
    "the", "other", "all", "general", "none", "unknown", "status", "type", "yes", "no",
    "will", "may", "act", "order", "party", "state", "event", "form", "case", "term",
    "notice", "action", "can", "us", "right", "exchange", "search", "appeal", "authority",
    "distribution", "assessment", "aggravated", "unpaid", "unsecured", "information",
    "code", "codes",
})
_DERIVED_SUFFIXES = frozenset({"clause", "claim", "law", "practice"})
_LEADING_ARTICLES = frozenset({"the", "a", "an"})
_MAX_AMBIGUITY = 3
_MAX_TOKENS = 8

_TOKEN_RE = re.compile(r"\w+")
_PAREN_RE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")

_KIND_RANK = {"label": 0, "alt": 1, "derived": 2}


def _singular(t: str) -> str:
    """Light English plural fold for an already casefolded token."""
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        return t[:-1]
    return t


def _tokens(text: str) -> List[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(unicodedata.normalize("NFKC", text))]


def _derived_forms(label: str) -> Iterable[List[str]]:
    """Shorter forms of a label that lawyers write in prose."""
    stripped = _PAREN_RE.sub("", label).strip()
    toks = _tokens(stripped)
    if stripped != label:
        yield toks
    if len(toks) > 2 and toks[0] == "u" and toks[1] == "s":
        toks = toks[2:]
        yield toks
    if len(toks) > 1 and toks[-1] in _DERIVED_SUFFIXES:
        yield toks[:-1]
    if len(toks) > 1 and _singular(toks[-1]) != toks[-1]:
        yield toks[:-1] + [_singular(toks[-1])]


class ConceptTagger:
    """Greedy longest-match tagger over a FOLIO label dictionary."""

    def __init__(self, records: Iterable[dict]):
        # surface key -> {iri: (kind, label, branch)}
        raw: Dict[Tuple[str, ...], Dict[str, Tuple[str, str, Optional[str]]]] = {}
        acronyms: Dict[str, Dict[str, Tuple[str, str, Optional[str]]]] = {}

        def add(key: Tuple[str, ...], iri: str, kind: str, label: str, branch: Optional[str]) -> None:
            slot = raw.setdefault(key, {})
            prev = slot.get(iri)
            if prev is None or _KIND_RANK[kind] < _KIND_RANK[prev[0]]:
                slot[iri] = (kind, label, branch)

        for rec in records:
            if rec.get("deprecated") or not rec.get("label") or not rec.get("iri"):
                continue
            branch = rec.get("branch")
            if branch in SKIP_BRANCHES:
                continue
            iri, label = rec["iri"], rec["label"]
            forms = [(label, "label")]
            pref = rec.get("preferred_label")
            if pref and pref != label:
                forms.append((pref, "label"))
            forms += [(a, "alt") for a in rec.get("alternative_labels") or [] if a]
            for form, kind in forms:
                form = form.strip()
                if not form or "_" in form or "+" in form or ":" in form:
                    continue
                if form.isalpha() and form.isupper() and 3 <= len(form) <= 6:
                    acronyms.setdefault(form, {}).setdefault(iri, (kind, label, branch))
                    continue
                toks = _tokens(form)
                if not toks or len(toks) > _MAX_TOKENS or toks[0] in _LEADING_ARTICLES:
                    continue
                if len(toks) == 1 and (kind != "label" or len(form) < 4 or toks[0] in _STOP_SINGLE):
                    continue
                add(tuple(toks), iri, kind, label, branch)
            for toks in _derived_forms(label):
                if len(toks) >= 2 and toks[0] not in _LEADING_ARTICLES:
                    add(tuple(toks), iri, "derived", label, branch)

        self._dict: Dict[Tuple[str, ...], List[Tuple[str, str, str, Optional[str]]]] = {}
        for key, by_iri in raw.items():
            best = min(_KIND_RANK[k] for k, _, _ in by_iri.values())
            hits = [(iri, kind, label, br) for iri, (kind, label, br) in by_iri.items() if _KIND_RANK[kind] == best]
            if len(hits) <= _MAX_AMBIGUITY:
                self._dict[key] = hits
        self._acronyms = {
            k: [(iri, kind, label, br) for iri, (kind, label, br) in v.items()]
            for k, v in acronyms.items()
            if len(v) <= _MAX_AMBIGUITY
        }
        self._max_n = max((len(k) for k in self._dict), default=1)

    def __len__(self) -> int:
        return len(self._dict) + len(self._acronyms)

    def tag(self, text: str, limit: int = 50, branch: Optional[str] = None) -> List[dict]:
        """Return concepts mentioned in text, in order of first mention."""
        text = unicodedata.normalize("NFKC", text)
        spans = list(_TOKEN_RE.finditer(text))
        toks = [m.group().casefold() for m in spans]
        found: Dict[str, dict] = {}
        i, n = 0, len(toks)
        while i < n:
            hit, width = None, 1
            for width in range(min(self._max_n, n - i), 0, -1):
                key = tuple(toks[i:i + width])
                hit = self._dict.get(key)
                if not hit:
                    last = _singular(key[-1])
                    if last != key[-1]:
                        hit = self._dict.get(key[:-1] + (last,))
                if hit:
                    break
            if not hit:
                width = 1
                hit = self._acronyms.get(spans[i].group())
            if hit:
                start, end = spans[i].start(), spans[i + width - 1].end()
                surface = text[start:end]
                for iri, kind, label, br in hit:
                    if branch and br != branch:
                        continue
                    entry = found.get(iri)
                    if entry is None:
                        found[iri] = {
                            "iri": iri,
                            "label": label,
                            "branch": br,
                            "match_type": kind,
                            "matched_text": [surface],
                            "count": 1,
                            "first_offset": start,
                        }
                    else:
                        entry["count"] += 1
                        if surface not in entry["matched_text"]:
                            entry["matched_text"].append(surface)
            i += width
        return list(found.values())[:limit]
