"""The canonical text layout that `pre-commit` admits on staged index blobs."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.repo.hook.staged_text as staged_text
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.repository.policy.quality.format_selection import POLICY_PATH
from ethos.repository.release.resources import canonical_resource
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("staged", "unstaged", "gap"),
    [
        ({".gitignore": "\nbuild/\n"}, {}, ".gitignore:1"),
        ({".gitignore": "build/\n\n\n*.log\n"}, {}, ".gitignore:3"),
        ({".gitignore": "build/\n"}, {".gitignore": "\nbuild/\n"}, ""),
        ({"notes.txt": "\n\nfree text\n"}, {}, ""),
    ],
    ids=["leading-blank", "doubled-blank", "worktree-only", "unowned-text"],
)
def test_pre_commit_admits_the_canonical_text_layout(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    staged: dict[str, str],
    unstaged: dict[str, str],
    gap: str,
) -> None:
    """The staged bytes of a canonical-text file decide; other text keeps its own owner."""
    for name, text in staged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert git_process(repo, "add", *staged).returncode == 0
    for name, text in unstaged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (f"pre_commit_text_layout:{gap}" in error) if gap else not error


@pytest.mark.parametrize(
    ("source", "refused"),
    [("", True), ("VALUE = 1\n", True), ('"""Application commands."""\n', False)],
    ids=["empty", "code-first", "docstring"],
)
def test_pre_commit_admits_a_package_marker_only_with_a_docstring(
    repo: Path, capsys: pytest.CaptureFixture[str], *, source: str, refused: bool
) -> None:
    """A staged `__init__.py` states its package's purpose before it is committed."""
    (repo / "app").mkdir()
    (repo / "app/__init__.py").write_text(source, encoding="utf-8")
    assert git_process(repo, "add", "app/__init__.py").returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(refused)
    error = capsys.readouterr().err
    assert ("pre_commit_package_docstring:app/__init__.py" in error) == refused


def test_an_installed_runtime_checks_the_product_repository_with_its_shipped_policy(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The repository keeps the full policy file; the runtime's shipped copy lives elsewhere."""
    shipped = canonical_resource(POLICY_PATH.as_posix())
    installed = tmp_path_factory.mktemp("installed-runtime") / "policy.toml"
    installed.write_bytes(shipped.read_bytes())
    for module in (native_inputs, staged_text):
        monkeypatch.setattr(module, "canonical_resource", lambda _path: installed, raising=False)
    (repo / POLICY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / POLICY_PATH).write_bytes(shipped.read_bytes())
    (repo / ".gitignore").write_text("\nbuild/\n", encoding="utf-8")
    assert git_process(repo, "add", POLICY_PATH.as_posix(), ".gitignore").returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert "pre_commit_text_layout:.gitignore:1" in capsys.readouterr().err
