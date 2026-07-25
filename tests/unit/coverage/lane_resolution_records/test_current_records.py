from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.current.core as current_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
import ethos.adapters.mutation.resolution.records.current.validation.core as current_validation
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
import ethos.adapters.mutation.resolution.records.roots as resolution_roots
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import canonical_record_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import historical_record_roots
from ethos.surface.cli.lane.resolution import _default_decision_path
from ethos_core.contracts.resolution.closeout import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"
_REBOUND_ERROR = "rebound"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _decision() -> dict[str, object]:
    observation = LaneObservation(
        lane_ref="work/20260724-record-edges",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:record-edges",
        holder_ref="",
        path="/tmp/record-edges",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )
    return LaneResolutionDecision(
        decision_id=_DECISION_ID,
        disposition="block",
        observation=observation,
        evidence_refs=("evidence:record-edges",),
        chronicle_ref="evidence/chronicle/record-edges.md",
        chronicle_digest="d" * 64,
        recovery_plan="Keep the exact lane unchanged.",
        reason="Exercise strict current inventory.",
    ).to_payload()


def _manifest() -> dict[str, object]:
    return {
        "decision_id": _DECISION_ID,
        "lane_ref": "work/20260724-record-edges",
        "head": "a" * 40,
        "observation_digest": "e" * 64,
        "bundle_sha256": "f" * 64,
        "patch_sha256": "0" * 64,
        "untracked_archive_sha256": "",
        "source_lease_transferred": False,
    }


def _receipt() -> dict[str, object]:
    return LaneResolutionReceipt(
        schema_version=3,
        receipt_id="lane-resolution-receipt:record-edges",
        decision_id=_DECISION_ID,
        completed=True,
        state="retired",
        observation_digest="e" * 64,
        reconciliation_required=False,
        lane_ref="work/20260724-record-edges",
        head="a" * 40,
        preservation_package="",
        preservation_manifest_sha256="",
        mints_authority=False,
    ).to_payload()


def _clear_receipt() -> dict[str, object]:
    return LaneResolutionClearReceipt(
        schema_version=1,
        clear_receipt_id="lane-resolution-clear-receipt:record-edges",
        decision_id=_DECISION_ID,
        manifest_sha256="f" * 64,
        chronicle_ref="evidence/chronicle/record-edges-clear.md",
        chronicle_digest="d" * 64,
        reason="Clear the exact retained package.",
        completed=True,
        mints_authority=False,
    ).to_payload()


def _reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-ownerless", "a" * 40
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservation_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _current_payload(category: str) -> dict[str, object]:
    return {
        "decisions": _decision,
        "manifests": _manifest,
        "receipts": _receipt,
        "clears": _clear_receipt,
        "reservations": _reservation,
    }[category]()


def _current_payload_path(root: Path, category: str, *, name: str = "record") -> Path:
    record_root = current_record_root(root)
    if category == "manifests":
        return record_root / name / "manifest.json"
    return record_root / category / f"{name}.json"


