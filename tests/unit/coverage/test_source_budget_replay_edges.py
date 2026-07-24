from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from typing import cast

import pytest

import ethos.adapters.repo.source_budget.artifacts as artifacts
import ethos.adapters.repo.source_budget.measurement.core as measurement
import ethos.adapters.repo.source_budget.snapshots as snapshots
from ethos.adapters.config import source_budget_taxonomy
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.domain.source_budget.core import source_budget_metrics_from_bytes
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path(__file__).resolve().parents[3]


def _artifact_payload() -> dict[str, object]:
    payload: dict[str, object] = {"schema": "test", "entries": []}
    payload["digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def _empty_tree() -> snapshots.GitTreeSnapshot:
    digest = vars(snapshots)["_tree_digest"]("a" * 40, "b" * 40, ())
    return snapshots.GitTreeSnapshot("a" * 40, "b" * 40, (), digest)


def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.contracts is not None
    assert load.required_gaps == ()
    return load.contracts


def _identity(include: str) -> CarrierIdentity:
    return CarrierIdentity.model_validate(
        {
            "carrier_id": "coverage-python",
            "role": "authored_behavioral_source",
            "scope_id": "test.python",
            "disposition": "measure",
            "include": (include,),
            "owner": "tests",
            "metric_profile": "python-source-v2",
        }
    )


def _inventory(path: str, include: str | None = None):
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": (_identity(include or path),),
        }
    )
    return classify_carriers((path,), manifest)


def test_artifact_contract_and_cleanup_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_data = vars(artifacts)["_artifact_data"]
    artifact_target = vars(artifacts)["_artifact_target"]
    open_parent = vars(artifacts)["_open_parent"]
    parent_is_current = vars(artifacts)["_parent_is_current"]
    write_all = vars(artifacts)["_write_all"]
    temporary = vars(artifacts)["_temporary"]
    require_current_parent = vars(artifacts)["_require_current_parent"]
    root = tmp_path / "root"
    root.mkdir()

    for payload in (cast("dict[str, object]", []), {1: "invalid"}, {"digest": "bad"}):
        with pytest.raises(ValueError):
            artifact_data(payload)
    for invalid_root in ("", "../outside", "/absolute", "bad\\root"):
        with pytest.raises(ValueError, match="artifact root invalid"):
            artifact_target(root, invalid_root, None, "0" * 64)
    with pytest.raises(ValueError, match="remain under configured"):
        artifact_target(root, "artifacts", root / "artifacts", "0" * 64)
    with pytest.raises(FileNotFoundError):
        open_parent(root, ("missing",), create=False)

    parent = open_parent(root, ())
    try:
        with monkeypatch.context() as patch:
            patch.setattr(artifacts.os, "fstat", lambda _fd: (_ for _ in ()).throw(OSError()))
            assert parent_is_current(root, (), parent) is False
        collision = ".artifact.json.collision"
        os.close(os.open(collision, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent))
        with monkeypatch.context() as patch:
            patch.setattr(artifacts.secrets, "token_hex", lambda _size: "collision")
            with pytest.raises(FileExistsError, match="temporary name exhausted"):
                temporary(parent, "artifact.json")
        os.unlink(collision, dir_fd=parent)
    finally:
        os.close(parent)

    with monkeypatch.context() as patch:
        patch.setattr(artifacts.os, "write", lambda *_args: 0)
        with pytest.raises(OSError, match="write failed"):
            write_all(-1, b"data")
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "_parent_is_current", lambda *_args: False)
        with pytest.raises(OSError, match="directory changed"):
            require_current_parent(root, (), -1, "missing", published=False)
    with monkeypatch.context() as patch:
        patch.setattr(
            artifacts,
            "_write_all",
            lambda *_args: (_ for _ in ()).throw(OSError("injected")),
        )
        with pytest.raises(OSError, match="injected"):
            artifacts.write_replay_artifact(root, "artifacts", None, _artifact_payload())
    assert list((root / "artifacts").glob(".*")) == []


def test_snapshot_model_envelope_edges() -> None:
    tree = _empty_tree()
    bytes_digest = vars(snapshots)["_bytes_digest"](())
    blob = snapshots.SnapshotBytes(tree.snapshot_digest, (), bytes_digest)

    invalid_entries = (
        (cast("str", 1), "100644", "blob", "a" * 40),
        ("\ud800", "100644", "blob", "a" * 40),
    )
    for values in invalid_entries:
        with pytest.raises(ValueError, match="invalid Git tree entry"):
            snapshots.GitTreeEntry(*values)
    with pytest.raises(ValueError, match="invalid Git tree snapshot"):
        snapshots.GitTreeSnapshot(cast("str", 1), "b" * 40, (), tree.snapshot_digest)
    for gaps in (cast("tuple[str, ...]", ["gap"]), ("gap", "gap")):
        with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
            snapshots.GitTreeSnapshotLoad(None, gaps)
    with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
        snapshots.GitTreeSnapshotLoad(cast("Any", object()), ())

    for gaps in (
        cast("tuple[str, ...]", ["gap"]),
        ("",),
        ("gap", "gap"),
    ):
        with pytest.raises(ValueError):
            snapshots.SnapshotBytesLoad(None, gaps)
    with pytest.raises(ValueError, match="invalid snapshot bytes load"):
        snapshots.SnapshotBytesLoad(cast("Any", tree), ())
    assert snapshots.SnapshotBytesLoad(blob, ()).snapshot == blob


