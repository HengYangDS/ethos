"""Launch the installed root-bound MCP transport without eager framework loading."""

from importlib import import_module

from ethos.surface.cli.application import app
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def mcp(*, root: RootOption) -> None:
    """Serve native ETHOS operations over stdio for one explicit repository."""
    server = import_module("ethos.surface.mcp.server").create_server(resolve_root(root))
    server.run(transport="stdio", show_banner=False)
