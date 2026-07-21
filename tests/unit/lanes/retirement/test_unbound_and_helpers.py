from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.core as retirement
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.reconciliation.core as reconciliation
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.store.state.lease.lifecycle import core as state
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

_CLAIM_ID = "exceptional-unbound-test-claim"
_CHRONICLE_REF = "evidence/chronicle/exceptional-unbound-test/2026-07-19.md"
_OBSERVE = "_" + "observe"
_STALE_OBSERVATION_GAP = "unbound_retire_pre_effect_observation_stale"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _exceptional_fixture(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    branch = "work/stale-ref"
    git(repo, "branch", branch, "dev")
    head = git(repo, "rev-parse", branch)
    _write(
        repo / f"evidence/claims/{_CLAIM_ID}.toml",
        (
            f'[claim]\nid = "{_CLAIM_ID}"\n'
            'subject = "ethos:test:exceptional-unbound"\nstate = "active"\n'
        ),
    )
    _write(
        repo / _CHRONICLE_REF,
        (
            "event: lane_retire/unbound_exceptional\n"
            f"target_branch: {branch}\ntarget_head: {head}\ntarget_claim: {_CLAIM_ID}\n"
        ),
    )
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accept policy",
    )
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    return repo, branch, head, _CHRONICLE_REF


def _retire(repo: Path, branch: str, head: str, chronicle: str, **changes):
    request = {
        "root": repo,
        "branch": branch,
        "expect_head": head,
        "reason": "accepted truth contains the source",
        "chronicle_ref": chronicle,
    }
    return retirement.retire_unbound_work_lane_ref(**(request | changes))


def _owner_unavailable_fixture(
    tmp_path: Path,
) -> tuple[Path, str, str, str, dict[str, object], Path]:
    """Create one accepted-policy-bound unbound ref with an absent source owner path."""
    repo, branch, head, chronicle_ref = _exceptional_fixture(tmp_path)
    source_path = tmp_path / "missing-source-worktree"
    holder = "agent:test:session:missing-source-owner"
    lease = state.acquire_lease(
        repo / ".ethos/state/state.sqlite",
        subject=branch,
        holder_ref=holder,
        payload={
            "branch": branch,
            "expected_head": head,
            "path": source_path.as_posix(),
        },
    )
    _write(
        repo / chronicle_ref,
        "\n".join(
            (
                "# Exceptional unbound owner-unavailable recovery policy",
                "",
                "event: lane_retire/unbound_exceptional",
                f"target_branch: {branch}",
                f"target_head: {head}",
                f"target_claim: {_CLAIM_ID}",
                "lease_recovery: owner_unavailable",
                f"source_lease_id: {lease['lease_id']}",
                f"source_lease_holder: {holder}",
                f"source_lease_epoch: {lease['epoch']}",
                f"source_lease_expected_head: {head}",
                f"source_lease_expires_at: {lease['expires_at']}",
                f"source_lease_payload_sha256: {lease['payload_sha256']}",
                (
                    "source_worktree_path_sha256: "
                    f"{hashlib.sha256(source_path.as_posix().encode()).hexdigest()}"
                ),
                "source_worktree_absent: true",
                "",
            )
        ),
    )
    git(repo, "add", chronicle_ref)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accept owner-unavailable policy",
    )
    return repo, branch, head, chronicle_ref, lease, source_path


