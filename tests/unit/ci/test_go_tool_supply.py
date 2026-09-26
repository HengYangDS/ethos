"""Verify the locked Go toolchain used by native adopter-quality checks."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import tools.ci.toolchain.native as native

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "fault", ["none", "missing-gofmt", "wrong-version", "offline-ready", "offline-missing"]
)
def test_declared_go_enters_native_quality_path_only_after_locked_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    """Go adopter evidence needs the declared toolchain, not an ambient host Go."""
    config = tmp_path / ".config/mise"
    config.mkdir(parents=True)
    (config / "config.toml").write_text('[tools]\ngo = "1.27.1"\n', encoding="utf-8")
    (config / "mise.lock").write_text("lockfile_version = 2\n", encoding="utf-8")
    binary = tmp_path / "mise-data/installs/go/1.27.1/bin"
    binary.mkdir(parents=True)
    go = binary / "go"
    observed = "1.27.0" if fault == "wrong-version" else "1.27.1"
    go.write_text(f"#!/bin/sh\necho 'go version go{observed} fixture/arch'\n")
    go.chmod(0o755)
    if fault != "missing-gofmt":
        gofmt = binary / "gofmt"
        gofmt.write_text("#!/bin/sh\nexit 0\n")
        gofmt.chmod(0o755)
    mise = tmp_path / "mise"
    mise.write_text("#!/bin/sh\nexit 0\n")
    mise.chmod(0o755)
    calls: list[tuple[str, ...]] = []
    if fault.startswith("offline-"):
        monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", str(tmp_path / "supply/input.sha256"))

    def locked_mise(_root: Path, arguments: tuple[str, ...], **_kwargs: object) -> Mock:
        calls.append(arguments)
        output = f"{go}\n" if arguments == ("which", "go") else f"{mise}\n"
        missing = fault == "offline-missing" and arguments == ("which", "go")
        return Mock(
            returncode=1 if missing else 0,
            stdout=output,
            stderr="missing" if missing else "",
        )

    monkeypatch.setattr(native, "prepare_mise", lambda _root: mise)
    monkeypatch.setattr(native, "run_mise", locked_mise)
    monkeypatch.setattr(sys, "argv", ["native", "--root", str(tmp_path), "--mise"])

    assert native.main() == (0 if fault in {"none", "offline-ready"} else 1)
    captured = capsys.readouterr()
    if fault.startswith("offline-"):
        assert not any(command[0] == "install" for command in calls)
    else:
        assert any(command[:2] == ("install", "--locked") and "go" in command for command in calls)
    if fault in {"none", "offline-ready"}:
        assert captured.out.strip().split(os.pathsep) == [str(binary), str(tmp_path)]
    else:
        assert captured.out == ""
        assert "native_tool_supply_failed" in captured.err
