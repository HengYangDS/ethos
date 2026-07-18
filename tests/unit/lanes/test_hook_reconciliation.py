from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from ethos.adapters.admission import identity as admission_identity
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import reconciliation_receipt_payload
from ethos.surface.cli.hook.core import reconciliation_receipt_command
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
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


def test_reconciliation_receipt_command_records_exact_tracking_observation(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    origin_head = git(repo, "rev-parse", "HEAD")
    github_head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/dev", origin_head)
    git(repo, "update-ref", "refs/remotes/github/dev", github_head)
    receipt_path = tmp_path / "dual-remote-reconciliation.json"

    payload = run_ethos(
        "hook",
        "reconciliation-receipt",
        "submit/dual-remote-reconciliation",
        origin_head,
        "--write-receipt",
        receipt_path.as_posix(),
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "observed"
    assert payload["data"]["receipt"] == reconciliation_receipt_payload(
        submit_branch="submit/dual-remote-reconciliation",
        source_head=origin_head,
        origin_head=origin_head,
        github_head=github_head,
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == payload["data"]["receipt"]


def test_reconciliation_receipt_command_blocks_missing_tracking_refs(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    receipt_path = tmp_path / "dual-remote-reconciliation.json"

    payload = run_ethos_blocked(
        "hook",
        "reconciliation-receipt",
        "submit/dual-remote-reconciliation",
        git(repo, "rev-parse", "HEAD"),
        "--write-receipt",
        receipt_path.as_posix(),
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [
        "reconciliation_origin_tracking_missing",
        "reconciliation_github_tracking_missing",
    ]
    assert not receipt_path.exists()


def test_reconciliation_receipt_command_rejects_repository_local_output(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    receipt_path = repo / "submit-reconciliation.json"

    with pytest.raises(ValueError, match="outside the repository root"):
        reconciliation_receipt_command(
            "submit/dual-remote-reconciliation",
            git(repo, "rev-parse", "HEAD"),
            write_receipt=receipt_path,
            root=repo,
        )


def test_reconciliation_receipt_helpers_reject_invalid_observations(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    missing_head = "f" * 40
    receipt_path = tmp_path / "invalid-reconciliation.json"
    receipt_path.write_text("not-json", encoding="utf-8")

    assert (
        admission_identity._pushed_commit_range_excluding(
            repo, pushed_head=missing_head, trusted_baselines=()
        )
        == []
    )
    assert admission_identity._read_reconciliation_receipt("") is None
    assert admission_identity._read_reconciliation_receipt(receipt_path.as_posix()) is None
    assert admission_identity._reconciliation_baselines(
        repo,
        pushed_head=git(repo, "rev-parse", "HEAD"),
        primary_baseline="",
        observation=ReconciliationObservation(
            submit_branch="submit/dual-remote-reconciliation",
            receipt_path=receipt_path.as_posix(),
        ),
    ) == ((), ["push_identity_reconciliation_receipt_invalid"])


def test_reconciliation_receipt_reports_mismatch_stale_and_missing_baselines(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    pushed_head = git(repo, "rev-parse", "HEAD")
    receipt_path = tmp_path / "mismatched-reconciliation.json"
    receipt = reconciliation_receipt_payload(
        submit_branch="submit/dual-remote-reconciliation",
        source_head=pushed_head,
        origin_head="a" * 40,
        github_head="b" * 40,
    )
    receipt["payload_digest"] = "mismatch"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    _, gaps = admission_identity._reconciliation_baselines(
        repo,
        pushed_head=pushed_head,
        primary_baseline="",
        observation=ReconciliationObservation(
            submit_branch="submit/dual-remote-reconciliation",
            receipt_path=receipt_path.as_posix(),
            origin_head="different-origin",
            github_head="different-github",
        ),
    )

    assert "push_identity_reconciliation_receipt_payload_digest_mismatch" in gaps
    assert "push_identity_reconciliation_origin_head_stale" in gaps
    assert "push_identity_reconciliation_github_head_stale" in gaps
    assert "push_identity_reconciliation_baseline_missing:" + "a" * 40 in gaps
    assert "push_identity_reconciliation_baseline_missing:" + "b" * 40 in gaps
