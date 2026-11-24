"""An install leaves safe mode only for a root that native mise reports as trusted."""

from __future__ import annotations

import ast
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
_TRUST_QUERY = ("trust", "--show")
ROOT = Path(__file__).resolve().parents[4]
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
    """Native mise's own answer for the root decides the install; resolution never leaves."""
    root = _repository(tmp_path / "repository")
    native = _NativeMise(root, trusted=trusted)
    monkeypatch.setattr(mise, "run_command", native)
    # The caller's own safe mode decides nothing: resolution replaces it and an install drops it.
    monkeypatch.setenv("MISE_SAFE", "1")
    mise.install_locked(root, ("python",), executable=Path("mise"), timeout=30)
    # Resolution keeps safe mode whatever it is asked to run, an install included.
    for arguments in (("which", "python"), ("install", "--locked", "python")):
        mise.run_mise(root, arguments, files=_FILES, executable=Path("mise"))
    (copy, command, install), *resolutions = native.calls
    assert command == ("install", "--locked", "python")
    assert install.get("MISE_SAFE") == (None if trusted else "1")
    assert install.get("MISE_TRUSTED_CONFIG_PATHS") == (
        str(copy / mise.MISE_CONFIG) if trusted else None
    )
    assert install["MISE_STATE_DIR"] == str(copy / "state")
    assert install["MISE_CEILING_PATHS"] == str(copy.parent)
    assert install["MISE_LOCKED"] == "1"
    assert len(resolutions) == 2
    for resolved, _command, resolution in resolutions:
        assert resolution["MISE_SAFE"] == "1"
        assert resolution["MISE_STATE_DIR"] == str(resolved / "state")
        assert resolution.get("MISE_TRUSTED_CONFIG_PATHS") == (
            str(resolved / mise.MISE_CONFIG) if trusted else None
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
    assert mise.install_mode({"MISE_YES": "0"}) == {"MISE_YES": "0", "MISE_SAFE": "1"}
    unsafe = {"MISE_SAFE": "0", "MISE_YES": "0"}
    assert mise.install_mode(unsafe) == {"MISE_YES": "0", "MISE_SAFE": "1"}
    assert mise.install_mode(unsafe | {"MISE_TRUSTED_CONFIG_PATHS": ""}) == {
        "MISE_YES": "0",
        "MISE_SAFE": "1",
    }
    trusted = {"MISE_YES": "0", "MISE_TRUSTED_CONFIG_PATHS": "copy/config.toml"}
    assert mise.install_mode(trusted | {"MISE_SAFE": "1"}) == trusted
    # Held apart, a trust mapping gives its one key and nothing else.
    apart = {"MISE_TRUSTED_CONFIG_PATHS": "copy/config.toml", "MISE_YES": "1", "MISE_SAFE": "0"}
    assert mise.install_mode({"MISE_YES": "0", "MISE_SAFE": "1"}, apart) == trusted
    assert mise.install_mode(trusted, {}) == {"MISE_YES": "0", "MISE_SAFE": "1"}


def _runner_references(path: Path) -> tuple[list[tuple[int, set[str | None]]], list[int]]:
    """Return the direct calls of `run_mise` with their keywords, and every other reference."""
    nodes = list(ast.walk(ast.parse(path.read_text(encoding="utf-8"))))
    calls = {id(node.func): node for node in nodes if isinstance(node, ast.Call)}
    direct: list[tuple[int, set[str | None]]] = []
    other: list[int] = []
    for node in nodes:
        if isinstance(node, ast.alias):
            # A renaming import would hide later calls from the name.
            other += [node.lineno] if node.name == "run_mise" and node.asname else []
        elif isinstance(node, ast.Constant):
            # The bare name as a string reaches the function through `getattr`.
            other += [node.lineno] if node.value == "run_mise" else []
        elif getattr(node, "id", getattr(node, "attr", None)) == "run_mise":
            call = calls.get(id(node))
            if call is None:
                other.append(node.lineno)
            else:
                direct.append((call.lineno, {keyword.arg for keyword in call.keywords}))
    return direct, other


def test_the_install_entry_alone_selects_a_mode_and_passes_no_declarations() -> None:
    """In the product and its tools, `mode` reaches `run_mise` from `install_locked` alone."""
    users: list[tuple[str, int, set[str | None]]] = []
    for path in sorted(p for base in ("src", "tools") for p in (ROOT / base).rglob("*.py")):
        where = path.relative_to(ROOT).as_posix()
        direct, other = _runner_references(path)
        # Passed on, renamed or named by a string, the function could take a mode unseen here.
        assert not other, (where, other)
        # A forwarded `**options` could carry a mode unseen, so it counts as one.
        users += [(where, line, keys) for line, keys in direct if keys & {"mode", None}]
    ((where, line, keywords),) = users
    assert where == "src/ethos/adapters/toolchain/mise.py"
    assert keywords == {"executable", "timeout", "mode"}
    entry = next(
        node
        for node in ast.walk(ast.parse((ROOT / where).read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name == "install_locked"
    )
    assert entry.lineno < line <= (entry.end_lineno or 0)


def test_the_guard_sees_a_runner_that_is_renamed_passed_on_or_named(tmp_path: Path) -> None:
    """Each indirect reference is reported, and a direct call is read with its keywords."""
    source = tmp_path / "caller.py"
    source.write_text(
        "from ethos.adapters.toolchain.mise import run_mise as runner\n"
        "from functools import partial\n"
        "import ethos.adapters.toolchain.mise as mise\n"
        "keep = mise.run_mise\n"
        "bound = partial(run_mise, mode=dict)\n"
        "found = getattr(mise, 'run_mise')\n"
        "mise.run_mise(root, ('which', 'node'), mode=dict, **options)\n",
        encoding="utf-8",
    )
    direct, other = _runner_references(source)
    assert sorted(other) == [1, 4, 5, 6]
    assert direct == [(7, {"mode", None})]
