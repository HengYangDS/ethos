from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import reconciliation_receipt_payload
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def test_new_submit_push_reconciles_divergent_origin_and_github_identity_baselines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Legacy User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "legacy@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Legacy User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "legacy@example.invalid")
    (repo / "legacy.txt").write_text("legacy\n", encoding="utf-8")
    git(repo, "add", "legacy.txt")
    git(repo, "commit", "-m", "legacy history")
    legacy_head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/github/dev", legacy_head)
    git(repo, "checkout", "-b", "origin-source", "HEAD~1")
    (repo / "origin.txt").write_text("origin\n", encoding="utf-8")
    git(repo, "add", "origin.txt")
    git(repo, "commit", "-m", "origin history")
    origin_head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/dev", origin_head)
    git(repo, "checkout", "dev")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Canonical User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "canonical@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Canonical User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "canonical@example.invalid")
    (repo / "carrier.txt").write_text("carrier\n", encoding="utf-8")
    git(repo, "add", "carrier.txt")
    git(repo, "commit", "-m", "reconciliation carrier")
    pushed_head = git(repo, "rev-parse", "HEAD")
    receipt_path = tmp_path / "dual-remote-reconciliation.json"
    receipt_path.write_text(
        json.dumps(
            reconciliation_receipt_payload(
                submit_branch="submit/dual-remote-reconciliation",
                source_head=pushed_head,
                origin_head=origin_head,
                github_head=legacy_head,
            )
        ),
        encoding="utf-8",
    )

    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/submit/dual-remote-reconciliation",
        pushed_head=pushed_head,
        remote_head="0" * 40,
        reconciliation=ReconciliationObservation(
            receipt_path=receipt_path.as_posix(),
            origin_head=origin_head,
            github_head=legacy_head,
        ),
    )

    identity = report["identity_policy"]
    assert identity["ok"] is True
    assert identity["checked_commit_count"] == 1
    assert identity["violations"] == []


def test_new_submit_push_blocks_divergence_without_an_exact_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    git(repo, "checkout", "-b", "origin-source")
    (repo / "origin.txt").write_text("origin\n", encoding="utf-8")
    git(repo, "add", "origin.txt")
    git(repo, "commit", "-m", "origin history")
    git(repo, "update-ref", "refs/remotes/origin/dev", "HEAD")
    git(repo, "checkout", "dev")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Canonical User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "canonical@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Canonical User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "canonical@example.invalid")
    (repo / "carrier.txt").write_text("carrier\n", encoding="utf-8")
    git(repo, "add", "carrier.txt")
    git(repo, "commit", "-m", "reconciliation carrier")
    pushed_head = git(repo, "rev-parse", "HEAD")

    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/submit/dual-remote-reconciliation",
        pushed_head=pushed_head,
        remote_head="0" * 40,
    )

    identity = report["identity_policy"]
    assert identity["ok"] is False
    assert "push_identity_reconciliation_receipt_required" in identity["required_gaps"]


def test_new_submit_push_blocks_reconciliation_receipt_when_remote_observation_is_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    git(repo, "checkout", "-b", "origin-source")
    (repo / "origin.txt").write_text("origin\n", encoding="utf-8")
    git(repo, "add", "origin.txt")
    git(repo, "commit", "-m", "origin history")
    origin_head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/dev", origin_head)
    git(repo, "checkout", "dev")
    (repo / "github.txt").write_text("github\n", encoding="utf-8")
    git(repo, "add", "github.txt")
    git(repo, "commit", "-m", "github history")
    github_head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/github/dev", github_head)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Canonical User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "canonical@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Canonical User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "canonical@example.invalid")
    (repo / "carrier.txt").write_text("carrier\n", encoding="utf-8")
    git(repo, "add", "carrier.txt")
    git(repo, "commit", "-m", "reconciliation carrier")
    pushed_head = git(repo, "rev-parse", "HEAD")
    receipt_path = tmp_path / "stale-reconciliation.json"
    receipt_path.write_text(
        json.dumps(
            reconciliation_receipt_payload(
                submit_branch="submit/dual-remote-reconciliation",
                source_head=pushed_head,
                origin_head=origin_head,
                github_head=github_head,
            )
        ),
        encoding="utf-8",
    )

    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/submit/dual-remote-reconciliation",
        pushed_head=pushed_head,
        remote_head="0" * 40,
        reconciliation=ReconciliationObservation(
            receipt_path=receipt_path.as_posix(),
            origin_head="different-head",
            github_head=github_head,
        ),
    )

    assert report["identity_policy"]["ok"] is False
    assert (
        "push_identity_reconciliation_origin_head_stale"
        in report["identity_policy"]["required_gaps"]
    )
