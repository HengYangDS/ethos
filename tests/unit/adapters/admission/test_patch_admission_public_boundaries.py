from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission
from ethos.adapters.admission.patch_admission import patch_admission
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path, *, scope: tuple[str, ...] = ("safe.txt",)) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "safe.txt").write_text("old\n", encoding="utf-8")
    commit_active_commitment(repo, scope=scope)
    return repo, git(repo, "rev-parse", "HEAD")


def _patch(old: str, new: str, body: str = "+value\n") -> str:
    return f"diff --git a/{old} b/{new}\n--- a/{old}\n+++ b/{new}\n@@ -0,0 +1 @@\n{body}"


def _change_patch() -> str:
    return (
        "diff --git a/safe.txt b/safe.txt\n"
        "--- a/safe.txt\n"
        "+++ b/safe.txt\n"
        "@@ -1 +1,2 @@\n"
        " old\n"
        "+value\n"
    )


@pytest.mark.parametrize("old", ["/absolute", "../escape"])
def test_patch_admission_rejects_absolute_and_escaping_preimages(tmp_path: Path, old: str) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_patch(old, "safe.txt"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_rejects_missing_preimage(tmp_path: Path) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_patch("missing.txt", "safe.txt"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_rejects_escaping_postimage(tmp_path: Path) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("../escape",),
        baseline_head=head,
        patch=_patch("safe.txt", "../escape"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_rejects_nonlist_scope(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    carrier = repo / "openspec/changes/fixture-change/commitment.toml"
    carrier.write_text(carrier.read_text().replace('scope = ["safe.txt"]', 'scope = "safe.txt"'))
    git(repo, "add", carrier.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "corrupt scope",
    )
    head = git(repo, "rev-parse", "HEAD")

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_change_patch(),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_postimage_failed"


def test_patch_admission_reports_failed_postimage_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repository(tmp_path)
    calls = 0

    real_run = admission.run_git

    def fail_second_apply(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        completed = real_run(*args, **kwargs)
        return completed if calls == 1 else completed.__class__(completed.args, 1, "", "")

    monkeypatch.setattr(admission, "run_git", fail_second_apply)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_change_patch(),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_postimage_failed"
