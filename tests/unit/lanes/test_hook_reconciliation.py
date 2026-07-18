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


def _use_identity(
    repo: Path, monkeypatch: pytest.MonkeyPatch, label: str, *, configure: bool = False
) -> None:
    name, email = f"{label} User", f"{label.lower()}@example.invalid"
    if configure:
        git(repo, "config", "user.name", name)
        git(repo, "config", "user.email", email)
        git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", name)
        monkeypatch.setenv(f"GIT_{role}_EMAIL", email)


def _commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_new_submit_push_reconciles_divergent_origin_and_github_identity_baselines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    _use_identity(repo, monkeypatch, "Canonical", configure=True)
    _use_identity(repo, monkeypatch, "Legacy")
    legacy_head = _commit_file(repo, "legacy.txt", "legacy\n", "legacy history")
    git(repo, "update-ref", "refs/remotes/github/dev", legacy_head)
    git(repo, "checkout", "-b", "origin-source", "HEAD~1")
    origin_head = _commit_file(repo, "origin.txt", "origin\n", "origin history")
    git(repo, "update-ref", "refs/remotes/origin/dev", origin_head)
    git(repo, "checkout", "dev")
    _use_identity(repo, monkeypatch, "Canonical")
    pushed_head = _commit_file(repo, "carrier.txt", "carrier\n", "reconciliation carrier")
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


def test_new_submit_push_reconciles_dev_and_main_identity_baselines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    _use_identity(repo, monkeypatch, "Canonical", configure=True)
    base = git(repo, "rev-parse", "HEAD")
    _use_identity(repo, monkeypatch, "Legacy")
    heads: dict[str, str] = {}
    branches: list[str] = []
    for remote, role in (
        ("origin", "dev"),
        ("origin", "main"),
        ("github", "dev"),
        ("github", "main"),
    ):
        branch = f"legacy-{remote}-{role}"
        branches.append(branch)
        git(repo, "checkout", "-b", branch, base)
        heads[f"{remote}_{role}"] = _commit_file(
            repo,
            f"{remote}-{role}.txt",
            f"{remote}-{role}\n",
            f"legacy {remote} {role}",
        )
        git(repo, "update-ref", f"refs/remotes/{remote}/{role}", "HEAD")
    git(repo, "checkout", "dev")
    _use_identity(repo, monkeypatch, "Canonical")
    for branch in branches:
        git(repo, "merge", "--no-ff", branch, "-m", f"merge {branch}")
    pushed_head = git(repo, "rev-parse", "HEAD")
    receipt_path = tmp_path / "four-ref-reconciliation.json"
    receipt_path.write_text(
        json.dumps(
            reconciliation_receipt_payload(
                submit_branch="submit/four-ref-reconciliation",
                source_head=pushed_head,
                origin_head=heads["origin_dev"],
                github_head=heads["github_dev"],
                main_heads=(heads["origin_main"], heads["github_main"]),
            )
        ),
        encoding="utf-8",
    )

    observation = ReconciliationObservation(
        receipt_path=receipt_path.as_posix(),
        origin_head=heads["origin_dev"],
        origin_main_head=heads["origin_main"],
        github_head=heads["github_dev"],
        github_main_head=heads["github_main"],
    )
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/submit/four-ref-reconciliation",
        pushed_head=pushed_head,
        remote_head="0" * 40,
        reconciliation=observation,
    )

    assert report["identity_policy"]["ok"] is True
    assert report["identity_policy"]["violations"] == []
    protected = push_admission_report(
        root=repo,
        target_ref="refs/heads/dev",
        pushed_head=pushed_head,
        remote_head=heads["origin_dev"],
        reconciliation=observation,
    )
    assert protected["identity_policy"]["ok"] is True


def test_new_submit_push_blocks_divergence_without_an_exact_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    _use_identity(repo, monkeypatch, "Canonical", configure=True)
    git(repo, "checkout", "-b", "origin-source")
    _commit_file(repo, "origin.txt", "origin\n", "origin history")
    git(repo, "update-ref", "refs/remotes/origin/dev", "HEAD")
    git(repo, "checkout", "dev")
    pushed_head = _commit_file(repo, "carrier.txt", "carrier\n", "reconciliation carrier")

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
    _use_identity(repo, monkeypatch, "Canonical", configure=True)
    git(repo, "checkout", "-b", "origin-source")
    origin_head = _commit_file(repo, "origin.txt", "origin\n", "origin history")
    git(repo, "update-ref", "refs/remotes/origin/dev", origin_head)
    git(repo, "checkout", "dev")
    github_head = _commit_file(repo, "github.txt", "github\n", "github history")
    git(repo, "update-ref", "refs/remotes/github/dev", github_head)
    pushed_head = _commit_file(repo, "carrier.txt", "carrier\n", "reconciliation carrier")
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
    git(repo, "update-ref", "refs/remotes/origin/main", origin_head)
    git(repo, "update-ref", "refs/remotes/github/dev", github_head)
    git(repo, "update-ref", "refs/remotes/github/main", github_head)
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
        main_heads=(origin_head, github_head),
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == payload["data"]["receipt"]


def test_reconciliation_receipt_command_blocks_missing_tracking_refs(
    tmp_path: Path,
) -> None:
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
        "reconciliation_origin_main_tracking_missing",
        "reconciliation_github_tracking_missing",
        "reconciliation_github_main_tracking_missing",
    ]
    assert not receipt_path.exists()


def test_reconciliation_receipt_command_rejects_repository_local_output(
    tmp_path: Path,
) -> None:
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
