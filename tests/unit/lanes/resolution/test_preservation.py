from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import tarfile
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution.capture as preservation
import ethos.adapters.store.state.lease.lifecycle.transitions as lease_transitions
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_head
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.lifecycle.declaration import LeaseTransitionDeclaration
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.resolution.lane import LaneObservation
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.lane_helpers import superseded_work_lane


def test_preservation_package_is_deterministic_for_its_observed_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"binary\x00payload\xff\n"
    (source / "listed.bin").write_bytes(payload)
    package = tmp_path / "package"
    package.mkdir()
    calls: list[tuple[str, ...]] = []

    def fixed_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
        assert root == source
        calls.append(args)
        if args[:2] == ("bundle", "create"):
            Path(args[2]).write_bytes(b"bundle")
            return subprocess.CompletedProcess(["git", *args], 0, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(
            ["git", *args],
            0,
            stdout=b"index\n" if "--cached" in args else b"tracked\n",
            stderr=b"",
        )

    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git)
    monkeypatch.setattr(resolution_effects, "untracked_files", lambda _source: [b"listed.bin"])
    result = resolution_effects.preserve_package(
        tmp_path,
        package,
        LaneObservation(
            lane_ref="work/example",
            head="a" * 40,
            lane_incarnation_id="lane:one",
            path=source.as_posix(),
            dirty=True,
            foreign=True,
            orphan=True,
            ambiguous=False,
            tracked_digest="b" * 64,
            untracked_digest="c" * 64,
        ),
        {"decision_id": "decision:one"},
    )

    assert calls == [
        ("bundle", "create", (package / "repository.bundle").as_posix(), "work/example"),
        ("diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
        ("diff", "--cached", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
    ]
    with tarfile.open(package / "untracked.tar") as archive:
        stored = archive.extractfile("listed.bin")
        assert archive.getnames() == ["listed.bin"]
        assert stored is not None
        assert stored.read() == payload
    assert (package / "tracked.patch").read_bytes() == b"tracked\n"
    assert (package / "index.patch").read_bytes() == b"index\n"
    manifest = result["manifest"]
    assert isinstance(manifest, dict)
    assert manifest["package_format_version"] == "v2"
    assert manifest["patch_sha256"] == hashlib.sha256(b"tracked\n").hexdigest()
    assert manifest["index_patch_sha256"] == hashlib.sha256(b"index\n").hexdigest()


def _lease_request(
    *,
    operation: str,
    branch: str,
    holder_ref: str,
    lease: dict[str, object],
    apply: bool,
    **values: object,
) -> LeaseOperationRequest:
    """Build a generation-bound public lease request from its current projection."""
    payload: dict[str, object] = {
        "operation": operation,
        "branch": branch,
        "holder_ref": holder_ref,
        "lease_id": str(lease["lease_id"]),
        "expected_epoch": int(lease["epoch"]),
        "expect_head": str(lease["expected_head"]),
        "expected_expires_at": str(lease["expires_at"]),
        "expected_payload_sha256": str(lease["payload_sha256"]),
        "apply": apply,
    }
    payload.update(values)
    return LeaseOperationRequest.model_validate(payload)


def _lease_snapshot(worktree: Path, branch: str) -> dict[str, object]:
    return leases_by_branch(worktree)[branch]


def _assert_reissue_changes(
    before: dict[str, object],
    after: dict[str, object],
    *declared_fields: str,
) -> None:
    before_payload = dict(before["payload"])
    after_payload = dict(after["payload"])
    assert set(before_payload) == set(after_payload) == set(LaneLease.model_fields)
    assert {
        field for field in LaneLease.model_fields if before_payload[field] != after_payload[field]
    } == set(declared_fields)


def _lease_transition(root: Path, operation: str) -> LeaseTransitionDeclaration:
    return next(
        item for item in load_lifecycle_declaration(root).lease_transition if item.id == operation
    )


def _apply_lease(root: Path, database: Path, request: LeaseOperationRequest) -> dict[str, object]:
    return apply_lease_operation(
        database,
        transition=_lease_transition(root, request.operation),
        request=request,
    )


def _insert_lease_row(
    database: Path,
    lease: LaneLease,
    *,
    payload: dict[str, object] | None = None,
    row_expires_at: str | None = None,
) -> None:
    raw_payload = json.dumps(payload or lease.to_payload(), sort_keys=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            (
                lease.lease_id,
                lease.lane_ref,
                lease.holder_ref.serialize(),
                row_expires_at or lease.expires_at.isoformat(),
                raw_payload,
            ),
        )


def test_lease_observation_keeps_valid_expired_unknown_and_missing_distinct(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    missing = observe_lease(database, "work/missing")
    assert (missing.state, missing.lease, missing.row) == ("missing", None, None)

    now = datetime.now(UTC)
    valid = LaneLease(
        lane_incarnation_id="lane-incarnation:valid",
        lease_id="lease:valid",
        lane_ref="work/valid",
        holder_ref=HolderRef.parse("agent:test:case:valid"),
        epoch=1,
        issued_at=now,
        renewed_at=now,
        expires_at=now + timedelta(hours=1),
        expected_head="a" * 40,
        base_change_contract_digest="b" * 64,
        path_scope=(),
        handoff=None,
    )
    _insert_lease_row(database, valid)
    observed_valid = observe_lease(database, valid.lane_ref)
    assert observed_valid.state == "valid"
    assert observed_valid.lease == valid

    expired = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:expired",
            "lease_id": "lease:expired",
            "lane_ref": "work/expired",
            "issued_at": now - timedelta(hours=2),
            "renewed_at": now - timedelta(hours=2),
            "expires_at": now - timedelta(hours=1),
        }
    )
    _insert_lease_row(database, expired)
    assert observe_lease(database, expired.lane_ref).state == "expired"

    legacy_payload = valid.to_payload() | {"claim_id": "retired"}
    legacy_payload.pop("base_change_contract_digest")
    legacy = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:legacy",
            "lease_id": "lease:legacy",
            "lane_ref": "work/legacy",
        }
    )
    _insert_lease_row(
        database,
        legacy,
        payload=legacy_payload
        | {
            "lane_incarnation_id": legacy.lane_incarnation_id,
            "lease_id": legacy.lease_id,
            "lane_ref": legacy.lane_ref,
        },
    )
    observed_unknown = observe_lease(database, legacy.lane_ref)
    assert observed_unknown.state == "unknown"
    assert observed_unknown.lease is None
    assert observed_unknown.row is not None
    assert observed_unknown.row.id == legacy.lease_id
    assert len(observed_unknown.row.payload_sha256) == 64
    assert observed_unknown.record()["error"] == "lane_lease_payload_fields_invalid"

    mismatch = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:mismatch",
            "lease_id": "lease:mismatch",
            "lane_ref": "work/mismatch",
        }
    )
    _insert_lease_row(
        database,
        mismatch,
        row_expires_at=(mismatch.expires_at + timedelta(minutes=1)).isoformat(),
    )
    assert observe_lease(database, mismatch.lane_ref).state == "unknown"


