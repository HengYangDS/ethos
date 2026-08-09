from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.identity import reconciliation_receipt_payload
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _identity_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, str]:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    baseline = git(repo, "rev-parse", "HEAD")
    (repo / "change.txt").write_text("change\n", encoding="utf-8")
    git(repo, "add", "change.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "matching identity",
    )
    return repo, baseline, git(repo, "rev-parse", "HEAD")


def _receipt(path: Path, *, source: str, baseline: str) -> ReconciliationObservation:
    payload = reconciliation_receipt_payload(
        proposal_branch="proposal/identity",
        source_head=source,
        origin_head=baseline,
        github_head=baseline,
        main_heads=(baseline, baseline),
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    return ReconciliationObservation(
        proposal_branch="proposal/identity",
        receipt_path=path.as_posix(),
        origin_head=baseline,
        origin_main_head=baseline,
        github_head=baseline,
        github_main_head=baseline,
    )


def test_identity_reconciliation_accepts_exact_receipt_baselines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, baseline, pushed = _identity_repository(tmp_path, monkeypatch)
    observation = _receipt(tmp_path / "receipt.json", source=pushed, baseline=baseline)

    report = push_identity_policy_report(repo, pushed, reconciliation=observation)

    assert report["verdict"] == "pass"
    assert report["checked_commit_count"] == 1
    assert report["required_gaps"] == []


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing", "push_identity_reconciliation_receipt_invalid"),
        ("invalid-json", "push_identity_reconciliation_receipt_invalid"),
        ("digest-drift", "push_identity_reconciliation_receipt_payload_digest_mismatch"),
        ("observed-drift", "push_identity_reconciliation_origin_head_stale"),
        ("baseline-missing", "push_identity_reconciliation_baseline_missing:"),
    ],
)
def test_identity_reconciliation_fails_closed_on_receipt_or_observation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, expected: str
) -> None:
    repo, baseline, pushed = _identity_repository(tmp_path, monkeypatch)
    path = tmp_path / "receipt.json"
    observation = _receipt(path, source=pushed, baseline=baseline)
    if case == "missing":
        path.unlink()
    elif case == "invalid-json":
        path.write_text("[", encoding="utf-8")
    elif case == "digest-drift":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["payload_digest"] = "0" * 64
        path.write_text(json.dumps(payload), encoding="utf-8")
    elif case == "observed-drift":
        observation = ReconciliationObservation(
            proposal_branch=observation.proposal_branch,
            receipt_path=observation.receipt_path,
            origin_head="f" * 40,
            origin_main_head=observation.origin_main_head,
            github_head=observation.github_head,
            github_main_head=observation.github_main_head,
        )
    else:
        missing = "f" * 40
        observation = _receipt(path, source=pushed, baseline=missing)

    report = push_identity_policy_report(repo, pushed, reconciliation=observation)

    assert report["verdict"] == "block"
    assert any(gap.startswith(expected) for gap in report["required_gaps"])


@pytest.mark.parametrize(
    ("trusted", "expected"),
    [
        ("ancestor", None),
        ("missing", "push_identity_reconciliation_receipt_required"),
    ],
)
def test_identity_reconciliation_requires_receipt_only_without_trusted_ancestry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted: str,
    expected: str | None,
) -> None:
    repo, baseline, pushed = _identity_repository(tmp_path, monkeypatch)
    trusted_baseline = baseline if trusted == "ancestor" else ""
    observation = ReconciliationObservation(proposal_branch="proposal/identity")

    report = push_identity_policy_report(
        repo,
        pushed,
        trusted_baseline=trusted_baseline,
        reconciliation=observation,
    )

    assert report["verdict"] == ("pass" if expected is None else "block")
    assert report["required_gaps"] == ([] if expected is None else [expected])
