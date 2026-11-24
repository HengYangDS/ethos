"""An install leaves safe mode only for a root that native mise reports as trusted."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
import ethos.adapters.toolchain.mise as mise
import ethos.adapters.toolchain.mise_install as mise_install

if TYPE_CHECKING:
    from collections.abc import Mapping

_FILES = {
    mise.MISE_CONFIG: '[tools]\npython = "3.14.10"\n',
    mise.MISE_LOCK: 'lockfile_version = 3\n[[tools.python]]\nversion = "3.14.10"\n',
}
_TRUST_QUERY = ("trust", "--show")
_FOREIGN = {"MISE_SAFE": "0", "MISE_CEILING_PATHS": "/", "MISE_YES": "1"}


class _NativeMise:
    """Stand in for native mise at the process seam: answer the trust query, record the rest."""

    def __init__(self, root: Path, *, trusted: bool) -> None:
        self.answer = f"{root.resolve()}: trusted\n" if trusted else ""
        self.calls: list[tuple[Path, tuple[str, ...], dict[str, str]]] = []

    def __call__(
        self,
        cwd: Path,
        command: tuple[str, ...],
        *,
        env: Mapping[str, str],
        remove_env_prefixes: tuple[str, ...] = (),
        **_options: object,
    ) -> subprocess.CompletedProcess[str]:
        if command[-2:] == _TRUST_QUERY:
            return subprocess.CompletedProcess(command, 0, self.answer, "")
        # Without this the child inherits the caller's own `MISE_*`, a safe mode among them.
        assert remove_env_prefixes == mise.MISE_ENVIRONMENT_PREFIXES
        self.calls.append((cwd, command[1:], dict(env)))
        return subprocess.CompletedProcess(command, 0, "", "")


def _repository(root: Path) -> Path:
    for path, content in _FILES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content, encoding="utf-8")
    return root


@pytest.mark.parametrize("trusted", [False, True])
def test_a_locked_install_leaves_safe_mode_only_for_a_trusted_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, trusted: bool
) -> None:
    """Native mise's own answer for the root decides the mode of the root's own install."""
    root = _repository(tmp_path / "repository")
    native = _NativeMise(root, trusted=trusted)
    monkeypatch.setattr(mise, "run_command", native)
    monkeypatch.setattr(mise_install, "run_command", native)
    # The caller's own safe mode decides nothing: the rule sets or drops it.
    monkeypatch.setenv("MISE_SAFE", "1")
    # A name that looks like an option follows the separator, where mise reads it as a name.
    mise_install.install_locked(root, ("python", "--cd"), executable=Path("mise"), timeout=30)
    ((copy, command, install),) = native.calls
    assert command == ("install", "--locked", "--", "python", "--cd")
    assert install.get("MISE_SAFE") == (None if trusted else "1")
    assert install.get("MISE_TRUSTED_CONFIG_PATHS") == (
        str(copy / mise.MISE_CONFIG) if trusted else None
    )
    assert install["MISE_STATE_DIR"] == str(copy / "state")
    assert install["MISE_CEILING_PATHS"] == str(copy.parent)
    assert install["MISE_LOCKED"] == "1"


@pytest.mark.parametrize("trusted", [False, True])
def test_the_runner_never_leaves_safe_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, trusted: bool
) -> None:
    """`run_mise` has no mode: whatever it is asked to run, an install included, stays safe."""
    root = _repository(tmp_path / "repository")
    native = _NativeMise(root, trusted=trusted)
    monkeypatch.setattr(mise, "run_command", native)
    for arguments in (("which", "python"), ("install", "--locked", "python")):
        mise.run_mise(root, arguments, files=_FILES, executable=Path("mise"))
    assert len(native.calls) == 2
    for copy, _command, environment in native.calls:
        assert environment["MISE_SAFE"] == "1"
        assert environment["MISE_STATE_DIR"] == str(copy / "state")
        assert environment.get("MISE_TRUSTED_CONFIG_PATHS") == (
            str(copy / mise.MISE_CONFIG) if trusted else None
        )


@pytest.mark.parametrize("foreign", [{}, _FOREIGN], ids=["carried-only", "foreign-entries"])
@pytest.mark.parametrize("trusted", [False, True])
def test_the_provisioner_leaves_safe_mode_only_for_a_trusted_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, trusted: bool, foreign: dict[str, str]
) -> None:
    """The provisioner follows the same rule, keeps its state and reads nothing above its root."""
    root = _repository(tmp_path / "repository")
    copy = tmp_path / "cache" / ".prepare-1"
    native = _NativeMise(root, trusted=trusted)
    monkeypatch.setattr(mise, "run_command", native)
    monkeypatch.setattr(native_supply, "run_command", native)
    trust = mise.carried_trust(root, copy, _FILES[mise.MISE_CONFIG], Path("mise"))
    # The mapping is `carried_trust`'s own, as production passes it, or holds foreign entries
    # too: none of those replaces what the provisioner fixes.
    native_supply.download_tool(
        ("mise", "install", "--locked", "node"), root=copy, trust=trust | foreign
    )
    ((_cwd, _command, seen),) = native.calls
    assert seen["MISE_YES"] == "0"
    assert seen.get("MISE_SAFE") == (None if trusted else "1")
    assert seen.get("MISE_TRUSTED_CONFIG_PATHS") == (
        str(copy / mise.MISE_CONFIG) if trusted else None
    )
    assert seen["MISE_STATE_DIR"] == str(copy / "state")
    assert seen["MISE_CEILING_PATHS"] == str(copy.parent)
    assert seen["MISE_LOCKED"] == "1"


def test_an_install_without_trust_is_always_in_safe_mode() -> None:
    """The rule sets safe mode itself; only a carried configuration path lifts it."""
    rule = mise_install.install_mode
    assert rule({"MISE_YES": "0"}) == {"MISE_YES": "0", "MISE_SAFE": "1"}
    unsafe = {"MISE_SAFE": "0", "MISE_YES": "0"}
    assert rule(unsafe) == {"MISE_YES": "0", "MISE_SAFE": "1"}
    assert rule(unsafe | {"MISE_TRUSTED_CONFIG_PATHS": ""}) == {"MISE_YES": "0", "MISE_SAFE": "1"}
    trusted = {"MISE_YES": "0", "MISE_TRUSTED_CONFIG_PATHS": "copy/config.toml"}
    assert rule(trusted | {"MISE_SAFE": "1"}) == trusted
    # Held apart, a trust mapping gives its one key and nothing else.
    apart = {"MISE_TRUSTED_CONFIG_PATHS": "copy/config.toml", "MISE_YES": "1", "MISE_SAFE": "0"}
    assert rule({"MISE_YES": "0", "MISE_SAFE": "1"}, apart) == trusted
    assert rule(trusted, {}) == {"MISE_YES": "0", "MISE_SAFE": "1"}