def test_unknown_lease_is_observe_only_for_public_mutation_and_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    fixture = start_adopted_work_lane(
        tmp_path / "unknown-mutation", name="unknown-mutation", holder_ref=holder_ref
    )
    branch = "work/unknown-mutation"
    database = state_database(fixture.worktree)
    initial = _lease_snapshot(fixture.worktree, branch)
    unknown_payload = dict(initial["payload"])
    unknown_payload["claim_id"] = "retired"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(unknown_payload, sort_keys=True), branch),
        )

    mutation = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=initial,
            apply=False,
        ),
    )
    assert mutation["ok"] is False
    assert mutation["required_gaps"] == [f"work_lane_lease_unknown:{branch}"]
    assert observe_lease(database, branch).state == "unknown"

    repo, lane, head, accepted, retirement_database = superseded_work_lane(
        tmp_path / "unknown-retirement", holder_ref=holder_ref
    )
    retired = leases_by_branch(lane)["work/superseded"]
    retired_payload = dict(retired["payload"])
    retired_payload["claim_id"] = "retired"
    with closing(sqlite3.connect(retirement_database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(retired_payload, sort_keys=True), "work/superseded"),
        )
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    retirement = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=head,
            absorbed_by=accepted,
            reason="superseded fixture",
            authorize=True,
            apply=False,
        ),
    )
    assert retirement["ok"] is False
    assert "work_lane_lease_unknown:work/superseded" in retirement["required_gaps"]
    assert observe_lease(retirement_database, "work/superseded").state == "unknown"


