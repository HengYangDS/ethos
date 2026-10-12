"""Reject escaping patch preimages and expose materialization failures."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission
from ethos.adapters.admission.patch_admission import patch_admission
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "safe.txt").write_text("old\n", encoding="utf-8")
    commit_active_change(repo)
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
    assert report["reference_coverage"] == "not_evaluated"


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


@pytest.mark.parametrize("relative", ["native space.txt", "native-é.txt", 'native "quote".txt'])
def test_original_git_quoted_patch_retains_literal_path(tmp_path: Path, relative: str) -> None:
    repo, head = _repository(tmp_path)
    source = repo / relative
    source.write_text("old\n")
    git(repo, "add", relative)
    source.write_text("old\nnew\n")
    patch = admission.run_git(repo, "-c", "core.quotePath=true", "diff", "--", relative).stdout
    source.write_text("old\n")
    report = patch_admission(
        root=repo, requested_paths=(relative,), baseline_head=head, patch=patch
    )
    assert report["verdict"] == "pass", report
    assert report["paths"] == [relative]
    assert source.read_text() == "old\n"


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


def test_patch_admission_reports_failed_postimage_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repository(tmp_path)
    calls = 0

    real_run = admission.run_git

    def fail_second_apply(root: Path, *args: str, **kwargs):
        nonlocal calls
        completed = real_run(root, *args, **kwargs)
        if args[:1] != ("apply",) or "--numstat" in args:
            return completed
        calls += 1
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
    assert report["reference_coverage"] == "not_evaluated"


def test_patch_admission_does_not_claim_unrequested_observation(tmp_path: Path) -> None:
    """No requested patch means no reference observation was evaluated."""
    repo, head = _repository(tmp_path)

    report = patch_admission(root=repo, requested_paths=(), baseline_head=head, patch="")

    assert report["verdict"] == "pass"
    assert report["state"] == "not_requested"
    assert report["reference_coverage"] == "not_evaluated"
    assert report["uncertainties"] == []


@pytest.mark.parametrize(
    ("source", "verdict", "coverage", "state"),
    [
        (
            "import subprocess\ndef launch(command):\n    subprocess.run(command)\n",
            "pass",
            "partial",
            "deferred",
        ),
        (
            'import subprocess\ngetattr(subprocess, selector)(["probe"])\n',
            "unknown",
            "unknown",
            "unknown",
        ),
    ],
)
def test_patch_admission_preserves_reference_observation(
    tmp_path: Path, source: str, verdict: str, coverage: str, state: str
) -> None:
    """Admission retains deferred and unknown sites instead of flattening them away."""
    repo, head = _repository(tmp_path)
    path = "src/probe.py"
    patch = f"diff --git a/{path} b/{path}\nnew file mode 100644\n" + "".join(
        difflib.unified_diff(
            [], source.splitlines(keepends=True), fromfile="/dev/null", tofile=f"b/{path}"
        )
    )

    report = patch_admission(root=repo, requested_paths=(path,), baseline_head=head, patch=patch)

    assert report["verdict"] == verdict, report
    assert report["reference_coverage"] == coverage, report
    residuals = report["uncertainties"]
    assert isinstance(residuals, list)
    assert len(residuals) == 1
    assert residuals[0]["state"] == state
    assert residuals[0]["kind"] == "executable"
    assert residuals[0]["path"] == path