def _partial_effect_reconciliation_fixture(
    tmp_path: Path,
) -> tuple[Path, str, str, str, dict[str, object], dict[str, object], Path]:
    """Create an accepted ref-absent residue plus its immutable failed-attempt record."""
    repo, branch, head, source_chronicle, lease, source_path = _owner_unavailable_fixture(tmp_path)
    source_observation = observation.observe(repo, branch=branch, chronicle_ref=source_chronicle)
    operation_id = records.operation_id(
        branch=branch,
        expect_head=head,
        accepted_head=str(source_observation["accepted_head"]),
        protected_refs=source_observation["protected_refs"],
        claim_id=str(source_observation["claim_id"]),
        chronicle=observation.chronicle_binding(source_observation),
        reason="native source attempt before partial effect",
        observation_sha256=str(source_observation["observation_sha256"]),
    )
    source_attempt = records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=head,
        reason="native source attempt before partial effect",
        observation=source_observation,
    )
    records_root = repo.parent / f"{repo.name}-records"
    records.write_record(
        records.attempt_path(records_root, operation_id),
        source_attempt,
        kind=records.ATTEMPT_KIND,
    )
    git(repo, "update-ref", "-d", f"refs/heads/{branch}", head)

    claim_id = "partial-effect-reconciliation-test-claim"
    chronicle_ref = "evidence/chronicle/partial-effect-reconciliation-test/2026-07-20.md"
    _write(
        repo / f"evidence/claims/{claim_id}.toml",
        "\n".join(
            (
                "[claim]",
                f'id = "{claim_id}"',
                'subject = "ethos:test:ref-absent-owner-unavailable-reconciliation"',
                'state = "active"',
                "",
            )
        ),
    )
    _write(
        repo / chronicle_ref,
        "\n".join(
            (
                "# Ref-absent owner-unavailable reconciliation policy",
                "",
                "event: lane_retire/unbound_exceptional",
                f"target_branch: {branch}",
                f"target_head: {head}",
                f"target_claim: {claim_id}",
                "lease_recovery: owner_unavailable",
                f"source_lease_id: {lease['lease_id']}",
                f"source_lease_holder: {lease['holder_ref']}",
                f"source_lease_epoch: {lease['epoch']}",
                f"source_lease_expected_head: {head}",
                f"source_lease_expires_at: {lease['expires_at']}",
                f"source_lease_payload_sha256: {lease['payload_sha256']}",
                (
                    "source_worktree_path_sha256: "
                    f"{hashlib.sha256(source_path.as_posix().encode()).hexdigest()}"
                ),
                "source_worktree_absent: true",
                "partial_effect_reconciliation: ref_absent_owner_unavailable",
                f"source_retirement_attempt_id: {operation_id}",
                f"source_retirement_attempt_accepted_head: {source_attempt['accepted_head']}",
                f"source_retirement_attempt_claim_id: {source_attempt['claim_id']}",
                f"source_retirement_attempt_chronicle_ref: {source_attempt['chronicle_ref']}",
                f"source_retirement_attempt_chronicle_sha256: {source_attempt['chronicle_sha256']}",
                (
                    "source_retirement_attempt_chronicle_claim_id: "
                    f"{source_attempt['chronicle_claim_id']}"
                ),
                (
                    "source_retirement_attempt_chronicle_claim_sha256: "
                    f"{source_attempt['chronicle_claim_sha256']}"
                ),
                "",
            )
        ),
    )
    git(repo, "add", "evidence")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accept ref-absent reconciliation policy",
    )
    return repo, branch, head, chronicle_ref, lease, source_attempt, source_path


def _reconcile(repo: Path, branch: str, chronicle: str, **changes):
    controls = reconciliation.RefAbsentReconciliationControls(
        reason="accepted policy binds the exact ref-absent partial effect",
        chronicle_ref=chronicle,
        **changes,
    )
    return reconciliation.reconcile_ref_absent_owner_unavailable_lease(
        root=repo,
        branch=branch,
        controls=controls,
    )


