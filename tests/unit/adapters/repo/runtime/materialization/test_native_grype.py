"""Grype joins the product's native supply through its platform-scoped Mise declaration."""

from __future__ import annotations

import hashlib
import json
import platform
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.native_supply as native_supply

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "0.121.1"
_URL = "https://github.com/anchore/grype/releases/download/v0.121.1/grype_0.121.1_{}.tar.gz"


def _declared(root: Path, *, scoped: bool = True) -> Path:
    config = root / ".config/mise"
    config.mkdir(parents=True)
    value = f'{{ version = "{_VERSION}", os = ["linux", "macos"] }}' if scoped else f'"{_VERSION}"'
    (config / "config.toml").write_text(f'[tools]\n"github:anchore/grype" = {value}\n')
    rows = "".join(
        f'[tools."github:anchore/grype"."platforms.{target}"]\n'
        f'checksum = "sha256:{hashlib.sha256(target.encode()).hexdigest()}"\n'
        f'url = "{_URL.format(asset)}"\n'
        for target, asset in (("linux-x64", "linux_amd64"), ("macos-arm64", "darwin_arm64"))
    )
    lock = f'lockfile_version = 3\n[[tools."github:anchore/grype"]]\nversion = "{_VERSION}"\n'
    (config / "mise.lock").write_text(lock + rows)
    return root


@pytest.mark.parametrize("scoped", [True, False])
def test_a_platform_scoped_declaration_resolves_its_locked_asset(tmp_path, monkeypatch, scoped):
    """The table form names the same version as the string form; only the hosts it scans lock it."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    supply = native_supply.NativeSupply.read(_declared(tmp_path, scoped=scoped), "grype")
    assert (supply.version, supply.archive) == (_VERSION, "grype_0.121.1_darwin_arm64.tar.gz")
    assert supply.executable_name == "grype"


def test_a_host_outside_the_declared_systems_gets_no_substitute(tmp_path, monkeypatch):
    """Windows on Arm has no Grype build, so the declaration excludes it instead of emulating."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "machine", lambda: "ARM64")
    with pytest.raises(ValueError, match="native_tool_platform_unsupported:grype:windows"):
        native_supply.NativeSupply.read(_declared(tmp_path), "grype")


def test_grype_reports_its_version_as_json(tmp_path, monkeypatch):
    """Grype, like Syft, states its version in JSON, so a stray banner cannot pass verification."""
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    supply = native_supply.NativeSupply.read(_declared(tmp_path), "grype")
    calls = []

    def observed(_cwd, argv, **_options):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({"version": _VERSION}))

    monkeypatch.setattr(native_supply, "run_command", observed)
    supply.verify(tmp_path / "grype")
    assert calls == [(str(tmp_path / "grype"), "version", "-o", "json")]
