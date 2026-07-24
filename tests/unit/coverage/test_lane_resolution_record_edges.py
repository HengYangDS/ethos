from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import canonical_record_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import historical_record_roots
from ethos.surface.cli.lane.resolution import _default_decision_path
from ethos_core.contracts.coordination import HolderRef
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
        target = record_store.ownerless_closeout_reservation_path(
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


def _reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-record-edges", "a" * 40
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:record-edges",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": record_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _partial_reservation(
    root: Path,
) -> tuple[Path, dict[str, object], Path, dict[str, object]]:
    record_root = root / "records"
    reservation = _reservation()
    path = record_store.reserve_ownerless_closeout_target(
        root=root,
        reservation=reservation,
        artifact_root=record_root,
    )
    record_store.transition_ownerless_closeout_reservation(
        root=root,
        expected=reservation,
        phase="receipt",
        recovery_state="effect_complete_receipt_missing",
        postcondition_digest="f" * 64,
        artifact_root=record_root,
    )
    binding = record_store.ownerless_closeout_recovery_binding(
        root=root,
        expected=reservation,
        artifact_root=record_root,
    )
    return record_root, reservation, path, binding


def _write_completion_receipt(
    root: Path,
    record_root: Path,
    reservation: dict[str, object],
    binding: dict[str, object],
    *,
    valid: bool = True,
) -> Path:
    destination = record_store.receipt_path(
        root,
        str(reservation["decision_id"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        {
            "schema_version": 3,
            "receipt_id": "lane-resolution-receipt:record-edge",
            "completed": True,
            "decision_id": reservation["decision_id"],
            "state": "retired",
            "observation_digest": "0" * 64,
            "reconciliation_required": True,
            "lane_ref": reservation["lane_ref"],
            "head": reservation["head"],
            "preservation_package": "",
            "preservation_manifest_sha256": "",
            "ownerless_closeout_binding": binding,
            "mints_authority": False,
        }
        if valid
        else {}
    )
    destination.write_text(json.dumps(payload), encoding="utf-8")
    return destination


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": True},
        {"decision_sha256": "g" * 64},
        {"lane_ref": ""},
        {"decision_id": "invalid"},
        {"executor_ref": "invalid"},
        {"head": "g" * 40},
        {"target_digest": "f" * 64},
        {"phase": "invalid"},
        {"postcondition_digest": None},
        {"phase": "unknown", "recovery_state": "transition_unknown"},
    ],
)
def test_ownerless_reservation_rejects_invalid_identity_or_state(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    reservation = dict(_reservation(), **updates)

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=reservation,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_rejects_non_exact_shape(tmp_path: Path) -> None:
    reservation = _reservation()
    reservation["unexpected"] = "field"

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=reservation,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_rejects_noncanonical_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ParsedHolder:
        @staticmethod
        def serialize() -> str:
            return "agent:codex:thread:canonical"

    monkeypatch.setattr(HolderRef, "parse", lambda _value: ParsedHolder())

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=_reservation(),
            artifact_root=tmp_path / "records",
        )


@pytest.mark.parametrize(
    ("phase", "recovery_state", "postcondition_digest"),
    [
        ("unknown", "transition_unknown", "invalid"),
        ("receipt", "effect_complete_receipt_missing", ""),
    ],
)
def test_ownerless_transition_rejects_invalid_classification_before_mutation(
    tmp_path: Path,
    phase: str,
    recovery_state: str,
    postcondition_digest: str,
) -> None:
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=_reservation(),
            phase=phase,
            recovery_state=recovery_state,
            postcondition_digest=postcondition_digest,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_reader_rejects_unsafe_path_and_invalid_json(
    tmp_path: Path,
) -> None:
    record_root = tmp_path / "records"
    outside = tmp_path / "outside.json"
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.read_ownerless_closeout_reservation(
            record_root=record_root,
            path=outside,
        )

    destination = record_store.ownerless_closeout_reservation_path(
        tmp_path,
        str(_reservation()["target_digest"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True)
    destination.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.read_ownerless_closeout_reservation(
            record_root=record_root,
            path=destination,
        )


@pytest.mark.parametrize("checks", [(True, False), (True, True, False)])
def test_ownerless_transition_preserves_record_when_replace_path_becomes_unsafe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checks: tuple[bool, ...],
) -> None:
    record_root = tmp_path / "records"
    reservation = _reservation()
    path = record_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    safety = iter(checks)
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            phase="unknown",
            recovery_state="transition_unknown",
            artifact_root=record_root,
        )

    assert json.loads(path.read_text(encoding="utf-8")) == reservation


def test_ownerless_release_rejects_unsafe_or_unreadable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, reservation, _path, _binding = _partial_reservation(tmp_path)
    safety = iter((True, False))
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    monkeypatch.undo()
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )


def test_ownerless_release_rejects_mismatched_receipt_and_unsafe_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, reservation, _path, binding = _partial_reservation(tmp_path)
    destination = _write_completion_receipt(
        tmp_path,
        record_root,
        reservation,
        binding,
        valid=False,
    )
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    destination.unlink()
    _write_completion_receipt(tmp_path, record_root, reservation, binding)
    safety = iter((True, True, False))
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )


@pytest.mark.parametrize("case", ["five-field", "unversioned"])
def test_ownerless_release_requires_canonical_completion_receipt(
    tmp_path: Path,
    case: str,
) -> None:
    record_root, reservation, reservation_path, binding = _partial_reservation(tmp_path)
    destination = record_store.receipt_path(
        tmp_path,
        str(reservation["decision_id"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 3,
        "receipt_id": "lane-resolution-receipt:record-edge",
        "decision_id": reservation["decision_id"],
        "completed": True,
        "state": "retired",
        "observation_digest": "0" * 64,
        "reconciliation_required": True,
        "lane_ref": reservation["lane_ref"],
        "head": reservation["head"],
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "ownerless_closeout_binding": binding,
        "mints_authority": False,
    }
    if case == "five-field":
        payload = {
            field: payload[field]
            for field in (
                "completed",
                "decision_id",
                "lane_ref",
                "head",
                "ownerless_closeout_binding",
            )
        }
    else:
        del payload["schema_version"]
    destination.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    assert reservation_path.is_file()


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


def test_receipt_reservation_reuse_rejects_pre_read_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")

    with monkeypatch.context() as scoped:
        safety = iter((True, True, True, True, False))
        scoped.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )

    def occupy_before_reuse(*_args: object) -> int:
        destination.write_text("occupied", encoding="utf-8")
        raise FileExistsError(reservation)

    with monkeypatch.context() as scoped:
        scoped.setattr(record_store.os, "open", occupy_before_reuse)
        with pytest.raises(FileExistsError):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )
    destination.unlink()

    def fail_both_opens(_path: object, flags: int, *_args: object) -> int:
        if flags & record_store.os.O_EXCL:
            raise FileExistsError(reservation)
        raise OSError

    with monkeypatch.context() as scoped:
        scoped.setattr(record_store.os, "open", fail_both_opens)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
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

    with monkeypatch.context() as scoped:
        safety = iter((True, True, True, True, True, True, False))
        scoped.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )

    original_read = record_store.os.read

    def occupy_destination(descriptor: int, length: int) -> bytes:
        content = original_read(descriptor, length)
        destination.write_text("occupied", encoding="utf-8")
        return content

    monkeypatch.setattr(record_store.os, "read", occupy_destination)
    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
        )
