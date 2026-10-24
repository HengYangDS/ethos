"""Own native Mise storage for the toolchain adapter tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def mise_installs(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Callable[[str, str, str], None]:
    """Own native Mise storage; each install reports its version, so no host install is used."""
    data = tmp_path_factory.mktemp("mise-data")
    monkeypatch.setenv("MISE_DATA_DIR", str(data))

    def install(tool: str, version: str, report: str) -> None:
        executable = data / "installs" / tool / version / "bin" / tool
        executable.parent.mkdir(parents=True)
        executable.write_text(f"#!/bin/sh\necho {report}\n", encoding="utf-8", newline="\n")
        executable.chmod(0o755)

    return install
