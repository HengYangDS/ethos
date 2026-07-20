from __future__ import annotations

import errno
import importlib
import os
import stat
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ethos.adapters.repo.source_budget.carriers import load_carrier_manifest
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.measurements import CarrierMeasurementLoad
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

ROOT = Path(__file__).resolve().parents[5]
MODULE = "ethos.adapters.repo.source_budget.measurement.core"


class _LowLevelFaults:
    def __init__(self, stage: str, root: Path) -> None:
        self.stage = stage
        self.root = root
        self.fstats = 0
        self.reads = 0
        self.real_fstat = os.fstat
        self.real_lstat = os.lstat
        self.real_read = os.read
        self.real_close = os.close

    def fstat(self, fd: int) -> Any:
        self.fstats += 1
        observed = self.real_fstat(fd)
        if self.stage == "root_not_directory" and self.fstats == 1:
            return SimpleNamespace(st_mode=stat.S_IFREG)
        if self.stage == "child_not_directory" and self.fstats == 2:
            return SimpleNamespace(st_mode=stat.S_IFREG)
        return observed

    def lstat(self, name: str, *, dir_fd: int) -> Any:
        if self.stage == "lstat":
            message = f"SENSITIVE:{self.root}"
            raise OSError(message)
        return self.real_lstat(name, dir_fd=dir_fd)

    def read(self, fd: int, size: int) -> bytes:
        self.reads += 1
        if self.stage == "short":
            return b""
        if self.stage == "long" and self.reads == 1:
            return b"x" * size
        return self.real_read(fd, size)

    def close(self, fd: int) -> None:
        self.real_close(fd)
        if self.stage == "close":
            message = f"SENSITIVE:{self.root}"
            raise OSError(message)


@lru_cache(maxsize=1)
def _registry():
    load = load_metric_contracts(ROOT)
    assert load.contracts is not None
    assert not load.required_gaps
    return load.contracts


def _identity(
    carrier_id: str,
    include: str,
    *,
    scope_id: str = "test.python",
    disposition: str = "measure",
    role: str = "authored_behavioral_source",
) -> CarrierIdentity:
    payload: dict[str, Any] = {
        "carrier_id": carrier_id,
        "role": role,
        "scope_id": scope_id,
        "disposition": disposition,
        "include": (include,),
        "owner": "tests",
    }
    if disposition == "measure":
        payload["metric_profile"] = "python-source-v2"
    else:
        payload["exclusion_reason"] = "reviewed exclusion"
    return CarrierIdentity.model_validate(payload)


def _inventory(paths: tuple[str, ...], *identities: CarrierIdentity):
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": identities,
        }
    )
    return classify_carriers(paths, manifest)


def _module():
    return importlib.import_module(MODULE)


def test_jinja_measurement_carrier_is_owned_outside_adoption_rendering() -> None:
    load = load_carrier_manifest(ROOT)
    assert load.required_gaps == ()
    assert load.manifest is not None

    inventory = classify_carriers(("packages/example.j2",), load.manifest)

    assert inventory.required_gaps == ()
    assert len(inventory.matches) == 1
    match = inventory.matches[0]
    assert match.state == "classified"
    assert match.identity is not None
    assert match.identity.carrier_id == "jinja-templates"
    assert match.identity.role == "template_source"
    assert match.identity.metric_profile == "template-jinja-v2"
    assert match.identity.owner == "ethos-product"


def test_measurement_orchestrator_measures_one_regular_inventory(
    tmp_path: Path,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    inventory = _inventory((relative,), _identity("test-python", relative))
    carrier = _module().measure_carrier(tmp_path, inventory.matches[0], _registry())
    assert carrier.required_gaps == ()
    assert carrier.measurement is not None
    snapshot = _module().measure_snapshot(tmp_path, inventory, _registry())
    assert snapshot.required_gaps == ()
    assert snapshot.snapshot is not None
    assert snapshot.snapshot.measurements == (carrier.measurement,)
    assert _module().__all__ == ("measure_carrier", "measure_snapshot")


def test_orchestrator_rejects_impossible_empty_read_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()
    monkeypatch.setattr(module, "_read_carrier", lambda *_: (None, None))
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]

    load = module.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_contract_invalid:{relative}",)


