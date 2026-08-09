from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_active_commitment(repo, scope=("module.py", "new.py"))
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


@pytest.mark.parametrize("scope", ["not-a-list", "invalid-toml"])
def test_patch_admission_does_not_invent_scope_from_invalid_commitment(
    tmp_path: Path, scope: str
) -> None:
    repo, _head = _repository(tmp_path)
    carrier = repo / "openspec/changes/fixture-change/commitment.toml"
    if scope == "not-a-list":
        carrier.write_text(carrier.read_text().replace("scope = [", 'scope = "'), encoding="utf-8")
    else:
        carrier.write_text("[invalid\n", encoding="utf-8")
    git(repo, "add", carrier.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "corrupt commitment fixture",
    )
    head = git(repo, "rev-parse", "HEAD")
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
        requested_paths=("new.py",),
        baseline_head=head,
        patch=patch,
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "product_path_not_admitted_at_baseline:new.py"
