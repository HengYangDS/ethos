"""Project native application operations through a root-bound MCP transport."""

import math
import os
from functools import partial
from pathlib import Path

import anyio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import CallNext
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import FunctionTool
from fastmcp.tools import ToolResult
from mcp.types import CallToolRequestParams
from mcp.types import ToolAnnotations

from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from ethos.domain.plan import plan_repository


class _BoundCalls(Middleware):
    """Keep process identity stable and drain each call before its successor."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.actor = os.environ.get("ETHOS_ACTOR", "")
        self.lock = anyio.Lock()

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        try:
            with anyio.fail_after(self.timeout_seconds):
                async with self.lock:
                    if os.environ.get("ETHOS_ACTOR", "") != self.actor:
                        message = "MCP process identity changed; restart with the intended actor."
                        raise ToolError(message)
                    result = await call_next(context)
                    await anyio.lowlevel.checkpoint()
        except TimeoutError:
            message = "Request deadline exceeded; outcome not acknowledged; observe before retry."
            raise ToolError(message) from None
        else:
            return result


def create_server(root: Path, *, timeout_seconds: float = 180.0) -> FastMCP:
    """Bind one exact repository without granting new authority or storing tasks."""
    if not 0 < timeout_seconds < math.inf:
        message = "MCP timeout must be finite and positive."
        raise ValueError(message)
    target = root.resolve(strict=True)
    server = FastMCP(
        "ETHOS",
        instructions=(
            "This instance is bound to one repository and its startup process actor. "
            "Read status and follow its current continuation. Adoption preview is not "
            "authorization. Review exact inputs before requesting an effect. "
            "Deadlines include queueing; synchronous work drains before completion. "
            "Cancellation or connection loss does not prove rollback: observe before retry."
        ),
        strict_input_validation=True,
        tasks=False,
        mask_error_details=True,
        middleware=[_BoundCalls(timeout_seconds)],
    )
    for name, operation in (
        ("status", inspect_repository),
        ("plan", plan_repository),
        ("adopt", adopt_repository),
    ):
        server.add_tool(
            FunctionTool.from_function(
                partial(operation, target),
                name=name,
                description=operation.__doc__,
                run_in_thread=True,
                annotations=ToolAnnotations(
                    read_only_hint=name in {"status", "plan"}, open_world_hint=False
                ),
            )
        )
    return server
