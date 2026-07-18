from __future__ import annotations

# ruff: noqa: ARG005, PT018
import json
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

import ethos.adapters.admission.core as admission
import ethos.adapters.admission.prewrite as prewrite
import ethos.adapters.admission.transitions as transitions
import ethos.adapters.mutation.lane_lifecycle.handoff.core as handoff
import ethos.adapters.mutation.lane_lifecycle.handoff.package as handoff_package
import ethos.adapters.mutation.lane_lifecycle.lease as lease_ops
import ethos.adapters.store.state.lease.lifecycle.core as lease_state
import ethos.adapters.store.state.lease.projection as lease_projection
from ethos_core.contracts.lifecycle.core import LeaseFacts
from ethos_core.contracts.lifecycle.core import lease_transition
from ethos_core.contracts.lifecycle.core import reduce_lease_request
from ethos_core.normalization.core import string_sequence

BRANCH = "work/example"
HEAD = "a" * 40
HOLDER = "agent:test:case:holder"
TARGET_HOLDER = "agent:test:case:target"
LEASE_ID = "lease:one"


def _lease_payload() -> dict[str, object]:
    return {
        "normalization_state": "normalized",
        "holder_ref": HOLDER,
        "lease_id": LEASE_ID,
        "epoch": 1,
        "expected_head": HEAD,
    }


def _lease_facts(**changes: object) -> LeaseFacts:
    return LeaseFacts(
        **{
            "role": "work_lane",
            "current_branch": BRANCH,
            "current_head": "a",
            "branch": BRANCH,
            "expect_head": "a",
            "lease_id": "lease",
            "epoch": 1,
            "ttl_seconds": 1,
            "offer_id": "",
            "apply": False,
            **changes,
        }
    )


def _handoff_manifest(**changes: object) -> dict[str, object]:
    return {
        "package_id": "handoff:one",
        "source_lane_ref": BRANCH,
        "source_head": HEAD,
        "target_holder_ref": TARGET_HOLDER,
        **changes,
    }


def _patch_handoff_manifest(monkeypatch, manifest: dict[str, object]) -> None:
    monkeypatch.setattr(
        handoff.handoff_package, "verified_handoff_manifest", lambda **_: (manifest, [])
    )


def test_handoff_validation_helper_matrix(tmp_path: Path) -> None:
    assert handoff._holder_ref_gaps("bad", "also-bad") == [
        "holder_ref_invalid",
        "target_holder_ref_invalid",
    ]  # noqa: RUF100, SLF001 - exact private branch coverage
    binding = {
        "branch": BRANCH,
        "holder_ref": HOLDER,
        "lease_id": LEASE_ID,
        "epoch": 1,
    }
    for facts, expected in (
        (
            {
                "status": {"role": "accepted_root", "branch": "work/other"},
                "head": HEAD,
                "expect_head": "",
                "lease": {},
            },
            [
                "work_lane_required",
                "lane_branch_mismatch",
                "expect_head_required",
                "lease_holder_mismatch",
                "lease_id_stale",
                "lease_epoch_stale",
                "lease_head_stale",
            ],
        ),
        (
            {
                "status": {"role": "work_lane", "branch": BRANCH},
                "head": "a",
                "expect_head": "b",
                "lease": {**_lease_payload(), "expected_head": "a"},
            },
            ["expect_head_mismatch"],
        ),
    ):
        assert handoff._export_binding_gaps(**binding, **facts) == expected  # noqa: RUF100, SLF001 - exact private branch coverage
    for dirty_paths, disposition, expected in (
        (("README.md",), "", ["dirty_disposition_required"]),
        ((), "preserved", ["dirty_disposition_mismatch"]),
        (("README.md",), "clean", ["dirty_disposition_mismatch"]),
        ((), "invalid", ["dirty_disposition_invalid"]),
    ):
        assert handoff._dirty_disposition_gaps(dirty_paths, disposition) == expected  # noqa: RUF100, SLF001 - exact private branch coverage
    context = tmp_path / "context.md"
    for content, context_text, expected in (
        ("context\n", "also", ("", "handoff_context_ambiguous")),
        ("context\n", "", ("context\n", "")),
        ("", "", ("", "handoff_context_required")),
    ):
        context.write_text(content, encoding="utf-8")
        assert handoff._handoff_context(context_text=context_text, context_file=context) == expected  # noqa: RUF100, SLF001 - exact private branch coverage
    assert handoff._handoff_context(context_text="", context_file=tmp_path / "missing.md") == (
        "",
        "handoff_context_file_unreadable",
    )  # noqa: RUF100, SLF001 - exact private branch coverage


