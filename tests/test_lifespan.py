"""
Session lifecycle of the MCP server's backend.

Under streamable HTTP, FastMCP enters ``app_lifespan`` once per *session*, not
once per process. folio-api injects its in-process graph via
``set_shared_folio``; a session ending must not discard that backend (later
sessions would silently fall back to an APIBackend calling the public REST
API, i.e. the server calling itself through its own rate limiter), and one
session ending must not close a backend other live sessions still use.
"""

import pytest

from folio_mcp import server
from folio_mcp.backends.local import LocalBackend


@pytest.fixture(autouse=True)
def _isolate_server_state(monkeypatch):
    monkeypatch.setattr(server, "_shared_backend", None)
    monkeypatch.setattr(server, "_owned_backend", None, raising=False)
    monkeypatch.setattr(server, "_owned_refs", 0, raising=False)
    monkeypatch.setitem(server._config, "local", False)
    monkeypatch.delenv("FOLIO_MCP_LOCAL", raising=False)


class _StubAPIBackend:
    instances = []

    def __init__(self, base_url=None):
        self.closed = 0
        _StubAPIBackend.instances.append(self)

    async def close(self):
        self.closed += 1


@pytest.fixture
def stub_api_backend(monkeypatch):
    import folio_mcp.backends.api as api_mod

    _StubAPIBackend.instances = []
    monkeypatch.setattr(api_mod, "APIBackend", _StubAPIBackend)
    return _StubAPIBackend


@pytest.mark.asyncio
async def test_injected_backend_survives_session_end(stub_api_backend):
    """folio-api's shared graph must serve every session, not just the first."""
    server.set_shared_folio(object())  # LocalBackend only stores it

    async with server.app_lifespan(None) as first:
        injected = first["backend"]
    async with server.app_lifespan(None) as second:
        assert second["backend"] is injected
    assert isinstance(injected, LocalBackend)
    assert stub_api_backend.instances == [], "fell back to the public REST API"


@pytest.mark.asyncio
async def test_overlapping_sessions_share_and_close_once(stub_api_backend):
    """One session ending must not close the backend another session still uses."""
    a_cm, b_cm = server.app_lifespan(None), server.app_lifespan(None)
    a = await a_cm.__aenter__()
    b = await b_cm.__aenter__()
    assert a["backend"] is b["backend"], "each session built its own backend"
    backend = a["backend"]

    await a_cm.__aexit__(None, None, None)
    assert backend.closed == 0, "closed while session B was still live"

    await b_cm.__aexit__(None, None, None)
    assert backend.closed == 1
    assert len(stub_api_backend.instances) == 1


@pytest.mark.asyncio
async def test_new_backend_after_all_sessions_end(stub_api_backend):
    """After the last session closes the backend, the next session gets a fresh one."""
    async with server.app_lifespan(None) as first:
        pass
    async with server.app_lifespan(None) as second:
        assert second["backend"] is not first["backend"]
        assert second["backend"].closed == 0


@pytest.mark.asyncio
async def test_cancelled_session_still_releases_owned_backend(stub_api_backend):
    """A session cancelled mid-flight (idle timeout, shutdown) must release its ref.

    Without shielding, the lock acquire in the lifespan's finally raises the
    cancellation first, so the count never reaches zero and the backend is
    never closed; the next session then reuses the stale backend.
    """
    import anyio

    entered = anyio.Event()

    async def session():
        async with server.app_lifespan(None):
            entered.set()
            await anyio.sleep_forever()

    async with anyio.create_task_group() as tg:
        tg.start_soon(session)
        await entered.wait()
        tg.cancel_scope.cancel()

    backend = stub_api_backend.instances[0]
    assert server._owned_refs == 0
    assert server._owned_backend is None
    assert backend.closed == 1
