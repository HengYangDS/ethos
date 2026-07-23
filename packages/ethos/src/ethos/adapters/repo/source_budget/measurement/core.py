"""Descriptor-bound Budget Contract v2 measurement orchestration."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.native.identity import resolve_native_provider
from ethos.adapters.repo.source_budget.measurement.router import measure_native
from ethos_core.contracts.source_budget.carriers import CarrierInventory
from ethos_core.contracts.source_budget.carriers import CarrierMatch
from ethos_core.contracts.source_budget.measurements import CarrierMeasurement
from ethos_core.contracts.source_budget.measurements import CarrierMeasurementLoad
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshot
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshotLoad
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import MetricContractSet
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

if TYPE_CHECKING:
    from ethos.adapters.repo.source_budget.measurement.native.identity import ResolvedNativeProvider

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FINAL_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_RESOURCE_EXHAUSTED_ERRNOS = frozenset({errno.EMFILE, errno.ENFILE, errno.ENOMEM})

type _EntryIdentity = tuple[int, int, int]
type _Fingerprint = tuple[int, int, int, int, int, int]
type _OpenedEntry = tuple[int, str, _EntryIdentity]


class _ObjectUnreadableError(Exception):
    pass


class _ObjectUnsupportedError(Exception):
    pass


class _ObjectChangedError(Exception):
    pass


class _ResourceExhaustedError(Exception):
    pass


class _CarrierBytesExceededError(Exception):
    pass


def _require_carrier_byte_limit(size: int, limit: int) -> None:
    if size > limit:
        raise _CarrierBytesExceededError


def _object_read_error(exc: OSError) -> Exception:
    if exc.errno in _RESOURCE_EXHAUSTED_ERRNOS:
        return _ResourceExhaustedError()
    return _ObjectUnreadableError()


def _require_directory(value: os.stat_result) -> None:
    if not stat.S_ISDIR(value.st_mode):
        raise _ObjectUnsupportedError


def _require_regular_file(value: os.stat_result) -> None:
    if not stat.S_ISREG(value.st_mode):
        raise _ObjectUnsupportedError


def _require_stable_fingerprint(before: os.stat_result, after: os.stat_result) -> None:
    if _fingerprint(after) != _fingerprint(before):
        raise _ObjectChangedError


def measure_carrier(
    root: Path,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    """Measure one exact classified worktree carrier or fail closed."""
    try:
        admitted = _admit_carrier_inputs(root, match, contracts)
    except MemoryError:
        return _carrier_failure("source_budget_measurement_resource_exhausted")
    if admitted is None:
        return _carrier_failure("source_budget_measurement_contract_invalid")
    try:
        return _measure_admitted_carrier(*admitted)
    except MemoryError:
        return _carrier_failure(
            f"source_budget_measurement_resource_exhausted:{admitted[1].relative_path}"
        )


def _measure_admitted_carrier(
    root: Path,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    relative = match.relative_path
    if match.state == "excluded":
        return _carrier_failure(f"source_budget_measurement_carrier_excluded:{relative}")
    identity = match.identity
    if match.state != "classified" or identity is None:
        return _carrier_failure(f"source_budget_measurement_carrier_not_classified:{relative}")
    try:
        resolved_contracts = resolve_metric_contracts(identity, contracts)
        provider = resolve_native_provider(resolved_contracts, contracts)
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{relative}")
    content, gap = _read_carrier(
        root,
        relative,
        provider.execution_descriptor.max_carrier_bytes,
    )
    if gap is not None:
        return _carrier_failure(gap)
    if content is None:
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{relative}")
    return _measure_carrier_content(content, relative, match, provider, contracts)


def _measure_carrier_content(
    content: bytes,
    relative: str,
    match: CarrierMatch,
    provider: ResolvedNativeProvider,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    try:
        native = measure_native(content, provider, contracts)
        return _load_native_measurement(content, relative, match, contracts, native)
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{relative}")


def _load_native_measurement(
    content: bytes,
    relative: str,
    match: CarrierMatch,
    contracts: MetricContractSet,
    native: NativeMeasurementLoad,
) -> CarrierMeasurementLoad:
    if type(native) is not NativeMeasurementLoad:
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{relative}")
    native = NativeMeasurementLoad(native.measurement, native.required_gaps)
    if native.measurement is None:
        return _carrier_failure(*_path_gaps(relative, native.required_gaps))
    if native.measurement.content_sha256 != hashlib.sha256(content).hexdigest():
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{relative}")
    measurement = CarrierMeasurement.create(
        match=match,
        contracts=contracts,
        native=native.measurement,
    )
    return CarrierMeasurementLoad(
        measurement,
        (),
        match=match,
        contracts=contracts,
    )


def _replay_carrier_load(
    load: CarrierMeasurementLoad,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad | None:
    if type(load) is not CarrierMeasurementLoad:
        return None
    try:
        if load.measurement is None:
            return CarrierMeasurementLoad(None, load.required_gaps)
        return CarrierMeasurementLoad(
            load.measurement,
            load.required_gaps,
            match=match,
            contracts=contracts,
        )
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return None


def measure_snapshot(
    root: Path,
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> MeasurementSnapshotLoad:
    """Measure every classified carrier and expose no partial snapshot."""
    try:
        admitted = _admit_snapshot_inputs(root, inventory, contracts)
    except MemoryError:
        return _snapshot_failure("source_budget_measurement_resource_exhausted")
    if admitted is None:
        return _snapshot_failure("source_budget_measurement_contract_invalid")
    try:
        return _measure_admitted_snapshot(*admitted)
    except MemoryError:
        return _snapshot_failure("source_budget_measurement_resource_exhausted")


def _measure_admitted_snapshot(
    root: Path,
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> MeasurementSnapshotLoad:
    if inventory.required_gaps:
        return _snapshot_failure(*inventory.required_gaps)
    measured: list[CarrierMeasurement] = []
    gaps: list[str] = []
    for match in inventory.matches:
        if match.state == "excluded":
            continue
        try:
            load = _replay_carrier_load(measure_carrier(root, match, contracts), match, contracts)
        except MemoryError:
            return _snapshot_failure(
                f"source_budget_measurement_resource_exhausted:{match.relative_path}"
            )
        if load is None:
            gaps.append(f"source_budget_measurement_contract_invalid:{match.relative_path}")
        elif load.measurement is None:
            gaps.extend(load.required_gaps)
        else:
            measured.append(load.measurement)
    if gaps:
        return _snapshot_failure(*gaps)
    try:
        snapshot = MeasurementSnapshot.from_inventory(
            inventory=inventory,
            contracts=contracts,
            measurements=tuple(measured),
        )
        return MeasurementSnapshotLoad(
            snapshot,
            (),
            inventory=inventory,
            contracts=contracts,
        )
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return _snapshot_failure("source_budget_measurement_snapshot_invalid")


def _admit_carrier_inputs(
    root: Path,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> tuple[Path, CarrierMatch, MetricContractSet] | None:
    if not isinstance(root, Path) or type(match) is not CarrierMatch:
        return None
    canonical_contracts = _canonical_contracts(contracts)
    if canonical_contracts is None:
        return None
    try:
        canonical_match = CarrierMatch.model_validate(match.model_dump(mode="python"))
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None
    return root, canonical_match, canonical_contracts


def _admit_snapshot_inputs(
    root: Path,
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> tuple[Path, CarrierInventory, MetricContractSet] | None:
    if not isinstance(root, Path) or type(inventory) is not CarrierInventory:
        return None
    canonical_contracts = _canonical_contracts(contracts)
    if canonical_contracts is None:
        return None
    try:
        canonical_inventory = CarrierInventory.model_validate(inventory.model_dump(mode="python"))
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None
    return root, canonical_inventory, canonical_contracts


def _canonical_contracts(contracts: MetricContractSet) -> MetricContractSet | None:
    if type(contracts) is not MetricContractSet:
        return None
    try:
        return MetricContractSet.model_validate(contracts.model_dump(mode="python", by_alias=True))
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _read_carrier(
    root: Path,
    relative: str,
    max_carrier_bytes: int,
) -> tuple[bytes | None, str | None]:
    try:
        return _read_stable_bytes(root, relative, max_carrier_bytes), None
    except _CarrierBytesExceededError:
        return None, f"source_budget_measurement_carrier_bytes_exceeded:{relative}"
    except _ObjectUnsupportedError:
        return None, f"source_budget_measurement_object_unsupported:{relative}"
    except _ObjectChangedError:
        return None, f"source_budget_measurement_object_changed:{relative}"
    except _ResourceExhaustedError:
        return None, f"source_budget_measurement_resource_exhausted:{relative}"
    except _ObjectUnreadableError:
        return None, f"source_budget_measurement_object_unreadable:{relative}"


def _read_stable_bytes(root: Path, relative: str, max_carrier_bytes: int) -> bytes:
    descriptors: list[int] = []
    entries: list[_OpenedEntry] = []
    content: bytes | None = None
    failure: Exception | None = None
    close_failed = False
    try:
        root_fd = os.open(root, _DIRECTORY_FLAGS)
        _register_descriptor(descriptors, root_fd)
        _require_directory(os.fstat(root_fd))
        parent_fd = root_fd
        parts = relative.split("/")
        for name in parts[:-1]:
            child_fd = _open_component(parent_fd, name, _DIRECTORY_FLAGS, directory=True)
            _register_descriptor(descriptors, child_fd)
            child_state = os.fstat(child_fd)
            _require_directory(child_state)
            entries.append((parent_fd, name, _entry_identity(child_state)))
            parent_fd = child_fd
        final_name = parts[-1]
        final_fd = _open_component(parent_fd, final_name, _FINAL_FLAGS, directory=False)
        _register_descriptor(descriptors, final_fd)
        before = os.fstat(final_fd)
        _require_regular_file(before)
        _require_carrier_byte_limit(before.st_size, max_carrier_bytes)
        entries.append((parent_fd, final_name, _entry_identity(before)))
        content = _read_exact(final_fd, before.st_size, max_carrier_bytes)
        after = os.fstat(final_fd)
        _require_stable_fingerprint(before, after)
        _reverify_entries(entries)
    except (
        _ObjectChangedError,
        _CarrierBytesExceededError,
        _ResourceExhaustedError,
        _ObjectUnreadableError,
        _ObjectUnsupportedError,
    ) as exc:
        failure = exc
    except MemoryError as exc:
        failure = _ResourceExhaustedError()
        failure.__cause__ = exc
    except OSError as exc:
        failure = _object_read_error(exc)
        failure.__cause__ = exc
    except (AttributeError, TypeError, ValueError) as exc:
        failure = _ObjectUnreadableError()
        failure.__cause__ = exc
    finally:
        close_failed = _close_descriptors(descriptors)
    if failure is not None:
        raise failure
    if close_failed or content is None:
        raise _ObjectUnreadableError
    return content


def _register_descriptor(descriptors: list[int], descriptor: int) -> None:
    try:
        descriptors.append(descriptor)
    except MemoryError:
        with suppress(OSError):
            os.close(descriptor)
        raise


def _open_component(parent_fd: int, name: str, flags: int, *, directory: bool) -> int:
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        if _entry_is_unsupported(parent_fd, name, directory=directory):
            raise _ObjectUnsupportedError from exc
        raise


def _entry_is_unsupported(parent_fd: int, name: str, *, directory: bool) -> bool:
    try:
        observed = os.lstat(name, dir_fd=parent_fd)
    except OSError:
        return False
    return not (stat.S_ISDIR(observed.st_mode) if directory else stat.S_ISREG(observed.st_mode))


def _read_exact(fd: int, expected_size: int, max_carrier_bytes: int) -> bytes:
    content = os.read(fd, min(expected_size + 1, max_carrier_bytes + 1))
    if len(content) > max_carrier_bytes:
        raise _CarrierBytesExceededError
    if len(content) != expected_size:
        raise _ObjectChangedError
    return content


def _reverify_entries(entries: list[_OpenedEntry]) -> None:
    for parent_fd, name, expected in entries:
        try:
            observed = os.lstat(name, dir_fd=parent_fd)
        except OSError as exc:
            raise _object_read_error(exc) from exc
        if _entry_identity(observed) != expected:
            raise _ObjectChangedError


def _entry_identity(value: os.stat_result) -> _EntryIdentity:
    return value.st_dev, value.st_ino, value.st_mode


def _fingerprint(value: os.stat_result) -> _Fingerprint:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _close_descriptors(descriptors: list[int]) -> bool:
    failed = False
    for fd in reversed(descriptors):
        try:
            os.close(fd)
        except OSError:
            failed = True
    return failed


def _path_gaps(relative: str, gaps: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{gap}:{relative}" for gap in gaps)


def _carrier_failure(*gaps: str) -> CarrierMeasurementLoad:
    return CarrierMeasurementLoad(None, tuple(sorted(set(gaps))))


def _snapshot_failure(*gaps: str) -> MeasurementSnapshotLoad:
    return MeasurementSnapshotLoad(None, tuple(sorted(set(gaps))))
