"""Descriptor-bound Budget Contract v2 measurement orchestration."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from contextlib import suppress
from pathlib import Path

from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.native.identity import ResolvedNativeProvider
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

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FINAL_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_RESOURCE_EXHAUSTED_ERRNOS = frozenset({errno.EMFILE, errno.ENFILE, errno.ENOMEM})
_PATH_CONTENT_PAIR_SIZE = 2

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


def _resolve_carrier_provider(
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> tuple[ResolvedNativeProvider | None, str | None]:
    relative = match.relative_path
    if match.state == "excluded":
        return None, f"source_budget_measurement_carrier_excluded:{relative}"
    identity = match.identity
    if match.state != "classified" or identity is None:
        return None, f"source_budget_measurement_carrier_not_classified:{relative}"
    try:
        resolved_contracts = resolve_metric_contracts(identity, contracts)
        return resolve_native_provider(resolved_contracts, contracts), None
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return None, f"source_budget_measurement_contract_invalid:{relative}"


def _measure_admitted_carrier(
    root: Path,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    provider, gap = _resolve_carrier_provider(match, contracts)
    if gap is not None or provider is None:
        return _carrier_failure(gap or "source_budget_measurement_contract_invalid")
    content, gap = _read_carrier(
        root,
        match.relative_path,
        provider.execution_descriptor.max_carrier_bytes,
    )
    if gap is not None:
        return _carrier_failure(gap)
    if content is None:
        return _carrier_failure(f"source_budget_measurement_contract_invalid:{match.relative_path}")
    return _measure_carrier_bytes_admitted(content, match, provider, contracts)


def measure_carrier_bytes(
    content: bytes,
    match: CarrierMatch,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    """Measure one exact classified carrier from already-admitted bytes."""
    try:
        if type(content) is not bytes:
            return _carrier_failure("source_budget_measurement_contract_invalid")
        admitted = _admit_carrier_inputs(Path(), match, contracts)
        if admitted is None:
            return _carrier_failure("source_budget_measurement_contract_invalid")
        _, match, contracts = admitted
        provider, gap = _resolve_carrier_provider(match, contracts)
        if gap is not None or provider is None:
            return _carrier_failure(gap or "source_budget_measurement_contract_invalid")
        return _measure_carrier_bytes_admitted(content, match, provider, contracts)
    except MemoryError:
        relative = getattr(match, "relative_path", "")
        gap = "source_budget_measurement_resource_exhausted"
        if relative:
            gap = f"{gap}:{relative}"
        return _carrier_failure(gap)


def _measure_carrier_bytes_admitted(
    content: bytes,
    match: CarrierMatch,
    provider: ResolvedNativeProvider,
    contracts: MetricContractSet,
) -> CarrierMeasurementLoad:
    if len(content) > provider.execution_descriptor.max_carrier_bytes:
        return _carrier_failure(
            f"source_budget_measurement_carrier_bytes_exceeded:{match.relative_path}"
        )
    return _measure_carrier_content(
        content,
        match.relative_path,
        match,
        provider,
        contracts,
    )


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


def _measure_snapshot_contents(
    contents: tuple[tuple[str, bytes], ...],
    inventory: CarrierInventory,
    contracts: MetricContractSet,
    providers: tuple[ResolvedNativeProvider, ...] | None = None,
) -> tuple[tuple[CarrierMeasurement, ...], tuple[str, ...]]:
    measured: list[CarrierMeasurement] = []
    gaps: list[str] = []
    matches = tuple(item for item in inventory.matches if item.state != "excluded")
    if providers is not None and (
        len(providers) != len(matches)
        or any(type(provider) is not ResolvedNativeProvider for provider in providers)
    ):
        return (), ("source_budget_measurement_contract_invalid",)
    for index, (match, (_, content)) in enumerate(zip(matches, contents, strict=True)):
        try:
            carrier_load = (
                measure_carrier_bytes(content, match, contracts)
                if providers is None
                else _measure_carrier_bytes_admitted(
                    content,
                    match,
                    providers[index],
                    contracts,
                )
            )
            load = _replay_carrier_load(carrier_load, match, contracts)
        except MemoryError:
            return (), (f"source_budget_measurement_resource_exhausted:{match.relative_path}",)
        if load is None:
            gaps.append(f"source_budget_measurement_contract_invalid:{match.relative_path}")
        elif load.measurement is None:
            gaps.extend(load.required_gaps)
        else:
            measured.append(load.measurement)
    return tuple(measured), tuple(gaps)


def _snapshot_load(
    measured: tuple[CarrierMeasurement, ...],
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> MeasurementSnapshotLoad:
    try:
        snapshot = MeasurementSnapshot.from_inventory(
            inventory=inventory,
            contracts=contracts,
            measurements=measured,
        )
        return MeasurementSnapshotLoad(
            snapshot,
            (),
            inventory=inventory,
            contracts=contracts,
        )
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return _snapshot_failure("source_budget_measurement_snapshot_invalid")


def _measure_snapshot_bytes_admitted(
    contents: tuple[tuple[str, bytes], ...],
    inventory: CarrierInventory,
    contracts: MetricContractSet,
    providers: tuple[ResolvedNativeProvider, ...] | None = None,
) -> MeasurementSnapshotLoad:
    measured, gaps = _measure_snapshot_contents(contents, inventory, contracts, providers)
    return _snapshot_failure(*gaps) if gaps else _snapshot_load(measured, inventory, contracts)


def measure_snapshot_bytes(
    contents: tuple[tuple[str, bytes], ...],
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> MeasurementSnapshotLoad:
    """Measure a complete inventory from ordered immutable path/bytes pairs."""
    try:
        admitted = _admit_snapshot_inputs(Path(), inventory, contracts)
    except MemoryError:
        return _snapshot_failure("source_budget_measurement_resource_exhausted")
    if admitted is None or type(contents) is not tuple:
        return _snapshot_failure("source_budget_measurement_contract_invalid")
    _, inventory, contracts = admitted
    if inventory.required_gaps:
        return _snapshot_failure(*inventory.required_gaps)
    expected = tuple(
        match.relative_path for match in inventory.matches if match.state != "excluded"
    )
    valid_items = all(
        type(item) is tuple
        and len(item) == _PATH_CONTENT_PAIR_SIZE
        and type(item[0]) is str
        and type(item[1]) is bytes
        for item in contents
    )
    if not valid_items or tuple(item[0] for item in contents) != expected:
        return _snapshot_failure("source_budget_measurement_snapshot_bytes_invalid")
    return _measure_snapshot_bytes_admitted(contents, inventory, contracts)


def measure_snapshot(
    root: Path,
    inventory: CarrierInventory,
    contracts: MetricContractSet,
) -> MeasurementSnapshotLoad:
    """Read every classified carrier once and delegate ordered bytes measurement."""
    try:
        admitted = _admit_snapshot_inputs(root, inventory, contracts)
    except MemoryError:
        return _snapshot_failure("source_budget_measurement_resource_exhausted")
    if admitted is None:
        return _snapshot_failure("source_budget_measurement_contract_invalid")
    root, inventory, contracts = admitted
    if inventory.required_gaps:
        return _snapshot_failure(*inventory.required_gaps)
    contents: list[tuple[str, bytes]] = []
    providers: list[ResolvedNativeProvider] = []
    gaps: list[str] = []
    for match in inventory.matches:
        if match.state == "excluded":
            continue
        provider, gap = _resolve_carrier_provider(match, contracts)
        if gap is not None or provider is None:
            gaps.append(gap or "source_budget_measurement_contract_invalid")
            continue
        content, gap = _read_carrier(
            root,
            match.relative_path,
            provider.execution_descriptor.max_carrier_bytes,
        )
        if gap is not None or content is None:
            gaps.append(gap or f"source_budget_measurement_contract_invalid:{match.relative_path}")
            continue
        contents.append((match.relative_path, content))
        providers.append(provider)
    if gaps:
        return _snapshot_failure(*gaps)
    try:
        return _measure_snapshot_bytes_admitted(
            tuple(contents),
            inventory,
            contracts,
            tuple(providers),
        )
    except MemoryError:
        return _snapshot_failure("source_budget_measurement_resource_exhausted")


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
