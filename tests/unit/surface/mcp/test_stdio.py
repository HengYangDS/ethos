"""Run the shared installed-conformance workload against source without duplicating cases."""

import sys

from tools.ci.delivery.acceptance.mcp import verify


def test_stdio_discovery_adoption_and_reconnect(tmp_path):
    """Effects, refusals and reconnect must agree through all supported transports."""
    result = verify((sys.executable, "-B", "-m", "ethos.cli"), tmp_path)
    assert result["state"] == "passed"
    assert result["mutation_surfaces"] == ["cli", "sdk", "mcp"]
    assert result["owned_work_removed"]
