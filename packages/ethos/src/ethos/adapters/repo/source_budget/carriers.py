"""Repository loaders for Budget Contract v2 carrier and metric declarations."""

from __future__ import annotations

import stat
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as carrier_contracts
from ethos_core.contracts.source_budget.carriers import CarrierManifestLoad
from ethos_core.contracts.source_budget.carriers import validate_carrier_manifest
from ethos_core.contracts.source_budget.metrics import MetricContractSetLoad
from ethos_core.contracts.source_budget.metrics import validate_metric_contracts

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import NoReturn

CARRIER_MANIFEST_PATH = Path("system/policies/source-budget-carriers.toml")
METRIC_CONTRACTS_PATH = Path("system/policies/source-budget-metrics.toml")
GIT_MODE_LENGTH = 6
MIN_TAGGED_RECORD_LENGTH = 3
TRACKED_TAGS = frozenset({b"H", b"M", b"S"})
REGULAR_GIT_MODES = frozenset({"100644", "100755"})


@dataclass(frozen=True, slots=True)
class PresentWorktreePathsLoad:
    """A Git inventory read that yields stable regular paths or required gaps."""

    paths: tuple[str, ...] | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject partial, empty-clean, or unstable inventory envelopes."""
        if not isinstance(self.required_gaps, tuple) or any(
            not isinstance(gap, str) or not gap for gap in self.required_gaps
        ):
            _raise_inventory_contract_error(
                "present worktree required gaps must be non-empty strings"
            )
        if self.required_gaps != tuple(sorted(set(self.required_gaps))):
            _raise_inventory_contract_error(
                "present worktree required gaps must be unique and stably ordered"
            )
        if self.paths is None:
            if not self.required_gaps:
                _raise_inventory_contract_error(
                    "present worktree path load requires non-empty required gaps"
                )
            return
        if not isinstance(self.paths, tuple) or any(
            not isinstance(path, str) or not path for path in self.paths
        ):
            _raise_inventory_contract_error("present worktree paths must be non-empty strings")
        if not self.paths:
            _raise_inventory_contract_error("present worktree path load requires non-empty paths")
        if self.required_gaps:
            _raise_inventory_contract_error(
                "present worktree path load with data forbids required gaps"
            )
        if self.paths != tuple(sorted(set(self.paths))):
            _raise_inventory_contract_error(
                "present worktree paths must be unique and stably ordered"
            )


def load_carrier_manifest(root: Path) -> CarrierManifestLoad:
    """Load the independent v2 carrier manifest or fail closed."""
    path = root / CARRIER_MANIFEST_PATH
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_missing",))
    except tomllib.TOMLDecodeError:
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_invalid_toml",))
    except (OSError, UnicodeError):
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_unreadable",))
    try:
        return CarrierManifestLoad(validate_carrier_manifest(payload), ())
    except (ValidationError, ValueError):
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_invalid",))


def load_metric_contracts(root: Path) -> MetricContractSetLoad:
    """Load the independent v2 metric registry or fail closed."""
    path = root / METRIC_CONTRACTS_PATH
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_missing",))
    except tomllib.TOMLDecodeError:
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_invalid_toml",))
    except (OSError, UnicodeError):
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_unreadable",))
    try:
        return MetricContractSetLoad(validate_metric_contracts(payload), ())
    except (ValidationError, ValueError):
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_invalid",))


def load_present_worktree_paths(root: Path) -> PresentWorktreePathsLoad:
    """Load present regular Git paths without erasing inventory failures."""
    output, gap = _read_git_inventory(root)
    if gap is not None:
        return PresentWorktreePathsLoad(None, (gap,))
    assert output is not None

    records, framing_gap = _parse_inventory_records(output)
    if framing_gap is not None:
        return PresentWorktreePathsLoad(None, (framing_gap,))
    assert records is not None

    paths: set[str] = set()
    gaps: set[str] = set()
    for raw in records:
        path, record_gap = _admit_inventory_record(root, raw)
        if path is not None:
            paths.add(path)
        if record_gap is not None:
            gaps.add(record_gap)
    if gaps:
        return PresentWorktreePathsLoad(None, tuple(sorted(gaps)))
    if not paths:
        return PresentWorktreePathsLoad(None, ("source_budget_inventory_empty",))
    return PresentWorktreePathsLoad(tuple(sorted(paths)), ())


def classify_carriers(
    paths: Iterable[str],
    manifest: carrier_contracts.CarrierManifest,
) -> carrier_contracts.CarrierInventory:
    """Classify one repository inventory through the typed manifest."""
    return carrier_contracts.classify_carriers(paths, manifest)


def _read_git_inventory(root: Path) -> tuple[bytes | None, str | None]:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "-t",
                "--stage",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None, "source_budget_inventory_git_unavailable"
    if completed.returncode != 0:
        return None, "source_budget_inventory_git_failed"
    return completed.stdout, None


def _parse_inventory_records(
    output: bytes,
) -> tuple[tuple[bytes, ...] | None, str | None]:
    if not output:
        return (), None
    if not output.endswith(b"\0"):
        return None, "source_budget_inventory_git_output_invalid"
    records = tuple(output[:-1].split(b"\0"))
    if any(not record for record in records):
        return None, "source_budget_inventory_git_output_invalid"
    return records, None


def _admit_inventory_record(
    root: Path,
    raw: bytes,
) -> tuple[str | None, str | None]:
    if len(raw) < MIN_TAGGED_RECORD_LENGTH or raw[1:2] != b" ":
        return None, "source_budget_inventory_git_output_invalid"
    tag = raw[:1]
    payload = raw[2:]
    if tag == b"?":
        return _admit_untracked_record(root, payload)
    if tag not in TRACKED_TAGS:
        return None, "source_budget_inventory_git_output_invalid"
    return _admit_tracked_record(root, tag, payload)


def _admit_tracked_record(
    root: Path,
    tag: bytes,
    raw: bytes,
) -> tuple[str | None, str | None]:
    parsed = _parse_stage_record(raw)
    if parsed is None:
        return None, "source_budget_inventory_git_output_invalid"
    mode, stage, relative = parsed
    gap = _tracked_record_gap(tag, mode, stage, relative)
    if gap is not None:
        return None, gap
    return _admit_regular_tracked_path(root, mode, relative)


def _tracked_record_gap(
    tag: bytes,
    mode: str,
    stage: str,
    relative: str,
) -> str | None:
    safe_relative = _safe_gap_path(relative)
    if tag == b"M":
        if stage == "0":
            return "source_budget_inventory_git_output_invalid"
        return f"source_budget_inventory_index_unmerged:{safe_relative}"
    if stage != "0":
        return "source_budget_inventory_git_output_invalid"
    if not _safe_relative_for_access(relative):
        return f"source_budget_inventory_path_invalid:{safe_relative}"
    if mode not in REGULAR_GIT_MODES:
        object_kind = {"120000": "symlink", "160000": "gitlink"}.get(mode, mode)
        return f"source_budget_inventory_object_unsupported:{object_kind}:{safe_relative}"
    return None


def _admit_regular_tracked_path(
    root: Path,
    mode: str,
    relative: str,
) -> tuple[str | None, str | None]:
    kind = _worktree_object_kind(root, relative)
    if kind == "regular":
        return relative, None
    if kind == "missing":
        return None, None
    return None, _tracked_worktree_gap(mode, kind, relative)


def _tracked_worktree_gap(mode: str, kind: str, relative: str) -> str:
    safe_relative = _safe_gap_path(relative)
    if kind == "unreadable":
        return f"source_budget_inventory_object_unreadable:{safe_relative}"
    if kind in {"symlink_ancestor", "non_directory_ancestor"}:
        return f"source_budget_inventory_object_unsupported:{kind}:{safe_relative}"
    return f"source_budget_inventory_object_mismatch:{mode}:{kind}:{safe_relative}"


def _admit_untracked_record(
    root: Path,
    raw: bytes,
) -> tuple[str | None, str | None]:
    relative = raw.decode("utf-8", errors="surrogateescape")
    safe_relative = _safe_gap_path(relative)
    if not _safe_relative_for_access(relative):
        return None, f"source_budget_inventory_path_invalid:{safe_relative}"
    kind = _worktree_object_kind(root, relative)
    if kind == "missing":
        return None, None
    if kind == "regular":
        return relative, None
    if kind == "unreadable":
        return None, f"source_budget_inventory_object_unreadable:{safe_relative}"
    return (
        None,
        f"source_budget_inventory_object_unsupported:untracked_{kind}:{safe_relative}",
    )


def _parse_stage_record(raw: bytes) -> tuple[str, str, str] | None:
    try:
        header, raw_path = raw.split(b"\t", 1)
        raw_mode, raw_object, raw_stage = header.split(b" ")
        mode = raw_mode.decode("ascii")
        object_id = raw_object.decode("ascii")
        stage = raw_stage.decode("ascii")
    except (UnicodeDecodeError, ValueError):
        return None
    if len(mode) != GIT_MODE_LENGTH or not mode.isdigit() or stage not in {"0", "1", "2", "3"}:
        return None
    if len(object_id) not in {40, 64} or any(char not in "0123456789abcdef" for char in object_id):
        return None
    return mode, stage, raw_path.decode("utf-8", errors="surrogateescape")


def _safe_relative_for_access(relative: str) -> bool:
    try:
        relative.encode("utf-8")
    except UnicodeEncodeError:
        return False
    if not relative or relative.startswith(("/", "./")) or "\\" in relative or "\0" in relative:
        return False
    return all(part not in {"", ".", ".."} for part in relative.split("/"))


def _safe_gap_path(relative: str) -> str:
    try:
        relative.encode("utf-8")
    except UnicodeEncodeError:
        return "<invalid-path>"
    return relative or "<empty>"


def _worktree_object_kind(root: Path, relative: str) -> str:
    parts = relative.split("/")
    current = root
    for part in parts[:-1]:
        current /= part
        kind = _ancestor_object_kind(current)
        if kind != "directory":
            return kind
    return _final_object_kind(current / parts[-1])


def _ancestor_object_kind(path: Path) -> str:
    mode = _lstat_mode(path)
    if isinstance(mode, str):
        return mode
    if stat.S_ISLNK(mode):
        return "symlink_ancestor"
    if stat.S_ISDIR(mode):
        return "directory"
    return "non_directory_ancestor"


def _final_object_kind(path: Path) -> str:
    mode = _lstat_mode(path)
    if isinstance(mode, str):
        return mode
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    return "other"


def _lstat_mode(path: Path) -> int | str:
    try:
        return path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"


def _raise_inventory_contract_error(message: str) -> NoReturn:
    raise ValueError(message)
