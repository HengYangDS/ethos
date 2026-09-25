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
from ethos.domain.land.operation import land_repository
from ethos.domain.plan import plan_repository
from ethos.domain.publication.operation import publish_repository


class _BoundCalls(Middleware):
    """Keep process identity stable and drain each call before its successor."""

    def __init__(
        self, timeout_seconds: float, *, target_binding: tuple[Path, Path] | None = None
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.actor = os.environ.get("ETHOS_ACTOR", "")
        self.target_binding = target_binding
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
                    if self.target_binding is not None:
                        requested, physical = self.target_binding
                        try:
                            current = requested.resolve(strict=False)
                        except (OSError, RuntimeError) as error:
                            message = (
                                "MCP target binding unavailable; restart with the intended root."
                            )
                            raise ToolError(message) from error
                        if current != physical:
                            message = "MCP target binding changed; restart with the intended root."
                            raise ToolError(message)
                    result = await call_next(context)
                    await anyio.lowlevel.checkpoint()
        except TimeoutError:
            message = "Request deadline exceeded; outcome not acknowledged; observe before retry."
            raise ToolError(message) from None
        else:
            return result


def create_server(
    root: Path, *, create_target: bool = False, timeout_seconds: float = 180.0
) -> FastMCP:
    """Bind one repository or an explicit absent formation target without effects."""
    if not 0 < timeout_seconds < math.inf:
        message = "MCP timeout must be finite and positive."
        raise ValueError(message)
    if create_target:
        requested = root.absolute()
        try:
            parent = requested.parent.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            message = "formation_parent_unsafe"
            raise ValueError(message) from error
        if not parent.is_dir():
            message = "formation_parent_unsafe"
            raise ValueError(message)
        physical = parent / requested.name
        if (
            requested.exists()
            or requested.is_symlink()
            or physical.exists()
            or physical.is_symlink()
        ):
            message = "formation_target_exists"
            raise ValueError(message)
        target = requested
        target_binding = (requested, physical)
    else:
        try:
            target = root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            message = "mcp_root_unavailable"
            raise ValueError(message) from error
        target_binding = None
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
        middleware=[_BoundCalls(timeout_seconds, target_binding=target_binding)],
    )
    for name, operation in (
        ("status", inspect_repository),
        ("plan", plan_repository),
        ("adopt", adopt_repository),
        ("land", land_repository),
        ("publish", publish_repository),
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
