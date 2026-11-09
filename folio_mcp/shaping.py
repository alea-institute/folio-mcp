"""
Input validation and output shaping shared by every tool, independent of backend.

Backends return JSON strings. The tool layer validates and clamps arguments
before calling them, then reshapes their output so both backends give an LLM
the same compact, bounded result:

- compact JSON (no indentation, UTF-8 kept as-is) to save tokens
- result lists cut to the requested ``limit`` (folio-python and the REST API
  both return more search results than asked for)
- long browse lists capped with an explicit ``truncated`` note instead of
  hundreds of kilobytes of JSON
- placeholder definitions ("NULL") dropped and long definitions shortened in
  list views (``get_concept`` always has the full text)
- short, actionable error objects ``{"error": ..., "hint": ...}``
"""

# imports
import json
import re
from typing import Any, Iterable, Optional, Tuple

# project
from folio_mcp.backends._branch_data import BRANCH_NAMES, BRANCH_ROOT_IDS, resolve_branch_name

FOLIO_PREFIX = "https://folio.openlegalstandard.org/"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
MAX_QUERY_LIMIT = 100
MAX_DEPTH = 3
MAX_LIST_ITEMS = 100
MAX_LIST_DEFINITION_CHARS = 300
MAX_QUERY_CHARS = 200

MATCH_MODES = ("substring", "exact", "regex", "fuzzy")

# Short IDs are 22-23 base62-ish characters (some legacy ones contain - or _).
_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{18,30}$")
_PLACEHOLDER_DEFINITIONS = {"", "null", "none", "no definition available"}


def dumps(obj: Any) -> str:
    """Compact JSON for tool output."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def error(message: str, hint: Optional[str] = None, **extra: Any) -> str:
    """A tool-level error object (returned as normal content, never raised)."""
    payload: dict = {"error": message}
    if hint:
        payload["hint"] = hint
    payload.update(extra)
    return dumps(payload)


def clamp(value: Any, low: int, high: int, default: int) -> int:
    """Coerce to int and clamp to at most ``high``; non-numbers and values below
    ``low`` (0, negatives) fall back to ``default``."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < low:
        return default
    return min(high, number)


def looks_like_iri(text: str) -> bool:
    """True for full IRIs and FOLIO short IDs; False for names like 'bankruptcy'."""
    text = text.strip()
    return text.startswith(("http://", "https://")) or bool(_SHORT_ID_RE.match(text) and not text.islower())


def _iri_id(iri: str) -> str:
    """The identifying part of an IRI: its last path or fragment segment."""
    return iri.rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def resolve_iri_argument(iri: Any) -> Tuple[Optional[str], Optional[str]]:
    """Validate an IRI argument. Returns (iri, None) or (None, error_json).

    Branch names ("areas_of_law", "Area of Law") are accepted and mapped to the
    branch's root concept, so get_children("areas_of_law") does the obvious thing.
    """
    text = iri.strip() if isinstance(iri, str) else ""
    if not text:
        return None, error(
            "iri is required.",
            hint="Use search_concepts(query=...) to find a concept's IRI by name.",
        )
    if not text.startswith("http"):
        branch = resolve_branch_name(text)
        if branch is not None:
            return FOLIO_PREFIX + BRANCH_ROOT_IDS[branch], None
    return text, None


def not_found_hint(iri: str) -> str:
    if looks_like_iri(iri):
        return "Check the IRI. Use search_concepts(query=...) to find concepts by name."
    return (
        f"'{iri}' is not a FOLIO IRI. Use search_concepts(query='{iri[:60]}') to find "
        "the concept by name, or list_branches() for branch names."
    )


def _parse(raw: str) -> Tuple[Any, Optional[str]]:
    """Parse backend JSON. Returns (data, passthrough) where passthrough is set on failure."""
    if not isinstance(raw, str):
        return raw, None
    stripped = raw.lstrip()
    if stripped.startswith("<"):
        return None, error("Unexpected non-JSON response from the FOLIO service.")
    try:
        return json.loads(raw), None
    except ValueError:
        return None, raw


def _with_hint(data: dict, iri: Optional[str]) -> str:
    """Re-emit a backend error compactly, adding a hint for not-found IRIs."""
    message = str(data.get("error", "Unknown error"))
    extra = {k: v for k, v in data.items() if k not in ("error", "hint")}
    hint = data.get("hint")
    if hint is None and iri is not None and "not found" in message.lower():
        hint = not_found_hint(iri)
    return error(message, hint=hint, **extra)


def _clean_definition(definition: Any, max_chars: Optional[int]) -> Optional[str]:
    if not isinstance(definition, str):
        return None
    definition = definition.strip()
    if definition.lower() in _PLACEHOLDER_DEFINITIONS:
        return None
    if max_chars and len(definition) > max_chars:
        cut = definition[:max_chars].rsplit(" ", 1)[0]
        return cut.rstrip(" ,;:") + "…"
    return definition


