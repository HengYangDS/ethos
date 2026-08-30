from __future__ import annotations

from pathlib import Path

import pytest

from tools.ci.toolchain.node import node_runtime


def _supply(root: Path, node: Path) -> Path:
    executable = root / node
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(b"node")
    executable.chmod(0o755)
    npm_cli = root / "lib/node_modules/npm/bin/npm-cli.js"
    npm_cli.parent.mkdir(parents=True)
    npm_cli.write_bytes(b"npm")
    return npm_cli


@pytest.mark.parametrize(
    ("platform_name", "node_relative"),
    [("posix", Path("bin/node")), ("nt", Path("node.exe"))],
)
def test_node_runtime_resolves_the_installed_platform_layout(
    tmp_path: Path, platform_name: str, node_relative: Path
) -> None:
    npm_cli = _supply(tmp_path, node_relative)

    node, resolved_npm = node_runtime(package_root=tmp_path, platform_name=platform_name)

    assert node == tmp_path / node_relative
    assert resolved_npm == npm_cli


def test_node_runtime_fails_before_build_for_an_incomplete_supply(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="package-local Node executable is unavailable"):
        node_runtime(package_root=tmp_path, platform_name="nt")
