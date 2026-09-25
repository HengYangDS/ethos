"""Launch the installed root-bound MCP transport without eager framework loading."""

from importlib import import_module

from ethos.surface.cli.application import app
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def mcp(*, root: RootOption, create_target: bool = False) -> None:
    """Serve one existing repository or explicit absent formation target."""
    selected = root.absolute() if create_target else resolve_root(root)
    server = import_module("ethos.surface.mcp.server").create_server(
        selected, create_target=create_target
    )
    server.run(transport="stdio", show_banner=False)
