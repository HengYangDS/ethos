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
_TOKEN = "_LOCKED_INSTALL"


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
    # Any other run keeps safe mode whatever it is asked to run, an install included, and
    # whatever a caller passes in place of the module's own token.
    install = ("install", "--locked", "python")
    mise.run_mise(root, ("which", "python"), files=_FILES, executable=Path("mise"))
    mise.run_mise(root, install, files=_FILES, executable=Path("mise"))
    mise.run_mise(root, install, executable=Path("mise"), install=object())
    (copy, command, install), *resolutions = native.calls
    assert command == ("install", "--locked", "python")
    assert install.get("MISE_SAFE") == (None if trusted else "1")
    assert install.get("MISE_TRUSTED_CONFIG_PATHS") == (
        str(copy / mise.MISE_CONFIG) if trusted else None
    )
    assert install["MISE_STATE_DIR"] == str(copy / "state")
    assert install["MISE_CEILING_PATHS"] == str(copy.parent)
    assert install["MISE_LOCKED"] == "1"
    assert len(resolutions) == 3
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


def _token_references(tree: ast.AST) -> list[tuple[int, str]]:
    """Return each reference to the install token under one node: its line and its kind."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.alias):
            found += [(node.lineno, "import")] if node.name.rpartition(".")[2] == _TOKEN else []
        elif isinstance(node, ast.Constant):
            # The name as a string, bare or as the last part of a dotted or `module:name` path,
            # reaches the token through `getattr`, `attrgetter` or a loader that imports by name.
            text = node.value if isinstance(node.value, str) else ""
            named = text.replace(":", ".").rpartition(".")[2] == _TOKEN and not any(
                character.isspace() for character in text
            )
            found += [(node.lineno, "string")] if named else []
        elif getattr(node, "id", getattr(node, "attr", None)) == _TOKEN:
            found.append((node.lineno, type(node.ctx).__name__.lower()))
    return found


def test_the_install_token_never_leaves_the_mise_adapter() -> None:
    """Only `install_locked` selects an install's mode: the token that does is the module's own."""
    module = "src/ethos/adapters/toolchain/mise.py"
    for path in sorted(p for base in ("src", "tools") for p in (ROOT / base).rglob("*.py")):
        where = path.relative_to(ROOT).as_posix()
        references = _token_references(ast.parse(path.read_text(encoding="utf-8")))
        assert where == module or not references, (where, references)
    tree = ast.parse((ROOT / module).read_text(encoding="utf-8"))
    holders = {
        getattr(top, "name", "<module>"): [kind for _line, kind in _token_references(top)]
        for top in tree.body
        if _token_references(top)
    }
    # Defined once, compared once in the runner, passed once by the entry.
    assert holders == {"<module>": ["store"], "run_mise": ["load"], "install_locked": ["load"]}
    entry = next(top for top in tree.body if getattr(top, "name", "") == "install_locked")
    assert isinstance(entry, ast.FunctionDef)
    # The entry takes no mode, no declarations and nothing it could forward as either.
    assert [argument.arg for argument in entry.args.posonlyargs + entry.args.args] == [
        "root",
        "tools",
    ]
    assert [argument.arg for argument in entry.args.kwonlyargs] == ["executable", "timeout"]
    assert entry.args.vararg is None
    assert entry.args.kwarg is None
    (call,) = (
        node
        for node in ast.walk(entry)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "run_mise"
    )
    assert {keyword.arg for keyword in call.keywords} == {"executable", "timeout", "install"}


def test_the_guard_reads_every_way_to_reach_the_token() -> None:
    """Imports, attribute reads, a rebinding and the name as a string are each reported."""
    sample = (
        "from ethos.adapters.toolchain.mise import _LOCKED_INSTALL\n"
        "from ethos.adapters.toolchain.mise import _LOCKED_INSTALL as token\n"
        "import ethos.adapters.toolchain.mise as mise\n"
        "held = mise._LOCKED_INSTALL\n"
        "found = getattr(mise, '_LOCKED_INSTALL')\n"
        "named = attrgetter('mise._LOCKED_INSTALL')\n"
        "loaded = load('ethos.adapters.toolchain.mise:_LOCKED_INSTALL')\n"
        "mise._LOCKED_INSTALL = held\n"
        "mise.run_mise(root, ('which', 'node'), files=files)\n"
        "note = 'the token _LOCKED_INSTALL stays in its module'\n"
    )
    assert sorted(_token_references(ast.parse(sample))) == [
        (1, "import"),
        (2, "import"),
        (4, "load"),
        (5, "string"),
        (6, "string"),
        (7, "string"),
        (8, "store"),
    ]