def test_carrier_admission_maps_memory_exhaustion_to_stable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    module = _module()

    def exhausted(*_args: object) -> None:
        message = f"SENSITIVE-ADMISSION:{tmp_path}"
        raise MemoryError(message)

    monkeypatch.setattr(module, "_canonical_contracts", exhausted)
    load = module.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_measurement_resource_exhausted",)


@pytest.mark.parametrize("stage", ["resolve", "load"])
def test_carrier_post_read_maps_memory_exhaustion_to_path_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    module = _module()

    def exhausted(*_args: object) -> None:
        message = f"SENSITIVE-{stage.upper()}:{tmp_path}"
        raise MemoryError(message)

    target = "resolve_metric_contracts" if stage == "resolve" else "_load_native_measurement"
    monkeypatch.setattr(module, target, exhausted)
    load = module.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_resource_exhausted:{relative}",)


def test_snapshot_admission_maps_memory_exhaustion_to_stable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    inventory = _inventory((relative,), _identity("test-python", relative))
    module = _module()

    def exhausted(*_args: object) -> None:
        message = f"SENSITIVE-SNAPSHOT-ADMISSION:{tmp_path}"
        raise MemoryError(message)

    monkeypatch.setattr(module, "_canonical_contracts", exhausted)
    load = module.measure_snapshot(tmp_path, inventory, _registry())

    assert load.snapshot is None
    assert load.required_gaps == ("source_budget_measurement_resource_exhausted",)


@pytest.mark.parametrize("stage", ["carrier", "replay"])
def test_snapshot_carrier_loop_maps_memory_exhaustion_to_path_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    relative = "sample.py"
    inventory = _inventory((relative,), _identity("test-python", relative))
    module = _module()

    def exhausted(*_args: object) -> None:
        message = f"SENSITIVE-{stage.upper()}:{tmp_path}"
        raise MemoryError(message)

    target = "measure_carrier" if stage == "carrier" else "_replay_carrier_load"
    monkeypatch.setattr(module, target, exhausted)
    load = module.measure_snapshot(tmp_path, inventory, _registry())

    assert load.snapshot is None
    assert load.required_gaps == (f"source_budget_measurement_resource_exhausted:{relative}",)


def test_snapshot_construction_maps_memory_exhaustion_to_stable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    inventory = _inventory((relative,), _identity("test-python", relative))
    module = _module()

    def exhausted(*_args: object, **_kwargs: object) -> None:
        message = f"SENSITIVE-SNAPSHOT-CONSTRUCTION:{tmp_path}"
        raise MemoryError(message)

    monkeypatch.setattr(module.MeasurementSnapshot, "from_inventory", exhausted)
    load = module.measure_snapshot(tmp_path, inventory, _registry())

    assert load.snapshot is None
    assert load.required_gaps == ("source_budget_measurement_resource_exhausted",)


def test_replay_rejects_forged_carrier_load_type() -> None:
    relative = "sample.py"
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    contracts = resolve_metric_contracts(match.identity, _registry())
    forged: Any = object()
    replay_carrier_load = vars(_module())["_replay_carrier_load"]

    assert replay_carrier_load(forged, match, contracts) is None