def test_full_lease_reissues_preserve_every_undeclared_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    branch = "work/reissue"
    fixture = start_adopted_work_lane(tmp_path / "reissue", name="reissue", holder_ref=holder_ref)
    database = state_database(fixture.worktree)
    initial = _lease_snapshot(fixture.worktree, branch)
    initial_payload = dict(initial["payload"])
    initial_payload["path_scope"] = ["src/**", "tests/**"]
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(initial_payload, sort_keys=True), branch),
        )
    initial = observe_lease(database, branch).record()

    renewed = _apply_lease(
        fixture.worktree,
        database,
        _lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=initial,
            apply=True,
        ),
    )
    _assert_reissue_changes(initial, renewed, "renewed_at", "expires_at")

    offered = _apply_lease(
        fixture.worktree,
        database,
        _lease_request(
            operation="handoff_offer",
            branch=branch,
            holder_ref=holder_ref,
            lease=renewed,
            apply=True,
            target_holder_ref=target_holder_ref,
        ),
    )
    _assert_reissue_changes(renewed, offered, "handoff")

    accepted = _apply_lease(
        fixture.worktree,
        database,
        _lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=holder_ref,
            lease=offered,
            apply=True,
            target_holder_ref=target_holder_ref,
            offer_id=str(offered["offer_id"]),
            holder_quiesced=True,
        ),
    )
    _assert_reissue_changes(
        offered,
        accepted,
        "holder_ref",
        "epoch",
        "renewed_at",
        "expires_at",
        "handoff",
    )

    advanced = advance_lease_head(
        database,
        request=_lease_request(
            operation="advance",
            branch=branch,
            holder_ref=target_holder_ref,
            lease=accepted,
            apply=True,
        ),
        new_head="c" * 40,
    )
    _assert_reissue_changes(accepted, advanced, "expected_head")

    def unexpected_replace(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError

    with monkeypatch.context() as invalid_reissue:
        invalid_reissue.setattr(
            lease_transitions,
            "replace_exact_lease_from_connection",
            unexpected_replace,
        )
        with pytest.raises(ValueError, match="expected_head"):
            advance_lease_head(
                database,
                request=_lease_request(
                    operation="advance",
                    branch=branch,
                    holder_ref=target_holder_ref,
                    lease=advanced,
                    apply=True,
                ),
                new_head="invalid-head",
            )
    assert observe_lease(database, branch).record() == advanced

    resume_fixture = start_adopted_work_lane(
        tmp_path / "resume-reissue", name="resume-reissue", holder_ref=holder_ref
    )
    resume_branch = "work/resume-reissue"
    resume_database = state_database(resume_fixture.worktree)
    expired = _lease_snapshot(resume_fixture.worktree, resume_branch)
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    expired_payload = dict(expired["payload"])
    expired_payload.update(
        issued_at=(expired_at - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired_at - timedelta(seconds=1)).isoformat(),
        expires_at=expired_at.isoformat(),
        path_scope=["src/**", "tests/**"],
    )
    with closing(sqlite3.connect(resume_database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired_at.isoformat(), json.dumps(expired_payload, sort_keys=True), resume_branch),
        )
    expired = observe_lease(resume_database, resume_branch).record()
    resumed = _apply_lease(
        resume_fixture.worktree,
        resume_database,
        _lease_request(
            operation="resume",
            branch=resume_branch,
            holder_ref=holder_ref,
            lease=expired,
            apply=True,
        ),
    )
    _assert_reissue_changes(expired, resumed, "renewed_at", "expires_at")


def test_full_lease_reissue_rejects_legacy_payload(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    now = datetime.now(UTC)
    initial = acquire_lease(
        database,
        lease=LaneLease(
            lane_incarnation_id="lane-incarnation:example",
            lease_id="lease:example",
            lane_ref="work/example",
            holder_ref="agent:test:case:holder",
            epoch=1,
            issued_at=now,
            renewed_at=now,
            expires_at=now + timedelta(days=1),
            expected_head="a" * 40,
            base_change_contract_digest="b" * 64,
            path_scope=(),
        ),
    )
    transition = LeaseTransitionDeclaration(
        id="renew",
        applied_state="renewed",
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "ttl_seconds",
        ),
        actor_field="holder_ref",
    )

    renewed = apply_lease_operation(
        database,
        transition=transition,
        request=_lease_request(
            operation="renew",
            branch="work/example",
            holder_ref="agent:test:case:holder",
            lease=initial,
            apply=True,
        ),
    )

    assert renewed["base_change_contract_digest"] == initial["base_change_contract_digest"]
    assert set(renewed["payload"]) == set(LaneLease.model_fields)
    assert renewed["payload"]["handoff"] is None

    with closing(sqlite3.connect(database)) as connection, connection:
        raw = connection.execute(
            "select payload_json from leases where subject = ?", ("work/example",)
        ).fetchone()[0]
        payload = json.loads(raw)
        payload["claim_id"] = "retired"
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True), "work/example"),
        )
    with pytest.raises(ValueError, match="lease_unknown:work/example"):
        apply_lease_operation(
            database,
            transition=transition,
            request=_lease_request(
                operation="renew",
                branch="work/example",
                holder_ref="agent:test:case:holder",
                lease=renewed,
                apply=True,
            ),
        )