def _clean_item(item: Any, max_definition_chars: Optional[int]) -> Any:
    if not isinstance(item, dict):
        return item
    cleaned = {}
    for key, value in item.items():
        if key == "definition":
            value = _clean_definition(value, max_definition_chars)
        if value is None or value == [] or value == {} or value == "":
            continue
        cleaned[key] = value
    return cleaned


def shape_list(
    raw: str,
    *,
    limit: Optional[int] = None,
    max_items: int = MAX_LIST_ITEMS,
    exclude_iris: Iterable[str] = (),
    iri: Optional[str] = None,
    empty_note: Optional[str] = None,
    truncated_hint: Optional[str] = None,
    max_definition_chars: Optional[int] = MAX_LIST_DEFINITION_CHARS,
) -> str:
    """Shape a backend JSON list result for an LLM (see module docstring)."""
    data, passthrough = _parse(raw)
    if passthrough is not None:
        return passthrough
    if isinstance(data, dict):
        if "error" in data:
            return _with_hint(data, iri)
        return dumps(data)
    if not isinstance(data, list):
        return dumps(data)

    # Compare by ID (last path segment): callers may pass a short ID such as
    # "RCIPwpgRpMs1eVz4vPid0pV" while results carry the full IRI.
    excluded = {_iri_id(x) for x in exclude_iris if x}
    items, seen = [], set()
    for item in data:
        item_iri = item.get("iri") if isinstance(item, dict) else None
        if item_iri is not None:
            item_id = _iri_id(item_iri)
            if item_id in excluded or item_id in seen:
                continue
            seen.add(item_id)
        items.append(_clean_item(item, max_definition_chars))

    if limit is not None:
        items = items[:limit]
    if not items and empty_note:
        return dumps({"results": [], "note": empty_note})
    if len(items) > max_items:
        return dumps({
            "results": items[:max_items],
            "truncated": True,
            "total": len(items),
            "note": truncated_hint or f"Showing the first {max_items} of {len(items)} results.",
        })
    return dumps(items)


def shape_concept(raw: str, iri: str) -> str:
    """Compact a full concept record: drop null/empty fields, keep everything else."""
    data, passthrough = _parse(raw)
    if passthrough is not None:
        return passthrough
    if isinstance(data, dict):
        if "error" in data:
            return _with_hint(data, iri)
        cleaned = _clean_item(data, max_definition_chars=None)
        if cleaned.get("deprecated") is False:
            cleaned.pop("deprecated")
        return dumps(cleaned)
    return dumps(data)


def shape_error_passthrough(raw: str, iri: Optional[str] = None) -> str:
    """For exports (Markdown, XML, JSON-LD): only reshape error objects."""
    if not isinstance(raw, str) or not raw.lstrip().startswith("{"):
        return raw
    try:
        data = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(data, dict) and set(data) <= {"error", "hint"} and "error" in data:
        return _with_hint(data, iri)
    return raw


def validate_query(query: Any, tool: str) -> Optional[str]:
    """Return an error JSON if a free-text search query is unusable."""
    text = query.strip() if isinstance(query, str) else ""
    if not text:
        return error(
            "query must not be empty.",
            hint="Pass a short legal term, e.g. 'noncompete agreement'. "
            "To browse instead, use list_branches() and get_taxonomy_branch().",
        )
    if len(text) > MAX_QUERY_CHARS:
        return error(
            f"query is too long for {tool} ({len(text)} characters; max {MAX_QUERY_CHARS}).",
            hint="Search one short concept name at a time (2-6 words). "
            "Pick the key legal terms from the text and search each separately.",
        )
    return None


def validate_match_mode(match_mode: Any, patterns: Iterable[Optional[str]]) -> Optional[str]:
    """Return an error JSON for an unknown match_mode or an invalid regex."""
    if match_mode not in MATCH_MODES:
        return error(
            f"Unknown match_mode: {match_mode!r}.",
            hint=f"Use one of: {', '.join(MATCH_MODES)}.",
        )
    if match_mode == "regex":
        for pattern in patterns:
            if pattern is None:
                continue
            try:
                re.compile(pattern)
            except re.error as exc:
                return error(
                    f"Invalid regular expression {pattern!r}: {exc}.",
                    hint="Escape special characters, or use match_mode='substring'.",
                )
    return None


def unknown_branch(branch_name: Any) -> str:
    return error(
        f"Unknown branch: {branch_name!r}.",
        hint="Use one of the branch names below (list_branches() shows concept counts).",
        available_branches=BRANCH_NAMES,
    )