def test_handoff_state_and_json_helpers(tmp_path: Path, monkeypatch) -> None:
    accepted = tmp_path / "accepted"
    accepted.mkdir()
    status = {
        "worktrees": [
            "malformed",
            {"role": "work_lane", "path": tmp_path.as_posix()},
            {"role": "accepted_root", "path": accepted.as_posix()},
        ]
    }
    monkeypatch.setattr(
        handoff,
        "active_leases",
        lambda _db: [
            {"subject": "work/example", "lease_id": "one"},
            {"subject": "work/other", "lease_id": "two"},
        ],
    )
    for probe, expected_root in (
        (status, accepted),
        ({"worktrees": ["bad"]}, tmp_path),
        ({"worktrees": "bad"}, tmp_path),
        ({"worktrees": []}, tmp_path),
    ):
        assert (
            handoff._current_lease(status=probe, repo=tmp_path, branch=BRANCH)["lease_id"] == "one"
        )  # noqa: RUF100, SLF001 - exact private branch coverage
        assert handoff._state_root(status=probe, repo=tmp_path) == expected_root  # noqa: RUF100, SLF001 - exact private branch coverage

    gaps: list[str] = []
    for path, content, expected_gaps in (
        (tmp_path / "missing.json", None, ["invalid"]),
        (tmp_path / "array.json", "[]", ["invalid", "invalid"]),
    ):
        if content is not None:
            path.write_text(content, encoding="utf-8")
        assert handoff._json_mapping(path, gap="invalid", gaps=gaps) == {}  # noqa: RUF100, SLF001 - exact private branch coverage
        assert gaps == expected_gaps


