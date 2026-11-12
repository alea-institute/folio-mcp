"""The optional tool-call observer used by hosts for usage telemetry.

Runs real MCP calls over the SDK's in-memory transport against the real graph.
"""

import json

import pytest
from mcp import types
from mcp.shared.memory import create_connected_server_and_client_session

from folio_mcp import server
from folio_mcp.observer import set_tool_observer


@pytest.fixture
def shared_graph(folio_graph, monkeypatch):
    from folio_mcp.backends.local import LocalBackend

    monkeypatch.setattr(server, "_shared_backend", LocalBackend(folio_graph))
    yield
    set_tool_observer(None)


async def _call(tool, args, client_name="telemetry-test"):
    async with create_connected_server_and_client_session(
        server.mcp, client_info=types.Implementation(name=client_name, version="0")
    ) as client:
        return await client.call_tool(tool, args)


@pytest.mark.asyncio
async def test_observer_receives_each_call(shared_graph):
    events = []
    set_tool_observer(events.append)

    result = await _call("search_concepts", {"query": "breach of contract", "limit": 3})

    assert not result.isError
    assert len(events) == 1
    event = events[0]
    assert event.tool == "search_concepts"
    assert event.arguments == {"query": "breach of contract", "limit": 3}
    assert event.client == "telemetry-test"
    assert event.error is None and event.duration_s >= 0
    assert [r["label"] for r in json.loads(event.result_text)][:1] == [
        "Breach of Contract"
    ]


@pytest.mark.asyncio
async def test_failing_observer_does_not_break_the_call(shared_graph):
    def boom(_event):
        raise RuntimeError("observer bug")

    set_tool_observer(boom)
    result = await _call("search_concepts", {"query": "negligence", "limit": 2})
    assert not result.isError
    assert json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_unknown_tool_is_reported_as_error(shared_graph):
    events = []
    set_tool_observer(events.append)
    result = await _call("no_such_tool", {})
    assert result.isError
    assert events and events[0].tool == "no_such_tool" and events[0].error


@pytest.mark.asyncio
async def test_no_observer_is_a_pass_through(shared_graph):
    set_tool_observer(None)
    result = await _call("list_branches", {})
    assert not result.isError