def test_owner_unavailable_recovery_requires_an_active_foreign_lease(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")

    report = _retire(
        repo,
        branch,
        head,
        chronicle,
        owner_unavailable_recovery=True,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["required_gaps"] == ["unbound_retire_owner_unavailable_not_required"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_owner_unavailable_recovery_revokes_exact_foreign_lease(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle, lease, source_path = _owner_unavailable_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")

    report = _retire(
        repo,
        branch,
        head,
        chronicle,
        owner_unavailable_recovery=True,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert source_path.exists() is False
    assert report["state"] == "retired_unbound_exceptional"
    assert report["lease_relinquished"] == {
        "revoked": True,
        "subject": branch,
        "lease_id": lease["lease_id"],
        "holder_ref": lease["holder_ref"],
        "epoch": lease["epoch"],
        "expected_head": head,
        "expires_at": lease["expires_at"],
        "payload_sha256": lease["payload_sha256"],
    }
    assert report["receipt"]["postconditions"]["active_lease_absent"] is True


def test_owner_unavailable_recovery_blocks_path_reappearance(monkeypatch, tmp_path: Path) -> None:
    repo, branch, head, chronicle, _lease, source_path = _owner_unavailable_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    source_path.mkdir()

    report = _retire(
        repo,
        branch,
        head,
        chronicle,
        owner_unavailable_recovery=True,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["required_gaps"] == ["unbound_retire_owner_unavailable_source_path_present"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_ref_absent_reconciliation_revokes_only_exact_foreign_lease(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle, lease, source_attempt, source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")

    report = _reconcile(
        repo,
        branch,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert source_path.exists() is False
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )
    assert report["state"] == "reconciled_ref_absent_owner_unavailable_lease"
    assert (
        report["mutation"]["decision"]["subject"]["expected_state"]["invocation_holder_ref"]
        == "agent:test:case:recovery-operator"
    )
    assert report["source_retirement_attempt"] == source_attempt
    assert report["lease_relinquished"] == {
        "revoked": True,
        "subject": branch,
        "lease_id": lease["lease_id"],
        "holder_ref": lease["holder_ref"],
        "epoch": lease["epoch"],
        "expected_head": head,
        "expires_at": lease["expires_at"],
        "payload_sha256": lease["payload_sha256"],
    }
    assert Path(str(report["receipt_path"])).is_file()
    assert report["receipt"]["postconditions"] == {
        "ref_absent": True,
        "worktree_absent": True,
        "active_lease_absent": True,
        "protected_refs_unchanged": True,
        "chronicle_unchanged": True,
    }


@pytest.mark.parametrize(
    ("mode", "expected_gap"),
    [
        ("ref", "unbound_retire_partial_effect_ref_present"),
        ("worktree", "unbound_retire_partial_effect_worktree_present"),
        ("lease", "unbound_retire_owner_unavailable_lease_mismatch"),
        ("attempt", "unbound_retire_partial_effect_attempt_mismatch"),
        ("chronicle", "unbound_retire_chronicle_content_drift"),
    ],
)
def test_ref_absent_reconciliation_fail_closed_matrix(
    monkeypatch, tmp_path: Path, mode: str, expected_gap: str
) -> None:
    repo, branch, head, chronicle, lease, source_attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    if mode == "ref":
        git(repo, "branch", branch, "dev")
    elif mode == "worktree":
        worktree = tmp_path / "reappeared-worktree"
        git(repo, "worktree", "add", "--detach", worktree.as_posix(), "dev")
        git(repo, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    elif mode == "lease":
        with closing(sqlite3.connect(repo / ".ethos/state/state.sqlite")) as connection:
            connection.execute(
                "update leases set payload_json = replace(payload_json, ?, ?) where id = ?",
                (head, "a" * 40, lease["lease_id"]),
            )
            connection.commit()
    elif mode == "attempt":
        monkeypatch.setattr(
            reconciliation.records,
            "read_record",
            lambda *_args, **_kwargs: {
                **source_attempt,
                "operation_id": "exceptional-unbound-retirement:missing",
            },
        )
    else:
        (repo / chronicle).write_text("drift\n", encoding="utf-8")

    report = _reconcile(repo, branch, chronicle)

    assert expected_gap in report["required_gaps"]
    if mode != "ref":
        assert (
            subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=repo,
                check=False,
            ).returncode
            != 0
        )


def test_exceptional_retirement_contract_matrix(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path / "plan")
    missing = _retire(repo, branch, head, "")
    assert missing["required_gaps"] == ["unbound_retire_chronicle_ref_required"]
    planned = _retire(repo, branch, head, chronicle)
    assert (planned["state"], planned["required_gaps"]) == (
        "ready_to_retire_unbound_exceptional",
        [],
    )
    blocked = _retire(repo, branch, head, chronicle, apply=True, authorized=True)
    assert blocked["required_gaps"] == [
        "irreversible_confirmation_required",
        "unbound_retire_requires_break_glass",
    ]
    live_repo, live_branch, live_head, live_chronicle = _exceptional_fixture(tmp_path / "live")
    retired = _retire(
        live_repo,
        live_branch,
        live_head,
        live_chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )
    assert retired["state"] == "retired_unbound_exceptional"
    assert retired["mutation"]["decision"]["verdict"] == "allow"
    assert all(retired["receipt"]["postconditions"].values())


def test_projection_and_dirty_support(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "dirty")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    assert dirty_provenance(repo)["summary"]["untracked"] == 1
    assert (
        observation.unbound_work_lane_ref(
            {"coordination": {"unbound_work_lane_refs": [{"branch": "work/other"}]}}, "work/x"
        )
        is None
    )


def _leased_case(tmp_path: Path, monkeypatch) -> tuple[Path, str, str, str, str, dict[str, object]]:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    holder = "agent:test:case:lease-holder"
    lease = state.acquire_lease(
        repo / ".ethos/state/state.sqlite",
        subject=branch,
        holder_ref=holder,
        payload={"branch": branch, "expected_head": head},
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    return repo, branch, head, chronicle, holder, lease


def _apply(repo: Path, branch: str, head: str, chronicle: str):
    return _retire(
        repo,
        branch,
        head,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )


def _insert_racing_lease(database: Path, *, branch: str, head: str, holder: str) -> None:
    payload = json.dumps(
        {
            "lease_id": "lease:racing",
            "lane_ref": branch,
            "holder_ref": holder,
            "epoch": 2,
            "expected_head": head,
            "claim_id": _CLAIM_ID,
        },
        sort_keys=True,
    )
    with closing(sqlite3.connect(database, timeout=0)) as connection:
        connection.execute("begin immediate")
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            ("lease:racing", branch, holder, "2099-01-01T00:00:00+00:00", payload),
        )


class _CommitFailure:
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        raise sqlite3.OperationalError


def test_owned_lease_relinquishment_receipt(monkeypatch, tmp_path: Path) -> None:
    repo, branch, head, chronicle, holder, lease = _leased_case(tmp_path, monkeypatch)
    report = _apply(repo, branch, head, chronicle)
    expected = {
        "revoked": True,
        "subject": branch,
        "lease_id": lease["lease_id"],
        "holder_ref": holder,
        "epoch": lease["epoch"],
        "expected_head": head,
        "expires_at": lease["expires_at"],
        "payload_sha256": lease["payload_sha256"],
    }
    assert report["lease_relinquished"] == expected
    assert report["receipt"]["lease_relinquished"] == expected
    assert report["receipt"]["lease_relinquish_binding"] == {
        "active": True,
        **{
            key: expected[key]
            for key in (
                "lease_id",
                "holder_ref",
                "epoch",
                "expected_head",
                "expires_at",
                "payload_sha256",
            )
        },
    }
    assert report["receipt"]["effect"]["command"] == "git update-ref --stdin"
    assert report["receipt"]["effect"]["transaction"] == "cas_protected_refs_delete_target"


def test_owned_lease_relinquishment_fail_closed(monkeypatch, tmp_path: Path) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        assert (
            retirement.relinquish_owned_lease(
                connection,
                observed={
                    observation.HAS_ACTIVE_LEASE: True,
                    "active_lease": {"holder_ref": "agent:test", "epoch": "bad"},
                    "branch": "work/stale-ref",
                },
                holder_ref="agent:test",
            )
            is None
        )
    with monkeypatch.context() as patch:
        repo, branch, head, chronicle, _holder, _lease = _leased_case(tmp_path / "revoke", patch)
        patch.setattr(
            retirement,
            "revoke_lease_from_connection",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError()),
        )
        report = _apply(repo, branch, head, chronicle)
        assert report["required_gaps"] == ["unbound_retire_active_lease"]
        assert git(repo, "rev-parse", "--verify", branch) == head
    with monkeypatch.context() as patch:
        repo, branch, head, chronicle, _holder, _lease = _leased_case(tmp_path / "delete", patch)
        real_git = retirement.run_git

        def failed_delete(root: Path, *args: str, check: bool = True, env=None, stdin=None):
            if args[:2] in {("update-ref", "-d"), ("update-ref", "--stdin")}:
                return subprocess.CompletedProcess(["git", *args], 1, "", "ref changed")
            return real_git(root, *args, check=check, env=env, stdin=stdin)

        patch.setattr(retirement, "run_git", failed_delete)
        report = _apply(repo, branch, head, chronicle)
        assert report["lease_relinquished"] == {}
        assert report["lease_relinquish_rolled_back"]["revoked"] is True
        assert "unbound_retire_ref_delete_failed" in report["required_gaps"]
        assert git(repo, "rev-parse", "--verify", branch) == head
        assert (
            observation.observe(repo, branch=branch, chronicle_ref=chronicle)[
                observation.HAS_ACTIVE_LEASE
            ]
            is True
        )


def test_last_window_lease_reappearance_keeps_target_ref(monkeypatch, tmp_path: Path) -> None:
    repo, branch, head, chronicle, holder, _lease = _leased_case(tmp_path, monkeypatch)
    real_git = retirement.run_git

    def race(root: Path, *args: str, check: bool = True, env=None, stdin=None):
        if args[:2] in {("update-ref", "-d"), ("update-ref", "--stdin")}:
            _insert_racing_lease(
                repo / ".ethos/state/state.sqlite", branch=branch, head=head, holder=holder
            )
        return real_git(root, *args, check=check, env=env, stdin=stdin)

    monkeypatch.setattr(retirement, "run_git", race)
    report = _apply(repo, branch, head, chronicle)
    assert report["required_gaps"] == ["unbound_retire_active_lease"]
    assert report["lease_relinquished"] == {}
    assert report["lease_relinquish_rolled_back"]["revoked"] is True
    assert real_git(repo, "rev-parse", "--verify", branch, check=False).stdout.strip() == head


def test_last_window_protected_ref_drift_keeps_target_ref(monkeypatch, tmp_path: Path) -> None:
    repo, branch, head, chronicle, _holder, _lease = _leased_case(tmp_path, monkeypatch)
    real_git = retirement.run_git
    accepted = git(repo, "rev-parse", "dev")

    def race(root: Path, *args: str, check: bool = True, env=None, stdin=None):
        if args[:2] in {("update-ref", "-d"), ("update-ref", "--stdin")}:
            real_git(root, "update-ref", "refs/heads/dev", head, accepted)
        return real_git(root, *args, check=check, env=env, stdin=stdin)

    monkeypatch.setattr(retirement, "run_git", race)
    report = _apply(repo, branch, head, chronicle)
    assert "unbound_retire_protected_refs_changed" in report["required_gaps"]
    assert report["lease_relinquished"] == {}
    assert report["lease_relinquish_rolled_back"]["revoked"] is True
    assert real_git(repo, "rev-parse", "--verify", branch, check=False).stdout.strip() == head


@pytest.mark.parametrize("rc", [0, 1])
def test_commit_failure_compensation(monkeypatch, tmp_path: Path, rc: int) -> None:
    repo, branch, head, chronicle, _holder, _lease = _leased_case(tmp_path, monkeypatch)
    real_git, real_closing = retirement.run_git, retirement.closing

    def fail_restore(root: Path, *args: str, check: bool = True, env=None, stdin=None):
        if rc and args[:1] == ("update-ref",) and args[1:2] != ("--stdin",):
            return subprocess.CompletedProcess(["git", *args], 1, "", "restore rejected")
        return real_git(root, *args, check=check, env=env, stdin=stdin)

    monkeypatch.setattr(retirement, "run_git", fail_restore)
    monkeypatch.setattr(
        retirement, "closing", lambda connection: real_closing(_CommitFailure(connection))
    )
    report = _apply(repo, branch, head, chronicle)
    observed = real_git(repo, "rev-parse", "--verify", branch, check=False).stdout.strip()
    assert observed == ("" if rc else head)
    assert report["compensation"]["restored"] is (rc == 0)
    assert ("unbound_retire_ref_restore_failed" in report["required_gaps"]) is bool(rc)
    assert (
        observation.observe(repo, branch=branch, chronicle_ref=chronicle)[
            observation.HAS_ACTIVE_LEASE
        ]
        is True
    )


@pytest.mark.parametrize(
    ("mode", "gaps"),
    [
        ("lease", ("unbound_retire_active_lease", _STALE_OBSERVATION_GAP)),
        ("claim", (_STALE_OBSERVATION_GAP,)),
    ],
)
def test_predelete_recheck_blocks_drift(
    monkeypatch, tmp_path: Path, mode: str, gaps: tuple[str, ...]
) -> None:
    repo, branch, head, chronicle, _holder, lease = _leased_case(tmp_path, monkeypatch)
    active = observation.public_lease(lease)
    active["holder_ref"] = "agent:test:racing"
    real_observe = getattr(retirement, _OBSERVE)
    count = 0

    def changed(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal count
        count += 1
        observed = real_observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        if count != 3:
            return observed
        if mode == "lease":
            return {**observed, observation.HAS_ACTIVE_LEASE: True, "active_lease": active}
        return {**observed, "claim_id": "drifted-claim"}

    monkeypatch.setattr(retirement, _OBSERVE, changed)
    report = _apply(repo, branch, head, chronicle)
    assert report["required_gaps"] == list(gaps)
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_ref_absent_reconciliation_rejects_missing_reason(monkeypatch, tmp_path: Path) -> None:
    """A dry-run must reject the empty reason before it can create an intent record."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")

    report = reconciliation.reconcile_ref_absent_owner_unavailable_lease(
        root=repo,
        branch=branch,
        controls=reconciliation.RefAbsentReconciliationControls(chronicle_ref=chronicle),
    )

    assert report["required_gaps"] == ["retire_reason_required"]


def test_ref_absent_reconciliation_blocks_record_write_failure(monkeypatch, tmp_path: Path) -> None:
    """A no-clobber attempt write failure must leave the foreign lease intact."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    monkeypatch.setattr(
        records, "write_record", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied"))
    )

    report = _reconcile(
        repo,
        branch,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["denied"]


def test_ref_absent_reconciliation_blocks_stale_pre_effect_observation(
    monkeypatch, tmp_path: Path
) -> None:
    """A last-window observation change must prevent the lease-only CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    real_observe = reconciliation.observation.observe_ref_absent_reconciliation
    calls = 0

    def changed(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        observed = real_observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        return observed if calls == 1 else {**observed, "claim_id": "drifted-claim"}

    monkeypatch.setattr(reconciliation.observation, "observe_ref_absent_reconciliation", changed)
    report = _reconcile(
        repo,
        branch,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert "unbound_retire_pre_effect_observation_stale" in report["required_gaps"]


def test_ref_absent_reconciliation_blocks_lease_revoke_failure(monkeypatch, tmp_path: Path) -> None:
    """A failed exact lease CAS must return the active-lease block without a receipt."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    monkeypatch.setattr(reconciliation, "relinquish_owned_lease", lambda *_args, **_kwargs: None)

    report = _reconcile(
        repo,
        branch,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["required_gaps"] == ["unbound_retire_active_lease"]


def test_ref_absent_reconciliation_blocks_receipt_write_failure(
    monkeypatch, tmp_path: Path
) -> None:
    """Receipt persistence failure remains explicit after a successful lease CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    real_write = records.write_record

    receipt_error = "receipt denied"

    def fail_receipt(path: Path, payload: dict[str, object], *, kind: str) -> str:
        if kind == records.RECONCILIATION_RECEIPT_KIND:
            raise OSError(receipt_error)
        return real_write(path, payload, kind=kind)

    monkeypatch.setattr(records, "write_record", fail_receipt)
    report = _reconcile(
        repo,
        branch,
        chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["receipt denied"]