def test_handoff_orchestration_catches_effect_failures(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(handoff, "repo_root", lambda root: root)
    monkeypatch.setattr(
        handoff,
        "workspace_status",
        lambda _root: {"role": "work_lane", "branch": BRANCH, "dirty": False},
    )
    monkeypatch.setattr(
        handoff,
        "_git_value",
        lambda _root, *args: HEAD if args == ("rev-parse", "HEAD") else "b" * 40,
    )
    monkeypatch.setattr(handoff, "changed_paths", lambda _root: ())
    monkeypatch.setattr(handoff, "_current_lease", lambda **_: _lease_payload())
    monkeypatch.setattr(
        handoff.handoff_package,
        "write_handoff_package",
        lambda **_: (_ for _ in ()).throw(ValueError("export-failed")),
    )
    exported = handoff.export_cross_host_handoff(
        root=tmp_path,
        branch="work/example",
        holder_ref=HOLDER,
        target_holder_ref=TARGET_HOLDER,
        lease_id=LEASE_ID,
        epoch=1,
        expect_head="a" * 40,
        context_text="context",
        context_file=None,
        output_root=None,
        dirty_disposition="clean",
        apply=True,
    )
    assert exported["required_gaps"] == ["handoff_export_failed:export-failed"]

    manifest = _handoff_manifest()
    _patch_handoff_manifest(monkeypatch, manifest)
    monkeypatch.setattr(handoff, "workspace_status", lambda _root: {"role": "accepted_root"})
    monkeypatch.setattr(handoff, "_branch_exists", lambda *_: False)
    monkeypatch.setattr(
        handoff.handoff_package,
        "apply_handoff_import",
        lambda **_: (_ for _ in ()).throw(ValueError("import-failed")),
    )
    imported = handoff.import_cross_host_handoff(
        root=tmp_path,
        package=tmp_path / "package",
        target_holder_ref=TARGET_HOLDER,
        apply=True,
    )
    assert imported["required_gaps"] == ["handoff_import_failed:import-failed"]


def test_handoff_import_and_revoke_validation_edges(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(handoff, "repo_root", lambda root: root)
    monkeypatch.setattr(
        handoff,
        "workspace_status",
        lambda _root: {"role": "work_lane", "branch": "work/other", "dirty": True},
    )
    manifest = _handoff_manifest(source_lease_binding={})
    _patch_handoff_manifest(monkeypatch, manifest)
    monkeypatch.setattr(handoff, "_branch_exists", lambda *_: True)
    imported = handoff.import_cross_host_handoff(
        root=tmp_path,
        package=tmp_path / "package",
        target_holder_ref="bad",
        apply=False,
    )
    assert imported["required_gaps"] == [
        "target_holder_ref_invalid",
        "handoff_target_holder_mismatch",
        "handoff_import_requires_accepted_root",
        "handoff_import_requires_clean_destination",
        "handoff_destination_branch_exists",
    ]

    ack = tmp_path / "ack.json"
    ack.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(handoff, "_git_value", lambda *_args: "b" * 40)
    revoked = handoff.revoke_cross_host_source(
        root=tmp_path,
        package=tmp_path / "package",
        acknowledgement=ack,
        holder_ref=HOLDER,
        lease_id=LEASE_ID,
        epoch=1,
        expect_head="a" * 40,
        apply=False,
    )
    assert {
        "handoff_source_lane_mismatch",
        "expect_head_mismatch",
        "handoff_source_holder_mismatch",
        "handoff_source_lease_mismatch",
        "handoff_source_epoch_mismatch",
        "handoff_source_head_mismatch",
        "handoff_acknowledgement_package_mismatch",
        "handoff_acknowledgement_head_mismatch",
        "handoff_acknowledgement_lease_boundary_invalid",
    } == set(revoked["required_gaps"])


def test_handoff_revoke_effect_failure_and_success(tmp_path: Path, monkeypatch) -> None:
    manifest = _handoff_manifest(
        source_lease_binding={
            "holder_ref": HOLDER,
            "lease_id": LEASE_ID,
            "epoch": 1,
            "expected_head": HEAD,
        }
    )
    ack = tmp_path / "ack.json"
    ack.write_text(
        json.dumps(
            {
                "acknowledgement_id": "ack:one",
                "package_id": "handoff:one",
                "destination_head": HEAD,
                "source_lease_transferred": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(handoff, "repo_root", lambda root: root)
    monkeypatch.setattr(
        handoff,
        "workspace_status",
        lambda _root: {"role": "work_lane", "branch": BRANCH},
    )
    _patch_handoff_manifest(monkeypatch, manifest)
    monkeypatch.setattr(handoff, "_git_value", lambda *_: HEAD)
    monkeypatch.setattr(handoff, "_state_root", lambda **_: tmp_path)
    monkeypatch.setattr(
        handoff,
        "revoke_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("stale")),
    )

    def revoke() -> dict[str, object]:
        return handoff.revoke_cross_host_source(
            root=tmp_path,
            package=tmp_path / "package",
            acknowledgement=ack,
            holder_ref=HOLDER,
            lease_id=LEASE_ID,
            epoch=1,
            expect_head="a" * 40,
            apply=True,
        )

    failed = revoke()
    assert failed["required_gaps"] == ["stale"]
    monkeypatch.setattr(handoff, "revoke_lease", lambda *_args, **_kwargs: {"revoked": True})
    assert revoke()["state"] == "source_revoked"


def test_handoff_package_manifest_and_effect_edges(tmp_path: Path, monkeypatch) -> None:
    assert handoff_package.verified_handoff_manifest(
        package=tmp_path / "missing", root=tmp_path
    ) == ({}, ["handoff_manifest_missing"])
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text("{", encoding="utf-8")
    assert handoff_package.verified_handoff_manifest(package=package, root=tmp_path)[1] == [
        "handoff_manifest_invalid_json"
    ]
    (package / "manifest.json").write_text("[]", encoding="utf-8")
    assert handoff_package.verified_handoff_manifest(package=package, root=tmp_path)[1] == [
        "handoff_manifest_invalid"
    ]
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    "bad",
                    {"path": "missing.txt", "sha256": "a" * 64},
                    {"path": "wrong.txt", "sha256": "a" * 64},
                ]
            }
        ),
        encoding="utf-8",
    )
    (package / "wrong.txt").write_text("wrong", encoding="utf-8")
    monkeypatch.setattr(
        handoff_package,
        "validate_schema_instance",
        lambda *args, **kwargs: {"ok": False, "required_gaps": ["schema"]},
    )
    _, gaps = handoff_package.verified_handoff_manifest(package=package, root=tmp_path)
    assert gaps == [
        "handoff_manifest_invalid:schema",
        "handoff_artifact_invalid",
        "handoff_artifact_missing:missing.txt",
        "handoff_artifact_digest_mismatch:wrong.txt",
    ]

    monkeypatch.setattr(
        handoff_package.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stderr=b"diff failed"),
    )
    with pytest.raises(subprocess.SubprocessError, match="diff failed"):
        handoff_package._preserve_dirty_work(repo=tmp_path, package_dir=tmp_path)  # noqa: RUF100, SLF001 - exact private branch coverage
    monkeypatch.setattr(
        handoff_package.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stderr="run failed"),
    )
    with pytest.raises(subprocess.SubprocessError, match="run failed"):
        handoff_package._run(tmp_path, "false")  # noqa: RUF100, SLF001 - exact private branch coverage