def _write_current_payload(
    root: Path,
    category: str,
    content: str,
    *,
    name: str = "record",
) -> Path:
    path = _current_payload_path(root, category, name=name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _preserved_case(repo: Path, lane: Path) -> dict[str, object]:
    (lane / "README.md").write_text("# preserved record edge\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve a coherent current-record baseline.",
        evidence_refs=("evidence:record-edges",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-record-edges", token="preserve"
        ),
        recovery_plan="Retain the exact observed bytes.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["ok"] is True
    return applied


def _valid_target(tmp_path: Path, category: str) -> tuple[Path, Path, dict[str, object], int]:
    if category == "decisions":
        repo = init_repo(tmp_path / "repo")
        payload = _decision()
        target = current_record_root(repo) / "decisions" / "case.json"
        target.parent.mkdir(parents=True)
        target.write_text(_canonical_json(payload), encoding="utf-8")
        expected_invalid = 1
    elif category == "reservations":
        repo = init_repo(tmp_path / "repo")
        payload = _reservation()
        target = reservation_store.ownerless_closeout_reservation_path(
            repo,
            str(payload["target_digest"]),
        )
        target.parent.mkdir(parents=True)
        target.write_text(_canonical_json(payload), encoding="utf-8")
        expected_invalid = 1
    else:
        repo, lane = orphan_work_lane(tmp_path)
        applied = _preserved_case(repo, lane)
        decision_id = str(applied["receipt"]["decision_id"])
        if category == "manifests":
            target = Path(str(applied["preservation_package"]["path"])) / "manifest.json"
        elif category == "receipts":
            target = record_store.receipt_path(repo, decision_id)
        else:
            package = Path(str(applied["preservation_package"]["path"]))
            cleared = clear_lane_resolution_package(
                root=repo,
                request=LaneResolutionClearRequest(
                    decision_id=decision_id,
                    expect_manifest_sha256=hashlib.sha256(
                        (package / "manifest.json").read_bytes()
                    ).hexdigest(),
                    chronicle_ref=write_chronicle_decision(
                        repo,
                        topic="lane-resolution-record-edges",
                        token="clear-preservation",
                    ),
                    reason="Materialize a coherent terminal clear baseline.",
                    break_glass=True,
                    confirm_irreversible=True,
                    apply=True,
                ),
            )
            assert cleared["ok"] is True
            target = record_store.clear_receipt_path(repo, decision_id)
        payload = json.loads(target.read_text(encoding="utf-8"))
        expected_invalid = 2
    baseline = lane_resolution_inventory(root=repo)
    assert baseline["summary"]["invalid_current_record_count"] == 0
    return repo, target, payload, expected_invalid


def _corrupt_payload(category: str, payload: dict[str, object], corruption: str) -> str:
    if corruption == "malformed_json":
        return "{\n"
    if corruption == "non_object":
        return _canonical_json([])
    corrupted = dict(payload)
    if corruption == "wrong_version":
        corrupted["schema_version"] = 99
    elif corruption == "extra_field":
        corrupted["unexpected"] = "field"
    elif corruption == "invalid_digest_or_invariant":
        field, value = {
            "decisions": ("observation_digest", "0" * 64),
            "manifests": ("source_lease_transferred", True),
            "receipts": ("observation_digest", "g" * 64),
            "clears": ("manifest_sha256", "g" * 64),
            "reservations": ("target_digest", "f" * 64),
        }[category]
        corrupted[field] = value
    else:
        raise AssertionError(corruption)
    return _canonical_json(corrupted)


@pytest.mark.parametrize(
    "category",
    ["decisions", "manifests", "receipts", "clears", "reservations"],
)
@pytest.mark.parametrize(
    "corruption",
    [
        "malformed_json",
        "non_object",
        "wrong_version",
        "extra_field",
        "invalid_digest_or_invariant",
    ],
)
def test_inventory_blocks_each_invalid_current_physical_payload(
    tmp_path: Path,
    category: str,
    corruption: str,
) -> None:
    repo, target, payload, expected_invalid = _valid_target(tmp_path, category)
    target.write_text(_corrupt_payload(category, payload, corruption), encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["state"] == "blocked"
    assert inventory["summary"]["invalid_current_record_count"] == expected_invalid
    assert target.absolute().as_posix() in inventory["invalid_current_record_paths"]
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


def test_inventory_blocks_noncanonical_but_semantically_valid_current_bytes(
    tmp_path: Path,
) -> None:
    repo, target, payload, expected_invalid = _valid_target(tmp_path, "receipts")
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == expected_invalid
    assert target.absolute().as_posix() in inventory["invalid_current_record_paths"]
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


def test_inventory_counts_invalid_physical_payloads_not_decision_identifiers(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    payload = _decision()
    payload["unexpected"] = "field"
    for name in ("one", "two"):
        _write_current_payload(repo, "decisions", _canonical_json(payload), name=name)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


def test_inventory_does_not_follow_symlinked_current_json_payload(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    outside = tmp_path / "outside-receipt.json"
    outside.write_text(_canonical_json(_receipt()), encoding="utf-8")
    destination = _current_payload_path(repo, "receipts", name="linked")
    destination.parent.mkdir(parents=True)
    destination.symlink_to(outside)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["entries"] == []
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


@pytest.mark.parametrize(
    ("category", "count_key", "state"),
    [
        ("decisions", "decision_count", "decision_pending"),
        ("receipts", "receipt_count", "receipt_only"),
        ("clears", "clear_count", "cleared"),
        ("reservations", "inflight_count", "inflight"),
    ],
)
def test_inventory_counts_reserved_category_manifest_once_as_its_record_type(
    tmp_path: Path,
    category: str,
    count_key: str,
    state: str,
) -> None:
    repo = init_repo(tmp_path / "repo")
    _write_current_payload(
        repo,
        category,
        _canonical_json(_current_payload(category)),
        name="manifest",
    )

    inventory = lane_resolution_inventory(root=repo)

    if category == "decisions":
        assert inventory["ok"] is True
        assert inventory["summary"][count_key] == 1
        assert inventory["summary"]["invalid_current_record_count"] == 0
        assert inventory["entries"][0]["state"] == state
    else:
        assert inventory["ok"] is False
        assert inventory["summary"][count_key] == 0
        assert inventory["summary"]["invalid_current_record_count"] == 1
        assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


def test_current_and_historical_record_roots_are_disjoint(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")

    current = current_record_root(carrier)
    historical = historical_record_roots(carrier)

    assert current == tmp_path / "repo-records/recovery/lane-resolution-v2"
    assert historical == (
        tmp_path / "repo-records/recovery/lane-resolution",
        repo / "build/artifacts/lane-resolution",
        carrier / "build/artifacts/lane-resolution",
    )
    assert current not in historical


def test_canonical_current_record_path_rejects_historical_roots(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    current = current_record_root(repo)

    assert canonical_record_path(repo, current / "decisions/current.json") is True
    assert all(
        canonical_record_path(repo, root / "decisions/historical.json") is False
        for root in historical_record_roots(repo)
    )


def test_plan_rejects_current_record_path_outside_decisions_category(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    unsupported = current_record_root(repo) / "custom-decision.json"

    report = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Decisions must remain visible to strict current inventory.",
        evidence_refs=("evidence:record-edges",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-record-edges", token="block"
        ),
        recovery_plan="Keep the lane unchanged.",
        decision_path=unsupported,
        break_glass=False,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]
    assert not unsupported.exists()


def test_canonical_current_record_path_rejects_parent_traversal_to_history(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    current = current_record_root(repo)
    historical = historical_record_roots(repo)[0] / "decisions/traversal.json"
    traversal = current / ".." / "lane-resolution" / "decisions/traversal.json"

    assert traversal.resolve() == historical.resolve()
    assert canonical_record_path(repo, traversal) is False


def test_canonical_current_record_path_rejects_parent_traversal_to_worktree_history(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    current = current_record_root(repo)
    historical = carrier / "build/artifacts/lane-resolution/decisions/traversal.json"
    traversal = (
        current
        / ".."
        / ".."
        / ".."
        / carrier.name
        / "build/artifacts/lane-resolution/decisions/traversal.json"
    )

    assert traversal.resolve() == historical.resolve()
    assert canonical_record_path(repo, traversal) is False


def test_default_decision_path_uses_current_record_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    assert _default_decision_path(repo, "work/example").parent == (
        current_record_root(repo) / "decisions"
    )


def test_descriptor_json_reader_rejects_oversize_raw_bytes(tmp_path: Path) -> None:
    source = tmp_path / "oversize.json"
    source.write_bytes(b'"' + b"x" * (17 * 1024 * 1024) + b'"')
    descriptor = os.open(source, os.O_RDONLY)
    try:
        with pytest.raises(ValueError, match="lane_resolution_current_record_invalid"):
            record_io.read_descriptor_bytes(descriptor)
    finally:
        os.close(descriptor)


def test_immutable_record_write_rejects_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    category = record_root / "receipts"
    category.mkdir(parents=True)
    destination = category / "record.json"
    held = record_root / "receipts-held"
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    original_open = record_io.os.open
    rebound = False

    def rebind_before_category_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        category_open = (dir_fd is None and Path(path) == category) or (
            dir_fd is not None and path == category.name
        )
        if category_open and not rebound:
            category.rename(held)
            category.symlink_to(outside, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "open", rebind_before_category_open)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.write_json_atomic(destination, {"value": "new"}, record_root=record_root)

    assert not (outside / destination.name).exists()


def test_resolution_record_storage_write_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    symlink_root = tmp_path / "record-root-link"
    symlink_root.symlink_to(target, target_is_directory=True)
    assert resolution_roots.record_destination_safe(symlink_root, symlink_root / "record") is False

    record_root = tmp_path / "records"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path == record_root:
            raise OSError
        return original_resolve(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", fail_resolve)
        assert (
            resolution_roots.record_destination_safe(record_root, record_root / "record") is False
        )

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.write_json_atomic(tmp_path / "outside.json", {}, record_root=record_root)

    destination = record_root / "receipts" / "record.json"
    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "record_destination_safe", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.write_json_atomic(destination, {}, record_root=record_root)

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id="invalid",
            artifact_root=record_root,
        )


def test_record_io_does_not_expose_an_unused_entry_probe() -> None:
    assert not hasattr(record_io, "record_entry_exists")


def test_current_snapshot_accessor_failure_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    category = record_root / "receipts"
    category.mkdir(parents=True)
    (category / "receipt.json").write_text("{}\n", encoding="utf-8")
    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot:
        assert snapshot.root_entry_identity("missing") is None
        assert snapshot.file_identity("receipts", "receipt.json") is None
        assert snapshot.read_file("receipts", "receipt.json") is None
        assert snapshot.digest_file("receipts", "receipt.json") is None
        assert snapshot.open_directory("missing") == ((), "missing")
        assert snapshot.open_directory("receipts") == (("receipt.json",), "valid")

        def fail_directory(*_args: object) -> None:
            raise OSError(_REBOUND_ERROR)

        monkeypatch.setattr(snapshot, "_require_directory", fail_directory)
        assert snapshot.open_directory("receipts") == ((), "invalid")
        assert snapshot.file_identity("receipts", "receipt.json") is None
        assert snapshot.digest_file("receipts", "receipt.json") is None


def test_current_snapshot_open_and_path_failure_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    record_root.mkdir()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            current_snapshot.posix,
            "directory_path_identity",
            lambda _root: (_ for _ in ()).throw(OSError(_REBOUND_ERROR)),
        )
        assert current_snapshot.open_current_record_snapshot(record_root) == (None, "invalid")
    assert current_snapshot.read_current_record_path(
        record_root, record_root / "receipts/not-a-decision.json"
    ) == (None, "invalid")
    assert current_snapshot.read_current_record_path(
        record_root, record_root / "decisions/missing.json"
    ) == (None, "missing")


@pytest.mark.parametrize(
    ("raw", "detail"),
    [
        (b"[]", "payload"),
        (b'{"observation":[]}', "observation_digest"),
        (b'{"observation":{},"observation_digest":"wrong"}', "model"),
    ],
)
def test_ownerless_decision_parser_failure_edges(
    tmp_path: Path,
    raw: bytes,
    detail: str,
) -> None:
    with pytest.raises(current_validation.OwnerlessDecisionAdmissionError) as captured:
        current_validation._typed_ownerless_decision(tmp_path, raw)  # noqa: SLF001, RUF100
    assert captured.value.detail == detail


def test_ownerless_decision_snapshot_path_and_read_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    with pytest.raises(current_validation.OwnerlessDecisionAdmissionError) as outside:
        current_validation.admit_ownerless_decision_snapshot(
            root=tmp_path,
            record_root=record_root,
            decision_path=tmp_path / "outside.json",
            supplied={},
        )
    assert outside.value.detail == "path"
    monkeypatch.setattr(
        current_validation, "read_current_record_path", lambda *_args: (None, "missing")
    )
    with pytest.raises(current_validation.OwnerlessDecisionAdmissionError) as missing:
        current_validation.admit_ownerless_decision_snapshot(
            root=tmp_path,
            record_root=record_root,
            decision_path=record_root / "decisions/missing.json",
            supplied={},
        )
    assert missing.value.detail == "descriptor_missing"
    cause = ValueError("bad model")
    with pytest.raises(current_validation.OwnerlessDecisionAdmissionError) as chained:
        current_validation._decision_error("decision_invalid", "model", cause)  # noqa: SLF001, RUF100
    assert chained.value.__cause__ is cause


def test_current_manifest_rejection_and_receipt_sidecar_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision_id = _DECISION_ID
    paths = tuple(tmp_path / f"copy-{index}" / decision_id / "manifest.json" for index in range(3))
    sources = tuple(
        current_store._CurrentPayload(  # noqa: SLF001, RUF100
            path,
            b"{}",
            payload_sha256={},
            package_names=set(),
            payload_identities={},
            entry_identity=(1, index, 0o40700),
        )
        for index, path in enumerate(paths)
    )
    payload = {
        "decision_id": decision_id,
        "lane_ref": "work/example",
        "head": "a" * 40,
        "observation_digest": "b" * 64,
    }
    reads = iter((payload, digest) for digest in ("c" * 64, "d" * 64, "e" * 64))
    monkeypatch.setattr(current_store, "_read_current_payload", lambda *_args: next(reads))
    monkeypatch.setattr(current_store, "preservation_payloads_match", lambda *_args: True)
    records, conflicts, invalid = current_store._manifests_with_conflicts(  # noqa: SLF001, RUF100
        tmp_path,
        sources,
        {},
    )
    assert records == {}
    assert conflicts == {decision_id}
    assert invalid == [*paths]

    invalid_source = current_store._CurrentPayload(  # noqa: SLF001, RUF100
        tmp_path / "receipts/.invalid.receipt-reservation",
        b"\xff",
    )
    reservations, invalid_paths = current_store._receipt_reservations(  # noqa: SLF001, RUF100
        tmp_path,
        tmp_path / "records",
        (invalid_source,),
    )
    assert reservations == {}
    assert invalid_paths == [invalid_source.path]