def test_snapshot_transport_helper_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_git = vars(snapshots)["_run_git"]
    bound_root = vars(snapshots)["_bound_root"]
    identity = vars(snapshots)["_identity"]
    parse_record = vars(snapshots)["_parse_ls_tree_record"]
    parse_tree = vars(snapshots)["_parse_ls_tree"]
    tree_from_root = vars(snapshots)["_tree_snapshot_from_bound_root"]
    worktree_from_root = vars(snapshots)["_worktree_snapshot_from_bound_root"]
    parse_header = vars(snapshots)["_parse_batch_header"]
    batch_contents = vars(snapshots)["_batch_contents"]
    selected_entries = vars(snapshots)["_selected_entries"]
    read_bound = vars(snapshots)["_read_bound_snapshot_blobs"]
    tree = _empty_tree()

    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_GIT_EXECUTABLE", None)
        assert run_git(tmp_path, "status") is None

    class BrokenRoot:
        def resolve(self, *, strict: bool) -> Path:
            del strict
            raise OSError

    assert bound_root(cast("Path", BrokenRoot())) is None
    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_run_git", lambda *_args, **_kwargs: None)
        assert bound_root(tmp_path) is None
    invalid_utf8 = subprocess.CompletedProcess([], 0, stdout=b"\xff\n", stderr=b"")
    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_run_git", lambda *_args, **_kwargs: invalid_utf8)
        assert bound_root(tmp_path) is None
        assert identity(tmp_path, "HEAD") is None
    no_newline = subprocess.CompletedProcess([], 0, stdout=b"a" * 40, stderr=b"")
    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_run_git", lambda *_args, **_kwargs: no_newline)
        assert identity(tmp_path, "HEAD") is None

    assert parse_record(b"\xff blob " + b"a" * 40 + b"\ta", b"")[0] is None
    assert parse_tree(b"") == ((), ())
    with monkeypatch.context() as patch:
        values = iter(("a" * 40, None))
        patch.setattr(snapshots, "_identity", lambda *_args: next(values))
        assert tree_from_root(tmp_path, "HEAD").required_gaps == ("git_snapshot_tree_unresolved",)
    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_identity", lambda *_args: None)
        assert worktree_from_root(tmp_path).required_gaps == ("git_snapshot_commit_unresolved",)
    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_identity", lambda *_args: "a" * 40)
        patch.setattr(snapshots, "_run_git", lambda *_args, **_kwargs: None)
        assert worktree_from_root(tmp_path).required_gaps == (
            "git_snapshot_worktree_status_failed",
        )

    assert snapshots.tree_snapshot(cast("Path", "bad"), "").required_gaps == (
        "git_snapshot_request_invalid",
    )
    assert snapshots.tree_snapshot(tmp_path / "missing", "HEAD").required_gaps == (
        "git_snapshot_root_invalid",
    )
    assert snapshots.worktree_snapshot(cast("Path", "bad")).required_gaps == (
        "git_snapshot_request_invalid",
    )
    assert snapshots.worktree_snapshot(tmp_path / "missing").required_gaps == (
        "git_snapshot_root_invalid",
    )
    assert parse_header(b"\xff", "a" * 40)[1] == "git_snapshot_blob_batch_invalid"
    assert batch_contents(b"missing-newline", ("a" * 40,))[1] == ("git_snapshot_blob_batch_invalid")
    assert selected_entries(tree, cast("tuple[str, ...]", []))[1] == (
        "git_snapshot_request_invalid",
    )
    assert selected_entries(tree, ("missing",))[1] == ("git_snapshot_path_selection_invalid",)
    assert read_bound(tmp_path, tree, ()).snapshot is not None
    assert snapshots.read_snapshot_blobs(cast("Path", "bad"), tree, ()).required_gaps == (
        "git_snapshot_request_invalid",
    )
    assert snapshots.read_snapshot_blobs(tmp_path / "missing", tree, ()).required_gaps == (
        "git_snapshot_root_invalid",
    )