@pytest.mark.parametrize("fail_at", [1, 2])
def test_handoff_import_rolls_back_partial_creation(
    tmp_path: Path, monkeypatch, fail_at: int
) -> None:
    calls = 0

    def fail_run(_root: Path, *args: str) -> None:
        nonlocal calls
        calls += 1
        if calls == fail_at:
            raise subprocess.SubprocessError("failed")  # noqa: EM101, RUF100 - machine-readable gap token is the exception contract

    monkeypatch.setattr(handoff_package, "_run", fail_run)
    monkeypatch.setattr(
        handoff_package.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    with pytest.raises(subprocess.SubprocessError, match="failed"):
        handoff_package.apply_handoff_import(
            destination=tmp_path / "destination",
            package=tmp_path / "package",
            manifest={
                "source_lane_ref": "work/example",
                "source_head": "a" * 40,
                "package_id": "handoff:one",
            },
            target_holder_ref="agent:test:case:target",
        )


def test_handoff_package_existing_output_and_schema_failure(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "output"
    output.mkdir()
    package_id = "handoff:fixed"
    existing = output / package_id
    existing.mkdir()
    (existing / "old").write_text("old", encoding="utf-8")

    def fake_run(root: Path, *args: str) -> None:
        target = Path(args[-2] if args[:3] == ("git", "bundle", "create") else args[-1])
        if args[:3] == ("git", "bundle", "create"):
            target.write_text("bundle", encoding="utf-8")

    monkeypatch.setattr(handoff_package, "_run", fake_run)
    monkeypatch.setattr(handoff_package, "_handoff_package_id", lambda **kwargs: package_id)
    monkeypatch.setattr(
        handoff_package,
        "validate_schema_instance",
        lambda *args, **kwargs: {"ok": False, "required_gaps": ["schema"]},
    )
    with pytest.raises(ValueError, match="handoff_manifest_invalid:schema"):
        handoff_package.write_handoff_package(
            repo=tmp_path,
            branch="work/example",
            head="a" * 40,
            tree="b" * 40,
            holder_ref=HOLDER,
            target_holder_ref=TARGET_HOLDER,
            lease_id=LEASE_ID,
            epoch=1,
            context="context",
            output_root=output,
            dirty_disposition="clean",
            dirty_paths=(),
        )
    assert not (existing / "old").exists()


def test_handoff_restore_and_empty_preservation_edges(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(handoff_package, "_run", lambda _root, *args: calls.append(args))
    for manifest, expected_calls in (
        ({"dirty_disposition": "clean"}, []),
        (
            {
                "dirty_disposition": "preserved",
                "artifacts": [
                    {"kind": "tracked_patch", "path": "tracked.patch"},
                    {"kind": "untracked_archive", "path": "untracked.tar"},
                ],
            },
            [
                ("git", "apply", "--binary", (tmp_path / "tracked.patch").as_posix()),
                ("tar", "-xf", (tmp_path / "untracked.tar").as_posix()),
            ],
        ),
        ({"dirty_disposition": "preserved", "artifacts": []}, []),
    ):
        calls.clear()
        handoff_package._restore_preserved_work(
            package=tmp_path, manifest=manifest, worktree=tmp_path
        )
        assert calls == expected_calls

    monkeypatch.setattr(
        handoff_package.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stderr=b""),
    )
    monkeypatch.setattr(handoff_package, "_git_lines", lambda *args: [])
    assert handoff_package._preserve_dirty_work(repo=tmp_path, package_dir=tmp_path) == []
    assert not (tmp_path / "tracked.patch").exists()


@pytest.mark.parametrize(
    ("operation", "facts", "expected_state", "expected_gaps"),
    [
        (
            "handoff_accept",
            _lease_facts(
                role="accepted_root",
                current_branch="work/other",
                expect_head="",
                lease_id="",
                epoch=None,
                ttl_seconds=0,
            ),
            "blocked",
            (
                "work_lane_required",
                "lane_branch_mismatch",
                "expect_head_required",
                "lease_id_required",
                "lease_epoch_required",
                "lease_ttl_invalid",
                "handoff_offer_id_required",
            ),
        ),
        ("renew", _lease_facts(), "planned", ()),
        ("renew", _lease_facts(expect_head="b"), "blocked", ("expect_head_mismatch",)),
    ],
)
def test_lease_request_reducer_matrix(
    operation: str,
    facts: LeaseFacts,
    expected_state: str,
    expected_gaps: tuple[str, ...],
) -> None:
    result = reduce_lease_request(lease_transition(operation), facts)
    assert result.state == expected_state
    assert result.gaps == expected_gaps


def test_lease_operation_validation_and_dispatch_edges(tmp_path: Path, monkeypatch) -> None:
    state, gaps = lease_ops._lease_expected_state(
        repo=tmp_path,
        branch=BRANCH,
        holder_ref="bad",
        lease_id="",
        epoch=None,
        expect_head="",
        target_holder_ref="",
        offer_id="",
    )
    assert state["epoch"] == 0 and gaps == ("holder_ref_invalid",)
    monkeypatch.setattr(
        lease_ops,
        "_apply_lease_lifecycle_operation",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("stale")),
    )
    result = {"ok": True, "state": "applying", "required_gaps": []}
    lease_ops._apply_lease_effect(
        result=result,
        db_path=tmp_path / "state.sqlite",
        operation="renew",
        branch="work/example",
        expected_state={
            "holder_ref": "agent:test:case:holder",
            "target_holder_ref": "",
        },
        offer_id="",
        lease_id="lease:one",
        epoch=1,
        expect_head="a" * 40,
        holder_quiesced=False,
        ttl_seconds=60,
    )
    assert result["required_gaps"] == ["stale"]
    monkeypatch.undo()
    with pytest.raises(ValueError, match="lease_operation_unknown:bad"):
        lease_ops._apply_lease_lifecycle_operation(  # noqa: RUF100, SLF001 - exact dispatch-error coverage
            db_path=tmp_path / "state.sqlite",
            operation="bad",
            branch=BRANCH,
            holder_ref=HOLDER,
            target_holder_ref="",
            offer_id="",
            lease_id=LEASE_ID,
            epoch=1,
            expect_head=HEAD,
            holder_quiesced=False,
            ttl_seconds=60,
        )


def test_lease_state_root_and_core_failure_edges(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted"
    accepted.mkdir()
    for status, expected_root in (
        (
            {
                "worktrees": [
                    "bad",
                    {"role": "accepted_root", "path": accepted.as_posix()},
                ]
            },
            accepted,
        ),
        ({"worktrees": []}, tmp_path),
        ({"worktrees": "bad"}, tmp_path),
        (
            {"worktrees": ["bad", {"role": "work_lane", "path": accepted.as_posix()}]},
            tmp_path,
        ),
    ):
        assert lease_ops._state_root(status, tmp_path) == expected_root

    db = tmp_path / "state.sqlite"
    lease = lease_state.acquire_lease(
        db,
        subject="work/example",
        holder_ref=HOLDER,
        ttl_seconds=60,
        payload={"expected_head": "a" * 40},
    )
    lease_request = {
        "subject": "work/example",
        "holder_ref": str(lease["holder_ref"]),
        "expected_lease_id": str(lease["lease_id"]),
        "expected_epoch": int(lease["epoch"]),
        "expected_head": "a" * 40,
    }
    with pytest.raises(ValueError, match="lease_resume_blocked_by_decision"):
        lease_state.resume_lease(db, contrary_decision=True, **lease_request)
    with pytest.raises(ValueError, match="lease_handoff_holder_not_quiesced"):
        lease_state.accept_lease_handoff(
            db,
            target_holder_ref="agent:test:case:target",
            offer_id="offer",
            holder_quiesced=False,
            **{key: value for key, value in lease_request.items() if key != "holder_ref"},
        )
    expired_db = tmp_path / "expired.sqlite"
    expired = lease_state.acquire_lease(
        expired_db,
        subject="work/expired",
        holder_ref=HOLDER,
        ttl_seconds=-1,
        payload={"expected_head": "a" * 40},
    )
    expired_request = {
        "subject": "work/expired",
        "holder_ref": str(expired["holder_ref"]),
        "expected_lease_id": str(expired["lease_id"]),
        "expected_epoch": int(expired["epoch"]),
        "expected_head": "a" * 40,
    }
    with pytest.raises(ValueError, match="lease_expired"):
        lease_state.renew_lease(expired_db, **expired_request)

    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "update leases set expires_at = ?",
            ((datetime.now(UTC) + timedelta(hours=1)).isoformat(),),
        )
        connection.commit()
    with pytest.raises(ValueError, match="lease_not_expired"):
        lease_state.resume_lease(db, **lease_request)


def test_lease_core_ambiguous_missing_and_time_edges(tmp_path: Path) -> None:
    db = tmp_path / "state.sqlite"
    lease_state.acquire_lease(
        db,
        subject="work/one",
        holder_ref="agent:test:case:holder",
    )
    with closing(sqlite3.connect(db)) as connection:
        with pytest.raises(ValueError, match="work_lane_missing_lease"):
            lease_state._sole_subject_row(connection, "work/missing")
        row = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            ("work/one",),
        ).fetchone()
        assert row is not None
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)",
            ("lease:duplicate", "work/one", row[2], row[3], row[4]),
        )
        connection.commit()
        with pytest.raises(ValueError, match="lane_lease_ambiguous"):
            lease_state._sole_subject_row(connection, "work/one")

    with pytest.raises(ValueError, match="lane_lease_legacy_ambiguous"):
        lease_state._expect_normalized({}, "work/one")
    assert lease_state._is_expired("invalid") is True
    assert lease_state._is_expired("2099-01-01T00:00:00") is False
    for value, expected in ((True, 0), ("2", 2), ("bad", 0), (object(), 0)):
        assert lease_projection.integer_value(value) == expected


