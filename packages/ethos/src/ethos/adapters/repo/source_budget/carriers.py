"""Repository loaders for Budget Contract v2 carrier and metric declarations."""

from __future__ import annotations

import re
import stat
import subprocess
import tomllib
import typing as t
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as carrier
import ethos_core.contracts.source_budget.metrics as metric

CARRIER_MANIFEST_PATH = Path("system/policies/source-budget-carriers.toml")
METRIC_CONTRACTS_PATH = Path("system/policies/source-budget-metrics.toml")
_GIT_ARGS = ["ls-files", "-z", "-t", "--stage", "--cached", "--others", "--exclude-standard"]
_REGULAR = {"100644", "100755"}
_W = "present worktree "


@dataclass(frozen=True, slots=True)
class PresentWorktreePathsLoad:
    """A Git inventory read that yields stable regular paths or required gaps."""

    paths: tuple[str, ...] | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject partial, empty-clean, or unstable inventory envelopes."""
        if error := _envelope_error(self.paths, self.required_gaps):
            _err(_W + error)


def _envelope_error(paths: object, gaps: object) -> str:
    checks = (
        (_strings(gaps), "required gaps must be non-empty strings"),
        (_stable(gaps), "required gaps must be unique and stably ordered"),
        (paths is not None or bool(gaps), "path load requires non-empty required gaps"),
        (paths is None or _strings(paths), "paths must be non-empty strings"),
        (paths is None or bool(paths), "path load requires non-empty paths"),
        (paths is None or not gaps, "path load with data forbids required gaps"),
        (paths is None or _stable(paths), "paths must be unique and stably ordered"),
    )
    return next((message for valid, message in checks if not valid), "")


def load_carrier_manifest(root: Path) -> carrier.CarrierManifestLoad:
    """Load the independent v2 carrier manifest or fail closed."""
    return _policy(root, "carrier")


def load_metric_contracts(root: Path) -> metric.MetricContractSetLoad:
    """Load the independent v2 metric registry or fail closed."""
    return _policy(root, "metric")


def _policy(root: Path, kind: str) -> t.Any:
    spec: tuple[t.Any, ...] = {
        "carrier": (
            CARRIER_MANIFEST_PATH,
            "carrier_manifest",
            carrier.validate_carrier_manifest,
            carrier.CarrierManifestLoad,
        ),
        "metric": (
            METRIC_CONTRACTS_PATH,
            "metric_contracts",
            metric.validate_metric_contracts,
            metric.MetricContractSetLoad,
        ),
    }[kind]
    path, code, validate, wrap = spec
    try:
        payload = tomllib.loads((root / path).read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError, UnicodeError) as error:
        suffix = next(
            name
            for exception, name in (
                (FileNotFoundError, "missing"),
                (tomllib.TOMLDecodeError, "invalid_toml"),
                (OSError, "unreadable"),
                (UnicodeError, "unreadable"),
            )
            if isinstance(error, exception)
        )
        return wrap(None, (_gap(f"{code}_{suffix}"),))
    try:
        return wrap(validate(payload), ())
    except (ValidationError, ValueError):
        return wrap(None, (_gap(f"{code}_invalid"),))


def load_present_worktree_paths(root: Path) -> PresentWorktreePathsLoad:
    """Load present regular Git paths without erasing inventory failures."""
    records, gap = _git_records(root)
    if gap:
        return PresentWorktreePathsLoad(None, (gap,))
    admitted = tuple(_admit(root, raw) for raw in records or ())
    paths = tuple(sorted({path for path, _ in admitted if path is not None}))
    gaps = tuple(sorted({item for _, item in admitted if item is not None}))
    return PresentWorktreePathsLoad(
        paths if paths and not gaps else None,
        gaps or (() if paths else (_gap("inventory_empty"),)),
    )


def classify_carriers(
    paths: t.Iterable[str], manifest: carrier.CarrierManifest
) -> carrier.CarrierInventory:
    """Classify one repository inventory through the typed manifest."""
    return carrier.classify_carriers(paths, manifest)


def _git_records(root: Path) -> tuple[tuple[bytes, ...] | None, str | None]:
    try:
        result = subprocess.run(["git", *_GIT_ARGS], cwd=root, capture_output=True, check=False)
    except OSError:
        return (None, _gap("inventory_git_unavailable"))
    if result.returncode:
        return (None, _gap("inventory_git_failed"))
    if not result.stdout:
        return ((), None)
    records = tuple(result.stdout[:-1].split(b"\0")) if result.stdout.endswith(b"\0") else ()
    return (
        (records, None)
        if records and all(records)
        else (None, _gap("inventory_git_output_invalid"))
    )


def _admit(root: Path, raw: bytes) -> tuple[str | None, str | None]:
    if len(raw) <= len(b"H ") or raw[1:2] != b" ":
        return _bad()
    tag, payload = raw[:1], raw[2:]
    if tag == b"?":
        return _present(root, payload.decode("utf-8", errors="surrogateescape"), None)
    match = re.fullmatch(
        rb"([0-9]{6}) [0-9a-f]{40}(?:[0-9a-f]{24})? ([0-3])\t(.*)", payload, re.DOTALL
    )
    if tag not in {b"H", b"M", b"S"} or match is None:
        return _bad()
    mode, stage = (value.decode() for value in match.group(1, 2))
    path = match.group(3).decode("utf-8", errors="surrogateescape")
    safe, label = _safe_path(path)
    if tag == b"M":
        result = _bad() if stage == "0" else (None, _gap("inventory_index_unmerged", label))
    elif stage != "0":
        result = _bad()
    elif not safe:
        result = (None, _gap("inventory_path_invalid", label))
    elif mode not in _REGULAR:
        kind = {"120000": "symlink", "160000": "gitlink"}.get(mode, mode)
        result = (None, _gap("inventory_object_unsupported", kind, label))
    else:
        result = _present(root, path, mode)
    return result


def _present(root: Path, path: str, mode: str | None) -> tuple[str | None, str | None]:
    safe, label = _safe_path(path)
    if mode is None and not safe:
        return (None, _gap("inventory_path_invalid", label))
    kind = _worktree_object_kind(root, path)
    if kind in {"regular", "missing"}:
        return ((path if kind == "regular" else None), None)
    if kind == "unreadable":
        return (None, _gap("inventory_object_unreadable", label))
    if mode is None:
        return (None, _gap("inventory_object_unsupported", "untracked_" + kind, label))
    code = (
        "inventory_object_unsupported" if kind.endswith("ancestor") else "inventory_object_mismatch"
    )
    parts = (kind, label) if code.endswith("unsupported") else (mode, kind, label)
    return (None, _gap(code, *parts))


def _safe_path(path: str) -> tuple[bool, str]:
    try:
        path.encode()
    except UnicodeEncodeError:
        return (False, "<invalid-path>")
    safe = bool(
        path
        and not path.startswith(("/", "./"))
        and "\\" not in path
        and "\0" not in path
        and all(part not in {"", ".", ".."} for part in path.split("/"))
    )
    return (safe, path or "<empty>")


def _worktree_object_kind(root: Path, relative: str) -> str:
    parts, current = relative.split("/"), root
    for part in parts[:-1]:
        current /= part
        if (kind := _kind(current, ancestor=True)) != "directory":
            return kind
    return _kind(current / parts[-1], ancestor=False)


def _kind(path: Path, *, ancestor: bool) -> str:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    labels = (
        (stat.S_ISLNK, "symlink_ancestor" if ancestor else "symlink"),
        (stat.S_ISDIR, "directory"),
        (stat.S_ISREG, "non_directory_ancestor" if ancestor else "regular"),
    )
    return next(
        (label for check, label in labels if check(mode)),
        "non_directory_ancestor" if ancestor else "other",
    )


def _bad() -> tuple[None, str]:
    return (None, _gap("inventory_git_output_invalid"))


def _err(message: str) -> t.NoReturn:
    raise ValueError(message)


def _gap(code: str, *parts: str) -> str:
    return ":".join((f"source_budget_{code}", *parts))


def _strings(values: object) -> bool:
    return isinstance(values, tuple) and all(isinstance(value, str) and value for value in values)


def _stable(values: object) -> bool:
    if not _strings(values):
        return False
    items = t.cast("tuple[str, ...]", values)
    return items == tuple(sorted(set(items)))