def test_measurement_public_and_provider_edge_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry()
    inventory = _inventory("sample.py")
    match = inventory.matches[0]
    resolve_provider = vars(measurement)["_resolve_carrier_provider"]
    measure_bytes_admitted = vars(measurement)["_measure_carrier_bytes_admitted"]
    measure_contents = vars(measurement)["_measure_snapshot_contents"]

    assert (
        measurement.measure_carrier_bytes(cast("bytes", "bad"), match, registry).measurement is None
    )
    with monkeypatch.context() as patch:
        patch.setattr(measurement, "_admit_carrier_inputs", lambda *_args: None)
        assert measurement.measure_carrier_bytes(b"", match, registry).measurement is None
    with monkeypatch.context() as patch:
        patch.setattr(
            measurement,
            "_resolve_carrier_provider",
            lambda *_args: (None, "source_budget_measurement_contract_invalid:sample.py"),
        )
        assert measurement.measure_carrier_bytes(b"", match, registry).measurement is None
    for subject, expected in (
        (match, "source_budget_measurement_resource_exhausted:sample.py"),
        (object(), "source_budget_measurement_resource_exhausted"),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(
                measurement,
                "_admit_carrier_inputs",
                lambda *_args: (_ for _ in ()).throw(MemoryError()),
            )
            load = measurement.measure_carrier_bytes(b"", cast("Any", subject), registry)
        assert load.required_gaps == (expected,)

    provider, gap = resolve_provider(match, registry)
    assert provider is not None and gap is None
    exceeded = measure_bytes_admitted(
        b"x" * (provider.execution_descriptor.max_carrier_bytes + 1),
        match,
        provider,
        registry,
    )
    assert exceeded.required_gaps == ("source_budget_measurement_carrier_bytes_exceeded:sample.py",)
    assert measure_contents((("sample.py", b"x"),), inventory, registry, ())[1] == (
        "source_budget_measurement_contract_invalid",
    )
    assert measure_contents((("sample.py", b"x"),), inventory, registry, (cast("Any", object()),))[
        1
    ] == ("source_budget_measurement_contract_invalid",)

    with monkeypatch.context() as patch:
        patch.setattr(
            measurement,
            "_admit_snapshot_inputs",
            lambda *_args: (_ for _ in ()).throw(MemoryError()),
        )
        assert measurement.measure_snapshot_bytes((), inventory, registry).required_gaps == (
            "source_budget_measurement_resource_exhausted",
        )
    with monkeypatch.context() as patch:
        patch.setattr(measurement, "_admit_snapshot_inputs", lambda *_args: None)
        assert measurement.measure_snapshot_bytes((), inventory, registry).required_gaps == (
            "source_budget_measurement_contract_invalid",
        )
    assert measurement.measure_snapshot_bytes(
        cast("tuple[tuple[str, bytes], ...]", []), inventory, registry
    ).required_gaps == ("source_budget_measurement_contract_invalid",)
    unsupported = _inventory("sample.py", include="other.py")
    assert measurement.measure_snapshot_bytes((), unsupported, registry).required_gaps == (
        "source_budget_carrier_unsupported:sample.py:.py",
    )
    with monkeypatch.context() as patch:
        patch.setattr(measurement, "_resolve_carrier_provider", lambda *_args: (None, None))
        assert measurement.measure_snapshot(tmp_path, inventory, registry).required_gaps == (
            "source_budget_measurement_contract_invalid",
        )


def test_v1_replay_rejects_invalid_container_taxonomy_and_item_shapes() -> None:
    taxonomy = source_budget_taxonomy(ROOT)
    with pytest.raises(ValueError, match="inputs invalid"):
        source_budget_metrics_from_bytes(cast("Any", []), taxonomy)
    with pytest.raises(ValueError, match="inputs invalid"):
        source_budget_metrics_from_bytes((), cast("Any", object()))
    with pytest.raises(ValueError, match="inputs invalid"):
        source_budget_metrics_from_bytes((cast("Any", (1, b"x")),), taxonomy)


def test_measurement_low_level_limit_and_resolution_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry()
    match = _inventory("sample.py").matches[0]
    limit_error = vars(measurement)["_CarrierBytesExceededError"]
    require_limit = vars(measurement)["_require_carrier_byte_limit"]
    resolve_provider = vars(measurement)["_resolve_carrier_provider"]
    read_carrier = vars(measurement)["_read_carrier"]
    read_exact = vars(measurement)["_read_exact"]

    with pytest.raises(limit_error):
        require_limit(2, 1)
    with monkeypatch.context() as patch:
        patch.setattr(
            measurement,
            "resolve_metric_contracts",
            lambda *_args: (_ for _ in ()).throw(ValueError()),
        )
        assert resolve_provider(match, registry)[1] == (
            "source_budget_measurement_contract_invalid:sample.py"
        )
    with monkeypatch.context() as patch:
        patch.setattr(
            measurement,
            "_read_stable_bytes",
            lambda *_args: (_ for _ in ()).throw(limit_error()),
        )
        assert read_carrier(tmp_path, "sample.py", 1)[1] == (
            "source_budget_measurement_carrier_bytes_exceeded:sample.py"
        )
    with monkeypatch.context() as patch:
        patch.setattr(measurement.os, "read", lambda *_args: b"xx")
        with pytest.raises(limit_error):
            read_exact(-1, 1, 1)