def test_admission_and_prewrite_normalization_edges(tmp_path: Path, monkeypatch) -> None:
    assert (
        admission.work_lane_ref_transition_report(  # noqa: RUF100, SLF001 - exact admission state coverage
            root=tmp_path,
            phase="prepared",
            ref_name="refs/heads/work/new",
            old_value="0" * 40,
            new_value=HEAD,
        )["state"]
        == "admitted"
    )
    assert transitions._work_lane_lease_transition_gaps(
        branch="work/example", lease={}, actor="", old_value="a"
    ) == ["work_lane_missing_lease:work/example"]
    assert transitions._work_lane_lease_transition_gaps(
        branch="work/example",
        lease={"normalization_state": "bad", "holder_ref": "", "expected_head": "b"},
        actor="agent",
        old_value="a",
    ) == [
        "lane_lease_legacy_ambiguous:work/example",
        "lease_holder_mismatch:work/example",
        "lease_generation_missing:work/example",
        "lease_head_stale:b!=a",
    ]
    for worktrees, expected_db in (
        ([], tmp_path / ".ethos/state/state.sqlite"),
        (
            [
                {"role": "work_lane", "path": tmp_path.as_posix()},
                {"role": "accepted_root", "path": (tmp_path / "accepted").as_posix()},
            ],
            tmp_path / "accepted/.ethos/state/state.sqlite",
        ),
    ):
        assert transitions._control_state_db(worktrees, tmp_path) == expected_db

    monkeypatch.setattr(transitions, "worktree_records", lambda *_, **__: [])
    monkeypatch.setattr(
        transitions, "leases_by_branch", lambda *_, **__: {BRANCH: _lease_payload()}
    )
    monkeypatch.setattr(transitions.os, "environ", {"ETHOS_ACTOR": HOLDER})
    monkeypatch.setattr(
        transitions,
        "advance_lease_head",
        lambda *_, **__: (_ for _ in ()).throw(ValueError("stale")),
    )
    failed = transitions.work_lane_ref_transition_report(
        root=tmp_path,
        phase="committed",
        ref_name="refs/heads/work/example",
        old_value="a" * 40,
        new_value="b" * 40,
    )
    assert failed["state"] == "repair_required"

    for lease, actor, current_head, expected_reason in (
        ({}, "", "", "lane_lease_legacy_ambiguous:work/example"),
        (
            {"normalization_state": "normalized", "holder_ref": "other"},
            "actor",
            "",
            "lease_holder_mismatch:work/example",
        ),
        (
            {"normalization_state": "normalized", "holder_ref": "actor"},
            "actor",
            "",
            "lease_generation_missing:work/example",
        ),
        (
            {
                "normalization_state": "normalized",
                "holder_ref": "actor",
                "lease_id": "lease",
                "epoch": 1,
                "expected_head": "other",
            },
            "actor",
            "head",
            "lease_head_stale:work/example",
        ),
    ):
        assert (
            prewrite._lease_binding_reason(
                branch=BRANCH, lease=lease, actor=actor, current_head=current_head
            )
            == expected_reason
        )


def test_string_sequence_normalizes_tuples_and_rejects_scalars() -> None:
    assert string_sequence(("a", 2)) == ["a", "2"] and string_sequence("bad") == []
