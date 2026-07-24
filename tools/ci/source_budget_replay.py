#!/usr/bin/env python3
"""Explicit immutable Git replay for source-budget history and v2 shadow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import tomllib
from contextlib import suppress
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal
from typing import Never
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.adapters.config import source_budget_taxonomy_from_bytes
from ethos.adapters.repo.source_budget.measurement.core import measure_snapshot_bytes
from ethos.adapters.repo.source_budget.snapshots import GitTreeSnapshot
from ethos.adapters.repo.source_budget.snapshots import read_snapshot_blobs
from ethos.adapters.repo.source_budget.snapshots import tree_snapshot
from ethos.domain.source_budget.core import source_budget_metrics_from_bytes
from ethos.domain.source_budget.core import source_budget_taxonomy_digest
from ethos_core.contracts.source_budget.carriers import carrier_manifest_digest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.carriers import validate_carrier_manifest
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshotLoad
from ethos_core.contracts.source_budget.metrics import metric_contracts_digest
from ethos_core.contracts.source_budget.metrics import validate_metric_contracts

_SHA = r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$"
_SHA256 = r"^[0-9a-f]{64}$"
# Compact declarations preserve deterministic order within the code-size hard limit.
_LEAF_CATEGORIES = tuple(
    "python_product python_tests python_tools python_other shell js toml yaml "  # noqa: SIM905
    "json ini jinja diagram".split()
)
_TUPLE_FIELDS = tuple(
    "expected_states expected_absent_categories expected_disagreements "  # noqa: SIM905
    "expected_required_gaps".split()
)


def _invalid(message: str) -> Never:
    raise ValueError(message)


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True, strict=True)


class DeclaredMetrics(_Strict):
    python_product: int = Field(ge=0)
    python_tests: int = Field(ge=0)
    python_tools: int = Field(ge=0)
    python_other: int = Field(ge=0)
    shell: int = Field(ge=0)
    js: int = Field(ge=0)
    toml: int = Field(ge=0)
    yaml: int = Field(ge=0)
    json_count: int = Field(alias="json", ge=0)
    ini: int = Field(ge=0)
    jinja: int = Field(ge=0)
    diagram: int = Field(ge=0)
    python_total: int = Field(ge=0)
    global_total: int = Field(ge=0)


class ExpectedCategories(_Strict):
    js: int | None = Field(default=None, ge=0)
    yaml: int | None = Field(default=None, ge=0)
    diagram: int | None = Field(default=None, ge=0)
    jinja: int | None = Field(default=None, ge=0)


class ExpectedDeltas(_Strict):
    js: int | None = None
    yaml: int | None = None
    diagram: int | None = None
    jinja: int | None = None


class DeclarationBinding(_Strict):
    commit_sha: str = Field(pattern=_SHA)
    tree_sha: str = Field(pattern=_SHA)
    path: str
    blob: str = Field(pattern=_SHA)
    content_sha256: str = Field(pattern=_SHA256)
    baseline_head: str = Field(pattern=_SHA)
    metrics: DeclaredMetrics

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _canonical_path(value)


class HistoryEntry(_Strict):
    profile_kind: Literal["historical_v1", "live_v1", "c1_v2"]
    subject_commit: str = Field(pattern=_SHA)
    subject_tree: str = Field(pattern=_SHA)
    observer_commit: str = Field(pattern=_SHA)
    observer_tree: str = Field(pattern=_SHA)
    taxonomy_path: str
    taxonomy_blob: str = Field(pattern=_SHA)
    taxonomy_content_sha256: str = Field(pattern=_SHA256)
    taxonomy_semantic_sha256: str = Field(pattern=_SHA256)
    expected_states: tuple[Literal["blocked", "unresolved", "reviewed_observation"], ...]
    expected_file_count: int | None = Field(default=None, ge=0)
    expected_inventory_digest: str | None = Field(default=None, pattern=_SHA256)
    expected_global_total: int | None = Field(default=None, ge=0)
    expected_categories: ExpectedCategories = Field(default_factory=ExpectedCategories)
    expected_category_deltas: ExpectedDeltas = Field(default_factory=ExpectedDeltas)
    expected_absent_categories: tuple[str, ...] = ()
    expected_disagreements: tuple[str, ...] = ()
    expected_required_gaps: tuple[str, ...] = ()
    carrier_manifest_path: str | None = None
    carrier_manifest_blob: str | None = Field(default=None, pattern=_SHA)
    carrier_manifest_content_sha256: str | None = Field(default=None, pattern=_SHA256)
    carrier_manifest_semantic_sha256: str | None = Field(default=None, pattern=_SHA256)
    metric_contracts_path: str | None = None
    metric_contracts_blob: str | None = Field(default=None, pattern=_SHA)
    metric_contracts_content_sha256: str | None = Field(default=None, pattern=_SHA256)
    metric_contracts_semantic_sha256: str | None = Field(default=None, pattern=_SHA256)

    @field_validator(*_TUPLE_FIELDS, mode="before")
    @classmethod
    def freeze_toml_array(cls, value: object) -> object:
        return tuple(value) if type(value) is list else value

    @field_validator("taxonomy_path", "carrier_manifest_path", "metric_contracts_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return _canonical_path(value) if value is not None else None

    @field_validator("expected_states")
    @classmethod
    def validate_expected_states(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            _invalid("expected states must be non-empty and unique")
        return value

    @field_validator(*_TUPLE_FIELDS[1:])
    @classmethod
    def validate_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value) or len(value) != len(set(value)):
            _invalid("history tuple items must be non-empty and unique")
        return value

    @model_validator(mode="after")
    def validate_profile_fields(self) -> Self:
        v1_expected = (
            self.expected_file_count,
            self.expected_inventory_digest,
            self.expected_global_total,
        )
        v2_fields = (
            self.carrier_manifest_path,
            self.carrier_manifest_blob,
            self.carrier_manifest_content_sha256,
            self.carrier_manifest_semantic_sha256,
            self.metric_contracts_path,
            self.metric_contracts_blob,
            self.metric_contracts_content_sha256,
            self.metric_contracts_semantic_sha256,
        )
        if self.profile_kind == "c1_v2":
            if any(value is not None for value in v1_expected) or any(
                value is None for value in v2_fields
            ):
                _invalid("C1 history bindings invalid")
        elif any(value is None for value in v1_expected) or any(
            value is not None for value in v2_fields
        ):
            _invalid("v1 history bindings invalid")
        return self


class HistoryConfig(_Strict):
    schema_id: Literal["ethos-source-budget-history-v1"] = Field(alias="schema")
    artifact_root: Literal["build/evidence/quality/source-budget-v2/replay"]
    declaration: DeclarationBinding
    entries: dict[str, HistoryEntry]

    @model_validator(mode="after")
    def validate_entries(self) -> Self:
        if not self.entries or any(not key for key in self.entries):
            _invalid("history entries required")
        return self


def _canonical_path(value: str) -> str:
    if not value or "\\" in value:
        _invalid("history path invalid")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        _invalid("history path invalid")
    return value


def load_history_config(root: Path) -> HistoryConfig:
    """Load the strict replay history owner."""
    path = root / ".config/checks/source-budget/history.toml"
    return HistoryConfig.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))


def _bound_blob(
    root: Path,
    snapshot: GitTreeSnapshot,
    path: str,
    oid: str,
    content_sha256: str,
) -> bytes:
    entry = next((item for item in snapshot.entries if item.relative_path == path), None)
    if entry is None or entry.oid != oid:
        message = f"bound blob identity mismatch:{path}"
        raise ValueError(message)
    load = read_snapshot_blobs(root, snapshot, (path,))
    if load.snapshot is None:
        message = f"bound blob unreadable:{path}"
        raise ValueError(message)
    content = load.snapshot.contents[0][1]
    if hashlib.sha256(content).hexdigest() != content_sha256:
        message = f"bound blob content mismatch:{path}"
        raise ValueError(message)
    return content


def _snapshot(root: Path, commit: str, tree: str) -> GitTreeSnapshot:
    load = tree_snapshot(root, commit)
    if (
        load.snapshot is None
        or load.snapshot.commit_sha != commit
        or load.snapshot.tree_sha != tree
    ):
        message = f"snapshot identity mismatch:{commit}"
        raise ValueError(message)
    return load.snapshot


def _declaration(root: Path, binding: DeclarationBinding) -> None:
    snapshot = _snapshot(root, binding.commit_sha, binding.tree_sha)
    content = _bound_blob(root, snapshot, binding.path, binding.blob, binding.content_sha256)
    payload = tomllib.loads(content.decode("utf-8"))["quality"]["source_budget"]
    if payload["baseline_head"] != binding.baseline_head or payload[
        "baseline"
    ] != binding.metrics.model_dump(mode="python", by_alias=True):
        _invalid("source-budget declaration mismatch")


def _all_bytes(root: Path, snapshot: GitTreeSnapshot) -> tuple[tuple[str, bytes], ...]:
    paths = tuple(item.relative_path for item in snapshot.entries)
    load = read_snapshot_blobs(root, snapshot, paths)
    if load.snapshot is None:
        _invalid("subject blob load failed")
    return load.snapshot.contents


def _expected_mismatches(
    entry: HistoryEntry,
    metrics: dict[str, int],
    inventory: dict[str, object],
    category_deltas: dict[str, int],
) -> list[str]:
    if entry.profile_kind == "c1_v2":
        return []
    gaps: list[str] = []
    checks = (
        ("file_count", inventory["file_count"], entry.expected_file_count),
        ("inventory_digest", inventory["digest"], entry.expected_inventory_digest),
        ("global_total", metrics["global_total"], entry.expected_global_total),
    )
    gaps.extend(
        f"source_budget_replay_expected_mismatch:{name}"
        for name, actual, expected in checks
        if expected is not None and actual != expected
    )
    expected_categories = entry.expected_categories.model_dump(exclude_none=True)
    gaps.extend(
        f"source_budget_replay_expected_mismatch:category:{name}"
        for name, expected in expected_categories.items()
        if metrics.get(name) != expected
    )
    if category_deltas != entry.expected_category_deltas.model_dump(exclude_none=True):
        gaps.append("source_budget_replay_expected_mismatch:category_deltas")
    gaps.extend(
        f"source_budget_replay_expected_mismatch:category_present:{name}"
        for name in entry.expected_absent_categories
        if name in metrics
    )
    return gaps


def _v2_observation(
    root: Path,
    entry: HistoryEntry,
    subject: GitTreeSnapshot,
    contents: tuple[tuple[str, bytes], ...],
) -> tuple[dict[str, object] | None, list[str]]:
    manifest_path = entry.carrier_manifest_path
    contracts_path = entry.metric_contracts_path
    if manifest_path is None or contracts_path is None:
        return None, ["source_budget_replay_v2_binding_missing"]
    by_path = dict(contents)
    manifest_bytes = _bound_blob(
        root,
        subject,
        manifest_path,
        entry.carrier_manifest_blob or "",
        entry.carrier_manifest_content_sha256 or "",
    )
    contracts_bytes = _bound_blob(
        root,
        subject,
        contracts_path,
        entry.metric_contracts_blob or "",
        entry.metric_contracts_content_sha256 or "",
    )
    manifest = validate_carrier_manifest(tomllib.loads(manifest_bytes.decode("utf-8")))
    contracts = validate_metric_contracts(tomllib.loads(contracts_bytes.decode("utf-8")))
    if carrier_manifest_digest(manifest) != entry.carrier_manifest_semantic_sha256:
        return None, ["source_budget_replay_v2_manifest_mismatch"]
    if metric_contracts_digest(contracts) != entry.metric_contracts_semantic_sha256:
        return None, ["source_budget_replay_v2_contracts_mismatch"]
    inventory = classify_carriers(tuple(path for path, _ in contents), manifest)
    selected = tuple(
        (match.relative_path, by_path[match.relative_path])
        for match in inventory.matches
        if match.state == "classified"
    )
    load = measure_snapshot_bytes(selected, inventory, contracts)
    if type(load) is not MeasurementSnapshotLoad:
        return None, ["source_budget_replay_v2_measurement_invalid"]
    coverage: dict[str, int] = {}
    for match in inventory.matches:
        if match.state == "classified" and match.identity is not None:
            profile = match.identity.metric_profile or ""
            coverage[profile] = coverage.get(profile, 0) + 1
    common = {
        "manifest_digest": inventory.manifest_digest,
        "inventory_digest": inventory.inventory_digest,
        "contract_set_digest": metric_contracts_digest(contracts),
        "provider_coverage": dict(sorted(coverage.items())),
    }
    if load.snapshot is None:
        return {
            **common,
            "coordinates": None,
            "vector_digest": None,
            "snapshot_digest": None,
        }, list(load.required_gaps)
    snapshot = load.snapshot
    return {
        **common,
        "coordinates": [item.model_dump(mode="json") for item in snapshot.coordinates],
        "vector_digest": snapshot.vector_digest,
        "snapshot_digest": snapshot.snapshot_digest,
    }, []


def replay_entry(
    root: Path,
    entry_id: str,
    entry: HistoryEntry,
    declaration: DeclarationBinding,
) -> dict[str, object]:
    """Replay one exact subject/observer pair."""
    subject = _snapshot(root, entry.subject_commit, entry.subject_tree)
    observer = _snapshot(root, entry.observer_commit, entry.observer_tree)
    taxonomy_bytes = _bound_blob(
        root,
        observer,
        entry.taxonomy_path,
        entry.taxonomy_blob,
        entry.taxonomy_content_sha256,
    )
    taxonomy = source_budget_taxonomy_from_bytes(taxonomy_bytes)
    semantic = source_budget_taxonomy_digest(taxonomy)
    if semantic != entry.taxonomy_semantic_sha256:
        _invalid("taxonomy semantic digest mismatch")
    contents = _all_bytes(root, subject)
    metrics, inventory = source_budget_metrics_from_bytes(contents, taxonomy)
    declared = declaration.metrics.model_dump(mode="python", by_alias=True)
    category_deltas = {
        name: metrics.get(name, 0) - declared[name]
        for name in _LEAF_CATEGORIES
        if metrics.get(name, 0) != declared[name]
    }
    mismatches = _expected_mismatches(entry, metrics, inventory, category_deltas)
    required_gaps: list[str] = []
    v2: dict[str, object] | None = None
    if entry.profile_kind == "historical_v1":
        disagreements = [f"v1_replay_drift:{metrics['global_total'] - declared['global_total']}"]
        state = "reviewed_observation"
    elif entry.profile_kind == "live_v1":
        disagreements = ["taxonomy_profile_drift:v1-continuation-20260719!=v1-live-at-task4-start"]
        required_gaps = ["source_budget_taxonomy_profile_unresolved"]
        state = "unresolved"
    else:
        v2, required_gaps = _v2_observation(root, entry, subject, contents)
        disagreements = ["v2_provider_gap"] if required_gaps else []
        state = "blocked" if required_gaps else "reviewed_observation"
    required_gaps.extend(mismatches)
    required_gaps = sorted(set(required_gaps))
    transport_valid = (
        state in entry.expected_states
        and disagreements == list(entry.expected_disagreements)
        and not mismatches
        and tuple(required_gaps) == entry.expected_required_gaps
    )
    return {
        "entry_id": entry_id,
        "transport_valid": transport_valid,
        "observer": {
            "profile_id": entry_id,
            "commit_sha": entry.observer_commit,
            "tree_sha": entry.observer_tree,
            "taxonomy_path": entry.taxonomy_path,
            "taxonomy_blob": entry.taxonomy_blob,
            "taxonomy_content_sha256": entry.taxonomy_content_sha256,
            "taxonomy_semantic_sha256": semantic,
        },
        "subject": {
            "commit_sha": subject.commit_sha,
            "tree_sha": subject.tree_sha,
            "snapshot_digest": subject.snapshot_digest,
        },
        "v1": {
            "declaration_commit": declaration.commit_sha,
            "declared_total": declared["global_total"],
            "replay_total": metrics["global_total"],
            "drift": metrics["global_total"] - declared["global_total"],
            "metrics": metrics,
            "category_deltas": category_deltas,
            "inventory": inventory,
        },
        "v2": v2,
        "disagreements": disagreements,
        "required_gaps": required_gaps,
        "comparison_state": state,
    }


def _artifact_output(root: Path, artifact_root: str, requested: Path | None) -> Path:
    expected_root = Path(os.path.normpath(root / artifact_root))
    output = requested if requested is not None else expected_root / "replay.json"
    output = output if output.is_absolute() else root / output
    output = Path(os.path.normpath(output))
    if output == expected_root or not output.is_relative_to(expected_root):
        _invalid("replay output must remain under configured artifact root")
    _reject_symlink_components(root, expected_root)
    _reject_symlink_components(root, output)
    expected_root.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(root, output)
    return output


def _reject_symlink_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        message = "artifact path escaped repository root"
        raise ValueError(message) from exc
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            _invalid("replay artifact path must not contain symlinks")


def _write_artifact(output: Path, payload: dict[str, object]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(output)
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        with suppress(OSError):
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--entry", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-clean", action="store_true")
    return parser


def _selected_entry_ids(history: HistoryConfig, requested: list[str]) -> list[str]:
    selected = requested or list(history.entries)
    if len(selected) != len(set(selected)) or any(item not in history.entries for item in selected):
        _invalid("history entry selection invalid")
    return selected


def _run_replay(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    history = load_history_config(root)
    _declaration(root, history.declaration)
    selected = _selected_entry_ids(history, args.entry)
    entries = [
        replay_entry(root, item, history.entries[item], history.declaration) for item in selected
    ]
    payload: dict[str, object] = {
        "schema": history.schema_id,
        "declaration": history.declaration.model_dump(mode="json", by_alias=True),
        "entries": entries,
    }
    payload["digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output = _artifact_output(root, history.artifact_root, args.output)
    _write_artifact(output, payload)
    valid = all(bool(item["transport_valid"]) for item in entries)
    clean = all(
        item["comparison_state"] == "reviewed_observation" and not item["required_gaps"]
        for item in entries
    )
    return 0 if valid and (clean or not args.require_clean) else 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run_replay(args)
    except (
        KeyError,
        MemoryError,
        OSError,
        UnicodeError,
        ValueError,
        tomllib.TOMLDecodeError,
    ) as exc:
        sys.stderr.write(f"source-budget replay failed: {type(exc).__name__}\n")
        return 2
    return result


if __name__ == "__main__":
    raise SystemExit(main())
