"""Optional per-tool-call observer, for hosts that want usage telemetry.

Off by default: nothing is recorded unless an embedding host (e.g. folio-api)
calls ``set_tool_observer``. The observer receives the raw call (tool name,
arguments, result text, timing, client name) and is responsible for what, if
anything, it keeps; folio-mcp itself stores nothing.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import FastMCP

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCallEvent:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result_text: str = ""
    duration_s: float = 0.0
    error: str | None = None  # exception class name if the call raised
    client: str | None = None  # MCP clientInfo.name from the initialize handshake


ToolObserver = Callable[[ToolCallEvent], None]
_observer: ToolObserver | None = None


def set_tool_observer(observer: ToolObserver | None) -> None:
    """Register (or clear, with None) the callback invoked after every tool call.

    It runs on the event loop after the result is computed, so it must be cheap,
    and it must not raise (exceptions are logged and swallowed).
    """
    global _observer
    _observer = observer


def _result_text(result: Any) -> str:
    if isinstance(result, tuple):  # (content blocks, structured content)
        result = result[0]
    if isinstance(result, dict):
        return ""
    texts = []
    for block in result or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            texts.append(text)
    return "\n".join(texts)


def _client_name(server: FastMCP) -> str | None:
    try:
        params = server.get_context().session.client_params
        return params.clientInfo.name if params is not None else None
    except Exception:  # noqa: BLE001  # pylint: disable=broad-except
        return None


class ObservableFastMCP(FastMCP):
    """FastMCP whose ``call_tool`` reports each call to the registered observer.

    FastMCP registers its own ``call_tool`` as the protocol handler at
    construction, so overriding the method here covers every tool, including
    ones registered later. With no observer it is a plain pass-through.
    """

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        observer = _observer
        if observer is None:
            return await super().call_tool(name, arguments)
        start = time.perf_counter()
        result: Any = None
        error: str | None = None
        try:
            result = await super().call_tool(name, arguments)
            return result
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            try:
                observer(
                    ToolCallEvent(
                        tool=name,
                        arguments=dict(arguments or {}),
                        result_text=_result_text(result),
                        duration_s=time.perf_counter() - start,
                        error=error,
                        client=_client_name(self),
                    )
                )
            except Exception:  # pylint: disable=broad-except
                LOGGER.warning("tool observer failed", exc_info=True)