def test_lease_public_transition_matrix_enforces_actor_cas_and_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    target_holder = "agent:test:case:target"
    branch = "work/lease"
    fixture = start_adopted_work_lane(tmp_path / "lease", name="lease", holder_ref=source_holder)
    initial = leases_by_branch(fixture.worktree)[branch]

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    wrong_actor = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="renew", branch=branch, holder_ref=source_holder, lease=initial, apply=True
        ),
    )
    assert wrong_actor["ok"] is False
    assert "lease_actor_mismatch" in wrong_actor["required_gaps"]

    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    renewed = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="renew", branch=branch, holder_ref=source_holder, lease=initial, apply=True
        ),
    )
    assert renewed["ok"] is True
    renewed_lease = renewed["lease"]
    assert isinstance(renewed_lease, dict)
    offered = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="handoff_offer",
            branch=branch,
            holder_ref=source_holder,
            lease=renewed_lease,
            apply=True,
            target_holder_ref=target_holder,
        ),
    )
    assert offered["ok"] is True
    offer = offered["handoff_offer"]
    assert isinstance(offer, dict)

    monkeypatch.setenv("ETHOS_ACTOR", target_holder)
    not_quiesced = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=source_holder,
            lease=offer,
            apply=True,
            target_holder_ref=target_holder,
            offer_id=str(offer["offer_id"]),
            holder_quiesced=False,
        ),
    )
    assert not_quiesced["ok"] is False
    assert "holder_quiescence_confirmation_required" in not_quiesced["required_gaps"]
    accepted = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=source_holder,
            lease=offer,
            apply=True,
            target_holder_ref=target_holder,
            offer_id=str(offer["offer_id"]),
            holder_quiesced=True,
        ),
    )
    assert accepted["ok"] is True
    accepted_lease = accepted["lease"]
    assert isinstance(accepted_lease, dict)
    assert (accepted_lease["holder_ref"], accepted_lease["epoch"]) == (
        target_holder,
        int(offer["epoch"]) + 1,
    )
    replay = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=source_holder,
            lease=offer,
            apply=True,
            target_holder_ref=target_holder,
            offer_id=str(offer["offer_id"]),
            holder_quiesced=True,
        ),
    )
    assert replay["ok"] is False
    assert any("lease_holder_mismatch" in gap for gap in replay["required_gaps"])