def test_descriptor_reader_opens_one_component_at_a_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "nested/sample.py"
    (tmp_path / "nested").mkdir()
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()
    real_open = os.open
    real_close = os.close
    calls: list[tuple[object, int, int | None]] = []
    opened: list[int] = []
    closed: list[int] = []

    def recorded(path: object, flags: int, *args: object, dir_fd: int | None = None) -> int:
        calls.append((path, flags, dir_fd))
        fd = real_open(path, flags, *args, dir_fd=dir_fd)
        opened.append(fd)
        return fd

    def closing(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    monkeypatch.setattr(module.os, "open", recorded)
    monkeypatch.setattr(module.os, "close", closing)
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.measurement is not None
    assert [item[0] for item in calls[1:]] == ["nested", "sample.py"]
    assert calls[0][1] & os.O_DIRECTORY
    assert calls[0][1] & os.O_NOFOLLOW
    assert calls[1][1] & os.O_DIRECTORY
    assert calls[1][1] & os.O_NOFOLLOW
    assert calls[2][1] & os.O_NONBLOCK
    assert calls[2][1] & os.O_NOFOLLOW
    assert closed == list(reversed(opened))


@pytest.mark.timeout(2)
@pytest.mark.parametrize("kind", ["ancestor_symlink", "final_symlink", "fifo", "directory"])
def test_descriptor_reader_rejects_symlinks_and_non_regular_objects(
    tmp_path: Path,
    kind: str,
) -> None:
    relative = "sample.py"
    if kind == "ancestor_symlink":
        relative = "alias/sample.py"
        (tmp_path / "real").mkdir()
        (tmp_path / "real/sample.py").write_text("value = 1\n", encoding="utf-8")
        (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    elif kind == "final_symlink":
        (tmp_path / "real.py").write_text("value = 1\n", encoding="utf-8")
        (tmp_path / relative).symlink_to(tmp_path / "real.py")
    elif kind == "fifo":
        os.mkfifo(tmp_path / relative)
    else:
        (tmp_path / relative).mkdir()
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    load = _module().measure_carrier(tmp_path, match, _registry())
    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_object_unsupported:{relative}",)
    assert str(tmp_path) not in load.required_gaps[0]


@pytest.mark.parametrize("mutation", ["read", "final", "ancestor", "same_size"])
def test_descriptor_reader_rejects_failures_and_post_open_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    relative = "nested/sample.py" if mutation == "ancestor" else "sample.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("value = 1\n", encoding="utf-8")
    module = _module()
    real_read = os.read
    changed = False

    def altered(fd: int, length: int) -> bytes:
        nonlocal changed
        if mutation == "read":
            message = f"SENSITIVE:{tmp_path}"
            raise OSError(message)
        if not changed:
            changed = True
            if mutation == "final":
                path.rename(path.with_suffix(".old"))
                path.write_text("other = 2\n", encoding="utf-8")
            elif mutation == "ancestor":
                path.parent.rename(tmp_path / "old")
                path.parent.mkdir()
                path.write_text("other = 2\n", encoding="utf-8")
            else:
                path.write_text("other = 2\n", encoding="utf-8")
        return real_read(fd, length)

    monkeypatch.setattr(module.os, "read", altered)
    match = _inventory((relative,), _identity("test-python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    reason = "unreadable" if mutation == "read" else "changed"
    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_object_{reason}:{relative}",)
    assert "SENSITIVE" not in load.required_gaps[0]
    assert str(tmp_path) not in load.required_gaps[0]


def test_snapshot_orders_sums_and_binds_reviewed_exclusions(tmp_path: Path) -> None:
    for relative in ("a.py", "b.py"):
        (tmp_path / relative).write_text(f"{relative[0]} = 1\n", encoding="utf-8")
    (tmp_path / "skip.bin").write_bytes(b"\xff")
    identities = (
        _identity("python-a", "a.py"),
        _identity("python-b", "b.py"),
        _identity(
            "reviewed",
            "skip.bin",
            disposition="exclude",
            role="vendor_or_lock",
        ),
    )
    forward = _inventory(("a.py", "b.py", "skip.bin"), *identities)
    reverse = _inventory(("skip.bin", "b.py", "a.py"), *identities)
    first = _module().measure_snapshot(tmp_path, forward, _registry())
    second = _module().measure_snapshot(tmp_path, reverse, _registry())
    assert first.snapshot is not None
    assert second.snapshot == first.snapshot
    assert tuple(item.relative_path for item in first.snapshot.measurements) == (
        "a.py",
        "b.py",
    )
    assert len(first.snapshot.coordinates) == 2
    excluded = next(item for item in forward.matches if item.state == "excluded")
    direct = _module().measure_carrier(tmp_path, excluded, _registry())
    assert direct.required_gaps == ("source_budget_measurement_carrier_excluded:skip.bin",)


def test_snapshot_reports_all_path_bound_failures_without_partial_result(
    tmp_path: Path,
) -> None:
    (tmp_path / "good.py").write_text("value = 1\n", encoding="utf-8")
    for relative in ("bad-a.py", "bad-b.py"):
        (tmp_path / relative).write_bytes(b"\xff")
    identity = _identity("python", "*.py")
    inventory = _inventory(("bad-b.py", "good.py", "bad-a.py"), identity)
    load = _module().measure_snapshot(tmp_path, inventory, _registry())
    assert load.snapshot is None
    assert load.required_gaps == tuple(
        f"source_budget_native_text_invalid_utf8:{relative}"
        for relative in ("bad-a.py", "bad-b.py")
    )


def test_snapshot_separates_raw_vector_and_scope_identity(tmp_path: Path) -> None:
    relative = "sample.py"
    path = tmp_path / relative
    first_inventory = _inventory((relative,), _identity("python", relative))
    path.write_bytes(b"value = 1\n")
    first = _module().measure_snapshot(tmp_path, first_inventory, _registry()).snapshot
    path.write_bytes(b"value = 1\r\n")
    second = _module().measure_snapshot(tmp_path, first_inventory, _registry()).snapshot
    assert first is not None
    assert second is not None
    assert first.coordinates == second.coordinates
    assert first.vector_digest == second.vector_digest
    assert first.snapshot_digest != second.snapshot_digest
    moved_inventory = _inventory(
        (relative,),
        _identity("python", relative, scope_id="test.moved"),
    )
    moved = _module().measure_snapshot(tmp_path, moved_inventory, _registry()).snapshot
    assert moved is not None
    assert moved.snapshot_digest != second.snapshot_digest
    assert {item.scope_id for item in moved.coordinates} == {"test.moved"}


def test_orchestrator_rejects_noncanonical_inputs_and_inventory_gaps(
    tmp_path: Path,
) -> None:
    identity = _identity("python", "sample.py")
    inventory = _inventory(("sample.py",), identity)
    match = inventory.matches[0]
    registry = _registry()
    module = _module()
    assert module.measure_carrier("bad", match, registry).measurement is None
    assert module.measure_carrier(tmp_path, object(), registry).measurement is None
    assert module.measure_carrier(tmp_path, match, object()).measurement is None
    assert module.measure_snapshot("bad", inventory, registry).snapshot is None
    assert module.measure_snapshot(tmp_path, object(), registry).snapshot is None
    assert module.measure_snapshot(tmp_path, inventory, object()).snapshot is None
    bad_match = match.model_copy(update={"relative_path": "../bad"})
    bad_inventory = inventory.model_copy(update={"inventory_digest": "0" * 64})
    bad_registry = registry.model_copy(update={"contract_version": 0})
    assert module.measure_carrier(tmp_path, bad_match, registry).measurement is None
    assert module.measure_snapshot(tmp_path, bad_inventory, registry).snapshot is None
    assert module.measure_carrier(tmp_path, match, bad_registry).measurement is None
    unclassified = _inventory(("other.txt",), identity)
    assert module.measure_carrier(tmp_path, unclassified.matches[0], registry).required_gaps
    assert (
        module.measure_snapshot(tmp_path, unclassified, registry).required_gaps
        == unclassified.required_gaps
    )


@pytest.mark.parametrize(
    "field",
    ["st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"],
)
def test_descriptor_reader_rejects_each_fingerprint_coordinate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()
    real_fstat = os.fstat
    regular_calls = 0

    def changed(fd: int):
        nonlocal regular_calls
        observed = real_fstat(fd)
        if stat.S_ISREG(observed.st_mode):
            regular_calls += 1
            if regular_calls == 2:
                values = {
                    name: getattr(observed, name)
                    for name in (
                        "st_dev",
                        "st_ino",
                        "st_mode",
                        "st_size",
                        "st_mtime_ns",
                        "st_ctime_ns",
                    )
                }
                values[field] += 1
                return SimpleNamespace(**values)
        return observed

    monkeypatch.setattr(module.os, "fstat", changed)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.required_gaps == (f"source_budget_measurement_object_changed:{relative}",)


@pytest.mark.parametrize(
    "stage",
    [
        "root_not_directory",
        "child_not_directory",
        "missing",
        "lstat",
        "short",
        "long",
        "close",
    ],
)
def test_descriptor_reader_maps_low_level_failures_without_leaking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    relative = "nested/sample.py" if stage == "child_not_directory" else "sample.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if stage != "missing":
        path.write_text("value = 1\n", encoding="utf-8")
    module = _module()
    faults = _LowLevelFaults(stage, tmp_path)
    monkeypatch.setattr(module.os, "fstat", faults.fstat)
    monkeypatch.setattr(module.os, "lstat", faults.lstat)
    monkeypatch.setattr(module.os, "read", faults.read)
    monkeypatch.setattr(module.os, "close", faults.close)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.measurement is None
    assert len(load.required_gaps) == 1
    assert "SENSITIVE" not in load.required_gaps[0]
    assert str(tmp_path) not in load.required_gaps[0]


def test_descriptor_reader_closes_every_descriptor_on_memory_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()
    real_open = os.open
    real_close = os.close
    opened: list[int] = []
    closed: list[int] = []

    def recorded(path: object, flags: int, *args: object, dir_fd: int | None = None) -> int:
        fd = real_open(path, flags, *args, dir_fd=dir_fd)
        opened.append(fd)
        return fd

    def exhausted(_fd: int, _size: int) -> bytes:
        message = "SENSITIVE"
        raise MemoryError(message)

    def closing(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    monkeypatch.setattr(module.os, "open", recorded)
    monkeypatch.setattr(module.os, "read", exhausted)
    monkeypatch.setattr(module.os, "close", closing)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_resource_exhausted:{relative}",)
    assert closed == list(reversed(opened))


@pytest.mark.parametrize("registration_index", [0, 1, 2])
def test_descriptor_reader_closes_descriptor_when_registration_exhausts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    registration_index: int,
) -> None:
    relative = "nested/sample.py"
    (tmp_path / "nested").mkdir()
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()
    real_open = os.open
    real_close = os.close
    real_register = vars(module)["_register_descriptor"]
    opened: list[int] = []
    closed: list[int] = []
    registrations = 0

    class ExhaustedRegistry:
        def append(self, _descriptor: int) -> None:
            message = f"SENSITIVE-REGISTER:{tmp_path}"
            raise MemoryError(message)

    exhausted_registry: Any = ExhaustedRegistry()

    def recorded(path: object, flags: int, *args: object, dir_fd: int | None = None) -> int:
        fd = real_open(path, flags, *args, dir_fd=dir_fd)
        opened.append(fd)
        return fd

    def closing(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    def register(descriptors: list[int], descriptor: int) -> None:
        nonlocal registrations
        current = registrations
        registrations += 1
        if current == registration_index:
            real_register(exhausted_registry, descriptor)
        real_register(descriptors, descriptor)

    monkeypatch.setattr(module.os, "open", recorded)
    monkeypatch.setattr(module.os, "close", closing)
    monkeypatch.setattr(module, "_register_descriptor", register)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_resource_exhausted:{relative}",)
    assert registrations == registration_index + 1
    assert closed == list(reversed(opened))


@pytest.mark.parametrize("error_code", [errno.EMFILE, errno.ENFILE, errno.ENOMEM])
def test_descriptor_reader_maps_local_resource_errno_to_stable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_code: int,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()

    def exhausted(*_args: object, **_kwargs: object) -> int:
        raise OSError(error_code, f"SENSITIVE:{tmp_path}")

    monkeypatch.setattr(module.os, "open", exhausted)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_resource_exhausted:{relative}",)


def test_descriptor_reader_maps_runtime_api_failure_to_unreadable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    module = _module()

    def invalid_stat(_fd: int) -> os.stat_result:
        message = "SENSITIVE"
        raise TypeError(message)

    monkeypatch.setattr(module.os, "fstat", invalid_stat)
    match = _inventory((relative,), _identity("python", relative)).matches[0]
    load = module.measure_carrier(tmp_path, match, _registry())
    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_object_unreadable:{relative}",)


def test_orchestrator_rejects_forged_provider_and_snapshot_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    inventory = _inventory((relative,), _identity("python", relative))
    match = inventory.matches[0]
    contracts = resolve_metric_contracts(match.identity, _registry())
    native = (
        importlib.import_module("ethos.adapters.repo.source_budget.measurement.native.core")
        .measure_native(b"value = 1\n", contracts)
        .measurement
    )
    assert native is not None
    forged = native.model_copy(update={"values": (native.values[0], native.values[0])})
    load = object.__new__(NativeMeasurementLoad)
    object.__setattr__(load, "measurement", forged)
    object.__setattr__(load, "required_gaps", ())
    module = _module()
    monkeypatch.setattr(module, "measure_native", lambda *_: object())
    assert module.measure_carrier(tmp_path, match, _registry()).measurement is None
    monkeypatch.setattr(module, "measure_native", lambda *_: load)
    assert module.measure_carrier(tmp_path, match, _registry()).measurement is None

    valid_native = NativeMeasurementLoad(native, ())
    object.__setattr__(
        valid_native,
        "required_gaps",
        ("source_budget_native_parse_failed:python",),
    )
    monkeypatch.setattr(module, "measure_native", lambda *_: valid_native)
    invalid_carrier = module.measure_carrier(tmp_path, match, _registry())
    assert invalid_carrier.measurement is None
    assert invalid_carrier.required_gaps == (
        f"source_budget_measurement_contract_invalid:{relative}",
    )

    monkeypatch.undo()
    valid_carrier = module.measure_carrier(tmp_path, match, _registry())
    assert valid_carrier.measurement is not None
    forged_carrier = CarrierMeasurementLoad(
        valid_carrier.measurement,
        (),
        match=match,
        contracts=_registry(),
    )
    object.__setattr__(
        forged_carrier,
        "required_gaps",
        ("source_budget_native_parse_failed:python",),
    )
    monkeypatch.setattr(module, "measure_carrier", lambda *_: forged_carrier)
    invalid_snapshot = module.measure_snapshot(tmp_path, inventory, _registry())
    assert invalid_snapshot.snapshot is None
    assert invalid_snapshot.required_gaps == (
        f"source_budget_measurement_contract_invalid:{relative}",
    )

    monkeypatch.undo()
    monkeypatch.setattr(module.MeasurementSnapshot, "from_inventory", lambda *_, **__: object())
    assert module.measure_snapshot(tmp_path, inventory, _registry()).snapshot is None


def test_orchestrator_rejects_provider_output_for_different_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_text("value = 1\n", encoding="utf-8")
    inventory = _inventory((relative,), _identity("python", relative))
    match = inventory.matches[0]
    contracts = resolve_metric_contracts(match.identity, _registry())
    other = importlib.import_module(
        "ethos.adapters.repo.source_budget.measurement.native.core"
    ).measure_native(b"value = 2\n", contracts)
    assert other.measurement is not None
    module = _module()
    monkeypatch.setattr(
        module,
        "measure_native",
        lambda *_: NativeMeasurementLoad(other.measurement, ()),
    )

    load = module.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_contract_invalid:{relative}",)


def test_all_reviewed_exclusions_keep_complete_snapshot_identity(
    tmp_path: Path,
) -> None:
    (tmp_path / "skip.bin").write_bytes(b"\xff")
    first = _inventory(
        ("skip.bin",),
        _identity("reviewed-a", "skip.bin", disposition="exclude", role="vendor_or_lock"),
    )
    second = _inventory(
        ("skip.bin",),
        _identity("reviewed-b", "skip.bin", disposition="exclude", role="vendor_or_lock"),
    )
    first_snapshot = _module().measure_snapshot(tmp_path, first, _registry()).snapshot
    second_snapshot = _module().measure_snapshot(tmp_path, second, _registry()).snapshot
    assert first_snapshot is not None
    assert second_snapshot is not None
    assert not first_snapshot.measurements
    assert not first_snapshot.coordinates
    assert first_snapshot.snapshot_digest != second_snapshot.snapshot_digest
