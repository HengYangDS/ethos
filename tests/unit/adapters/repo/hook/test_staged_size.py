"""The per-file code ceiling that `pre-commit` admits on staged index blobs."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.admission as hook_runtime
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path

_CEILING = load_repository_paradigm().parameter_defaults("size")["code_effective_lines"]
_LOWERED = "[paradigm.size]\ncode_effective_lines = 400\n"


def _python(count: int) -> str:
    return "".join(f"value_{index} = {index}\n" for index in range(count))


def _javascript(count: int) -> str:
    return "".join(f"const value_{index} = {index};\n" for index in range(count))


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an empty repository whose `pre-commit` runs only its staged content checks."""
    assert git_process(tmp_path, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.prewrite_guard", lambda **_kwargs: {"verdict": "pass"}
    )
    return tmp_path


@pytest.mark.parametrize(
    ("staged", "unstaged", "gap"),
    [
        ({"module.py": _python(_CEILING + 1)}, {}, f"module.py:{_CEILING + 1}>{_CEILING}"),
        ({"module.js": _javascript(_CEILING + 1)}, {}, f"module.js:{_CEILING + 1}>{_CEILING}"),
        ({"module.py": _python(_CEILING)}, {"module.py": _python(_CEILING + 1)}, ""),
        ({"module.py": _python(401)}, {".ethos/rules.toml": _LOWERED}, "module.py:401>400"),
        (
            {
                ".gitattributes": "module.py linguist-generated\n",
                "module.py": _python(_CEILING + 1),
            },
            {},
            "",
        ),
    ],
    ids=["over", "lexed", "worktree-only", "bound-ceiling", "received"],
)
def test_pre_commit_admits_the_code_ceiling_on_staged_blobs(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    staged: dict[str, str],
    unstaged: dict[str, str],
    gap: str,
) -> None:
    """The staged bytes decide, under the paradigm report's measure and resolved ceiling."""
    for name, text in staged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert git_process(repo, "add", *staged).returncode == 0
    for name, text in unstaged.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (f"pre_commit_code_size_exceeded:{gap}" in error) if gap else not error


@pytest.mark.parametrize("mode", ["120000", "160000"], ids=["symlink", "submodule"])
def test_pre_commit_measures_only_regular_files(
    repo: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    """A staged symlink or gitlink holds no source of its own, so its object is never measured."""
    stored = git_process(repo, "hash-object", "-w", "--stdin", stdin=_javascript(_CEILING + 1))
    entry = f"{mode},{stored.stdout.strip()},vendored.js"
    assert git_process(repo, "update-index", "--add", "--cacheinfo", entry).returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 0
    assert not capsys.readouterr().err


def test_pre_commit_refuses_a_staged_source_it_cannot_measure(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Undecodable staged source is refused, as the paradigm report refuses it in the worktree."""
    (repo / "module.js").write_bytes(b"const value = '\xff';\n")
    assert git_process(repo, "add", "module.js").returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert "pre_commit_code_size_unmeasurable:module.js" in capsys.readouterr().err