def test_lease_effect_rejects_unknown_and_non_applying_requests_without_mutation(
    tmp_path: Path,
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    branch = "work/effect-boundary"
    fixture = start_adopted_work_lane(
        tmp_path / "effect-boundary", name="effect-boundary", holder_ref=holder_ref
    )
    initial = _lease_snapshot(fixture.worktree, branch)
    database = state_database(fixture.worktree)

    non_applying = _lease_request(
        operation="renew",
        branch=branch,
        holder_ref=holder_ref,
        lease=initial,
        apply=False,
    )
    with pytest.raises(ValueError, match=r"^lease_apply_required:renew$"):
        _apply_lease(fixture.worktree, database, non_applying)
    assert _lease_snapshot(fixture.worktree, branch) == initial

    unknown = _lease_request(
        operation="typo_accept",
        branch=branch,
        holder_ref=holder_ref,
        lease=initial,
        apply=True,
        target_holder_ref=target_holder_ref,
    )
    with pytest.raises(ValueError, match=r"^lease_operation_unknown:typo_accept$"):
        apply_lease_operation(
            database,
            transition=_lease_transition(fixture.worktree, "renew"),
            request=unknown,
        )
    assert _lease_snapshot(fixture.worktree, branch) == initial

    forged_payload = _lease_transition(fixture.worktree, "renew").model_dump(mode="python")
    forged_payload["effect_fields"] = _lease_transition(
        fixture.worktree, "handoff_offer"
    ).effect_fields
    forged = LeaseTransitionDeclaration.model_construct(**forged_payload)
    with pytest.raises(ValueError, match=r"^lease_effect_unsupported:renew$"):
        apply_lease_operation(
            database,
            transition=forged,
            request=_lease_request(
                operation="renew",
                branch=branch,
                holder_ref=holder_ref,
                lease=initial,
                apply=True,
                target_holder_ref=target_holder_ref,
            ),
        )
    assert _lease_snapshot(fixture.worktree, branch) == initial


def test_lease_effect_enforces_expiry_cas_handoff_tokens_and_transient_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    branch = "work/effect-cas"
    fixture = start_adopted_work_lane(
        tmp_path / "effect-cas", name="effect-cas", holder_ref=holder_ref
    )
    database = state_database(fixture.worktree)
    initial = _lease_snapshot(fixture.worktree, branch)

    active_resume = _lease_request(
        operation="resume",
        branch=branch,
        holder_ref=holder_ref,
        lease=initial,
        apply=True,
    )
    with pytest.raises(ValueError, match=f"^lease_not_expired:{branch}$"):
        _apply_lease(fixture.worktree, database, active_resume)

    expired = datetime.now(UTC) - timedelta(seconds=1)
    expired_payload = dict(initial["payload"])
    expired_payload.update(
        issued_at=(expired - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired - timedelta(seconds=1)).isoformat(),
        expires_at=expired.isoformat(),
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired.isoformat(), json.dumps(expired_payload, sort_keys=True), branch),
        )
    expired_lease = observe_lease(database, branch).record()
    expired_renew = _lease_request(
        operation="renew",
        branch=branch,
        holder_ref=holder_ref,
        lease=expired_lease,
        apply=True,
    )
    with pytest.raises(ValueError, match=f"^lease_expired:{branch}$"):
        _apply_lease(fixture.worktree, database, expired_renew)
    resumed = _apply_lease(
        fixture.worktree,
        database,
        _lease_request(
            operation="resume",
            branch=branch,
            holder_ref=holder_ref,
            lease=expired_lease,
            apply=True,
        ),
    )
    assert resumed["expires_at"] > expired.isoformat()

    _assert_stale_lease_dimensions(fixture.worktree, database, branch, holder_ref, resumed)

    invalid_holder = _lease_request(
        operation="renew",
        branch=branch,
        holder_ref="invalid-holder",
        lease=resumed,
        apply=True,
    )
    with pytest.raises(ValueError, match=r"^holder_ref must have four non-empty segments$"):
        _apply_lease(fixture.worktree, database, invalid_holder)

    offer = _apply_lease(
        fixture.worktree,
        database,
        _lease_request(
            operation="handoff_offer",
            branch=branch,
            holder_ref=holder_ref,
            lease=resumed,
            apply=True,
            target_holder_ref=target_holder_ref,
        ),
    )
    unquiesced = _lease_request(
        operation="handoff_accept",
        branch=branch,
        holder_ref=holder_ref,
        lease=offer,
        apply=True,
        target_holder_ref=target_holder_ref,
        offer_id=str(offer["offer_id"]),
    )
    with pytest.raises(ValueError, match=f"^lease_handoff_holder_not_quiesced:{branch}$"):
        _apply_lease(fixture.worktree, database, unquiesced)

    _assert_stale_handoff_tokens(
        fixture.worktree,
        database,
        branch,
        holder_ref,
        target_holder_ref,
        offer,
    )

    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    public = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=offer,
            apply=True,
        ),
    )
    assert "receipt" not in public
    assert (public["ok"], public["state"], public["branch"]) == (True, "renewed", branch)
    assert public["handoff_offer"] == {}
    assert set(public["lease"]) >= {
        "lease_id",
        "holder_ref",
        "epoch",
        "lane_ref",
        "expected_head",
        "expires_at",
        "payload_sha256",
    }


def _assert_stale_lease_dimensions(
    root: Path,
    database: Path,
    branch: str,
    holder_ref: str,
    lease: dict[str, Any],
) -> None:
    for field, value, token in (
        ("lease_id", "lease:stale", "lease_id_stale"),
        ("expected_epoch", int(lease["epoch"]) + 1, "lease_epoch_stale"),
        ("expect_head", "f" * 40, "lease_head_stale"),
        ("expected_expires_at", "1970-01-01T00:00:00+00:00", "lease_maintenance_candidate_drift"),
        ("expected_payload_sha256", "0" * 64, "lease_maintenance_candidate_drift"),
    ):
        request = _lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=lease,
            apply=True,
            **{field: value},
        )
        with pytest.raises(ValueError, match=f"^{token}"):
            _apply_lease(root, database, request)


def _assert_stale_handoff_tokens(
    root: Path,
    database: Path,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    offer: dict[str, Any],
) -> None:
    for field, value, token in (
        ("offer_id", "handoff-offer:stale", "lease_handoff_offer_stale"),
        ("target_holder_ref", "agent:test:case:other", "lease_handoff_target_mismatch"),
    ):
        values: dict[str, object] = {
            "target_holder_ref": target_holder_ref,
            "offer_id": str(offer["offer_id"]),
            "holder_quiesced": True,
        }
        values[field] = value
        request = _lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=holder_ref,
            lease=offer,
            apply=True,
            **values,
        )
        with pytest.raises(ValueError, match=f"^{token}"):
            _apply_lease(root, database, request)
