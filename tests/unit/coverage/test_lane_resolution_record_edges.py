from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
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


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_clear_quarantine_identity_accepts_only_canonical_name() -> None:
    identity = (0xABC, 0xDEF, 0o40755)
    canonical = record_store.clear_quarantine_name(_DECISION_ID, identity)
    _empty, digest, encoded, suffix = canonical.split(".")

    assert suffix == "clear-quarantine"
    assert record_store.clear_quarantine_identity(canonical, _DECISION_ID) == identity
    for malformed in (
        f".{digest}.0{encoded}.clear-quarantine",
        f".{digest}.{encoded.upper()}.clear-quarantine",
        f".{digest}.clear-quarantine",
        f".{digest}.{encoded}-1.clear-quarantine",
    ):
        assert record_store.clear_quarantine_identity(malformed, _DECISION_ID) is None


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


def _receipt_reservation_paths(root: Path) -> tuple[Path, Path, Path]:
    record_root = root / "records"
    destination = record_store.receipt_path(
        root,
        _DECISION_ID,
        artifact_root=record_root,
    )
    reservation = destination.with_name(f".{destination.stem}.receipt-reservation")
    reservation.parent.mkdir(parents=True)
    return record_root, destination, reservation


def _mutate_current_record(
    operation: str,
    destination: Path,
    expected: dict[str, object],
    *,
    record_root: Path,
) -> None:
    if operation == "replace":
        record_store.replace_json_atomic(
            destination,
            {"value": "new"},
            expected=expected,
            record_root=record_root,
        )
        return
    record_store.remove_record(
        destination,
        expected=expected,
        record_root=record_root,
    )


def test_receipt_reservation_reuse_rejects_pre_read_drift(
    tmp_path: Path,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")
    destination.write_text("occupied", encoding="utf-8")

    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
        )


def test_receipt_reservation_reuse_rejects_post_read_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")

    original_read = record_io.os.read

    def occupy_destination(descriptor: int, length: int) -> bytes:
        content = original_read(descriptor, length)
        destination.write_text("occupied", encoding="utf-8")
        return content

    monkeypatch.setattr(record_io.os, "read", occupy_destination)
    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
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


@pytest.mark.parametrize("operation", ["replace", "remove"])
def test_mutable_record_operation_rejects_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    record_root = tmp_path / "records"
    category = record_root / "reservations"
    category.mkdir(parents=True)
    destination = category / "record.json"
    expected = {"value": "old"}
    destination.write_bytes(record_store.canonical_current_record_bytes(expected))
    held = record_root / "reservations-held"
    outside = tmp_path / "outside-reservations"
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
        _mutate_current_record(operation, destination, expected, record_root=record_root)

    assert (held / destination.name).read_bytes() == record_store.canonical_current_record_bytes(
        expected
    )
    assert not (outside / destination.name).exists()


@pytest.mark.parametrize("operation", ["replace", "remove"])
def test_mutable_record_operation_preserves_a_post_compare_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    competitor = {"value": "competitor"}
    destination.write_bytes(record_store.canonical_current_record_bytes(expected))
    rename_no_replace = record_io.rename_record_no_replace
    raced = False

    def install_competitor_then_rename(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
    ) -> None:
        nonlocal raced
        if not raced:
            replacement = destination.with_name("replacement.json")
            replacement.write_bytes(record_store.canonical_current_record_bytes(competitor))
            replacement.replace(destination)
            raced = True
        assert rename_no_replace is not None
        rename_no_replace(directory_descriptor, source_name, target_name)

    monkeypatch.setattr(
        record_io,
        "rename_record_no_replace",
        install_competitor_then_rename,
        raising=False,
    )

    with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
        _mutate_current_record(operation, destination, expected, record_root=record_root)

    assert destination.read_bytes() == record_store.canonical_current_record_bytes(competitor)


def test_receipt_reservation_create_does_not_follow_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    held = record_root / "receipts-held"
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    original_open = record_io.os.open
    rebound = False

    def rebind_before_absolute_create(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        if dir_fd is None and Path(path) == reservation and not rebound:
            destination.parent.rename(held)
            destination.parent.symlink_to(outside, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "open", rebind_before_absolute_create)

    created = record_store.reserve_resolution_receipt(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )

    assert created == reservation
    assert reservation.read_text(encoding="utf-8") == f"{_DECISION_ID}\n"
    assert not (outside / reservation.name).exists()


def test_receipt_reservation_release_does_not_unlink_through_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")
    held = record_root / "receipts-held"
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    outside_reservation = outside / reservation.name
    outside_reservation.write_text("outside\n", encoding="utf-8")
    original_unlink = Path.unlink
    rebound = False

    def rebind_before_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal rebound
        if path == reservation and not rebound:
            destination.parent.rename(held)
            destination.parent.symlink_to(outside, target_is_directory=True)
            rebound = True
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", rebind_before_unlink)

    record_store.release_resolution_receipt_reservation(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )

    assert outside_reservation.read_text(encoding="utf-8") == "outside\n"
