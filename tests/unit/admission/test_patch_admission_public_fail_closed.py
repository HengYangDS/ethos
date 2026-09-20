"""Reject unverifiable patch state and preserve exact source admission."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission
from ethos.repository.policy.references.observation import deleted_input_gaps
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_active_change(repo)
    return repo, git(repo, "rev-parse", "HEAD")


def _patch(repo: Path, path: str = "module.py", content: str = "VALUE = 2\n") -> str:
    target = repo / path
    original = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(content, encoding="utf-8")
    patch = git(repo, "diff", "--no-ext-diff", "--", path)
    if original is None:
        target.unlink()
    else:
        target.write_text(original, encoding="utf-8")
    return f"{patch}\n"


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("path-mismatch", "prewrite_patch_paths_mismatch"),
        ("baseline-missing", "prewrite_patch_baseline_missing"),
        ("preimage-mismatch", "prewrite_patch_preimage_mismatch"),
        ("binary", "prewrite_patch_binary_unsupported"),
        ("quoted-header", "prewrite_patch_invalid"),
        ("short-header", "prewrite_patch_invalid"),
        ("no-change", "prewrite_patch_invalid"),
    ],
)
def test_patch_admission_rejects_unverifiable_patch_state(
    tmp_path: Path, case: str, expected: str
) -> None:
    repo, head = _repository(tmp_path)
    patch = _patch(repo)
    requested = ("module.py",)
    if case == "path-mismatch":
        requested = ("new.py",)
    elif case == "baseline-missing":
        head = ""
    elif case == "preimage-mismatch":
        patch = patch.replace("VALUE = 1", "VALUE = 0")
    elif case == "binary":
        patch = "diff --git a/module.py b/module.py\nGIT binary patch\n"
    elif case == "quoted-header":
        patch = 'diff --git "a/module.py b/module.py\n'
    elif case == "short-header":
        patch = "diff --git a/module.py\n"
    elif case == "no-change":
        patch = "not a unified patch\n"

    report = admission.patch_admission(
        root=repo,
        requested_paths=requested,
        baseline_head=head,
        patch=patch,
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["reason"] == expected


def test_patch_admission_blocks_when_postimage_reference_observation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repository(tmp_path)

    def unavailable(*_args: object, **_kwargs: object) -> dict[str, set[str]]:
        message = "reference observer unavailable"
        raise OSError(message)

    monkeypatch.setattr(admission, "product_references_from_files", unavailable)
    report = admission.patch_admission(
        root=repo,
        requested_paths=("module.py",),
        baseline_head=head,
        patch=_patch(repo),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_postimage_failed"
    assert report["references"] == {}


def test_patch_admission_accepts_new_file_with_exact_preimage_and_reference_closure(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo)
    head = git(repo, "rev-parse", "HEAD")
    path = "new.py"
    patch = (
        "diff --git a/new.py b/new.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/new.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
    )

    report = admission.patch_admission(
        root=repo,
        requested_paths=(path,),
        baseline_head=head,
        patch=patch,
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "admitted"


@pytest.mark.parametrize("change", ["body", "new-command", "prefix", "delete-app", "retire"])
def test_patch_command_ownership_uses_exact_unchanged_context(tmp_path, change) -> None:
    """Changes retain imported namespaces but cannot inherit deleted or stale parents."""
    repo, _head = _repository(tmp_path)
    files = {
        "pyproject.toml": '[project]\nname="example"\nversion="1"\ndependencies=["cyclopts"]\n',
        "src/example/app.py": 'from cyclopts import App\napp = App(name="ethos")\n',
        "src/example/commands.py": (
            "from example.app import app as cli\n@cli.command\ndef status():\n    return 1\n"
        ),
    }
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare command context")
    head = git(repo, "rev-parse", "HEAD")
    handler = "src/example/commands.py"
    app = "src/example/app.py"
    target = repo / handler
    target.write_text(
        files[handler].replace(
            "status" if change == "new-command" else "return 1",
            "other" if change == "new-command" else "return 2",
        )
    )
    paths = (handler, app) if change in {"prefix", "delete-app", "retire"} else (handler,)
    if change == "prefix":
        (repo / app).write_text(files[app].replace("ethos", "different"))
    elif change in {"delete-app", "retire"}:
        (repo / app).unlink()
        if change == "retire":
            target.unlink()
    patch = git(repo, "diff", "--", *paths) + "\n"
    for relative in paths:
        (repo / relative).write_text(files[relative])
    report = admission.patch_admission(
        root=repo, requested_paths=paths, baseline_head=head, patch=patch
    )
    assert report["verdict"] == ("block" if change == "delete-app" else "pass")
    assert not report["references"].get("command")
    if change == "delete-app":
        assert report["reason"] == "deleted_input:src/example/app.py:src/example/commands.py:import"


@pytest.mark.parametrize(
    ("source", "path", "replacement", "expected"),
    [
        ("import pkg.owner as local", "consumer.py", False, "block"),
        ("from pkg import owner", "consumer.py", False, "block"),
        ("from .owner import item", "consumer.py", False, "block"),
        ("from . import owner", "consumer.py", False, "block"),
        ("from . import owner", "__init__.py", False, "block"),
        ("VALUE = 1", "consumer.py", False, "pass"),
        ("def invalid(:", "consumer.py", False, "unknown"),
        ("import pkg.owner", "consumer.py", True, "pass"),
    ],
)
def test_deleted_python_input_retains_import_identity(source, path, replacement, expected):
    files = {f"src/pkg/{path}": source}
    if replacement:
        files["src/pkg/owner/__init__.py"] = ""
    gaps, unknown = deleted_input_gaps(files, frozenset({"src/pkg/owner.py"}))
    assert bool(gaps) is (expected == "block")
    assert bool(unknown) is (expected == "unknown")
