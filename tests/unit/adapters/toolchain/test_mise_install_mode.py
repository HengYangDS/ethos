"""An install's safe mode follows the trust that its disposable copy carries."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
import ethos.adapters.toolchain.mise as mise

if TYPE_CHECKING:
    from collections.abc import Mapping

_FILES = {
    mise.MISE_CONFIG: '[tools]\npython = "3.14.10"\n',
    mise.MISE_LOCK: 'lockfile_version = 3\n[[tools.python]]\nversion = "3.14.10"\n',
}


@pytest.mark.parametrize("trusted", [False, True])
def test_a_locked_install_leaves_safe_mode_only_with_the_roots_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, trusted: bool
) -> None:
    """A copy that carries trust installs outside safe mode; resolution never leaves it."""
    root = tmp_path / "repository"
    for path, content in _FILES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content, encoding="utf-8")
    calls: list[tuple[Path, dict[str, str]]] = []

    def native(
        cwd: Path, command: tuple[str, ...], *, env: Mapping[str, str], **_options: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((cwd, dict(env)))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(mise, "_root_trusted", lambda *_arguments: trusted)
    monkeypatch.setattr(mise, "run_command", native)
    # The caller's own safe mode decides nothing here, as before: the carried trust does.
    monkeypatch.setenv("MISE_SAFE", "1")
    for arguments in (("install", "--locked", "python"), ("which", "python")):
        mise.run_mise(root, arguments, files=_FILES, executable=Path("mise"))
    (copy, install), (resolved, resolution) = calls
    assert install.get("MISE_SAFE") == (None if trusted else "1")
    assert install.get("MISE_TRUSTED_CONFIG_PATHS") == (
        str(copy / mise.MISE_CONFIG) if trusted else None
    )
    assert install["MISE_STATE_DIR"] == str(copy / "state")
    assert install["MISE_LOCKED"] == resolution["MISE_SAFE"] == "1"
    assert resolution["MISE_STATE_DIR"] == str(resolved / "state")


@pytest.mark.parametrize("trust", [{}, {"MISE_TRUSTED_CONFIG_PATHS": "copy/config.toml"}])
def test_the_provisioner_leaves_safe_mode_only_with_carried_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trust: dict[str, str]
) -> None:
    """The product's provisioner follows the same rule and keeps mise's state in its root."""
    seen: dict[str, str] = {}

    def native(
        _cwd: Path, command: tuple[str, ...], *, env: Mapping[str, str], **_options: object
    ) -> subprocess.CompletedProcess[str]:
        seen.update(env)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(native_supply, "run_command", native)
    native_supply.download_tool(("mise", "install", "--locked", "node"), root=tmp_path, trust=trust)
    assert seen.get("MISE_SAFE") == (None if trust else "1")
    assert seen["MISE_STATE_DIR"] == str(tmp_path / "state")
    assert seen["MISE_LOCKED"] == "1"
    assert trust.items() <= seen.items()
