"""
LocalBackend must not block the event loop.

folio-api mounts this server in-process on a single uvicorn worker, so a
synchronous ontology search run directly inside an ``async def`` stalls every
other MCP session, REST request, health check and SSE stream until it ends.
These tests use a stub graph whose calls block, so they need no ontology.

Limitation: the stub blocks with time.sleep, which releases the GIL. The real
label/definition searches spend their time in rapidfuzz.process.extract, a
single C call that holds the GIL, so for those two tools the offload does
NOT free the event loop (measured: ~2.9 s worst stall for 20 searches either
way). These tests cover the pure-Python tools (query_concepts, traversals)
and guard against regressing to inline calls. Freeing the loop during fuzzy
search needs a GIL-releasing search in folio-python, e.g.
rapidfuzz.process.cdist(..., workers=N).
"""

import asyncio
import json
import threading
import time
from types import SimpleNamespace

import pytest

from folio_mcp.backends.local import LocalBackend

BLOCK_S = 0.4


class _BlockingFolio:
    """Stub FOLIO whose search blocks the calling thread, like a CPU-bound search."""

    def __init__(self):
        self.threads = []

    def search_by_label(self, query, limit=10):
        self.threads.append(threading.current_thread())
        time.sleep(BLOCK_S)
        return [(SimpleNamespace(iri="X1", label=query, definition=None), 99.0)]

    search_by_definition = search_by_label


async def _ticks_during(coro, interval=0.01):
    """Run coro while counting how often a concurrent ticker gets the loop."""
    ticks = 0
    done = asyncio.Event()

    async def ticker():
        nonlocal ticks
        while not done.is_set():
            await asyncio.sleep(interval)
            ticks += 1

    task = asyncio.create_task(ticker())
    try:
        result = await coro
    finally:
        done.set()
        await task
    return result, ticks


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["search_by_label", "search_by_definition"])
async def test_search_does_not_block_event_loop(method):
    folio = _BlockingFolio()
    backend = LocalBackend(folio)

    result, ticks = await _ticks_during(getattr(backend, method)("contract", 5))

    assert json.loads(result)[0]["label"] == "contract"
    # A blocked loop yields ~0 ticks; a free one ~BLOCK_S / 0.01 = 40.
    assert ticks >= 10, f"event loop starved: only {ticks} ticks in {BLOCK_S}s"
    assert folio.threads and folio.threads[0] is not threading.main_thread()


@pytest.mark.asyncio
async def test_concurrent_searches_overlap():
    """Several blocking searches run concurrently, not one after another."""
    backend = LocalBackend(_BlockingFolio())

    start = time.perf_counter()
    await asyncio.gather(*(backend.search_by_label(f"q{i}", 5) for i in range(4)))
    elapsed = time.perf_counter() - start

    assert elapsed < BLOCK_S * 2.5, f"searches serialized: {elapsed:.2f}s for 4 x {BLOCK_S}s"
