"""Guard the mcp dependency against an unbounded major version.

folio_mcp.server imports mcp.server.fastmcp, which mcp 2.x removed. Until the
server is ported to the 2.x API, the declared requirement must exclude 2.x.
"""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from packaging.requirements import Requirement
from packaging.version import Version

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _mcp_requirement() -> Requirement:
    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    matches = [Requirement(d) for d in deps if Requirement(d).name == "mcp"]
    assert len(matches) == 1, f"expected exactly one mcp requirement, got {deps}"
    return matches[0]


def test_mcp_requirement_excludes_major_2_and_above():
    spec = _mcp_requirement().specifier
    for v in ("2.0.0", "2.0.0rc1", "2.5.1", "3.0.0"):
        assert not spec.contains(Version(v), prereleases=True), f"mcp spec {spec} allows {v}"


def test_mcp_requirement_allows_supported_1x():
    spec = _mcp_requirement().specifier
    assert spec.contains(Version("1.26.0"))
