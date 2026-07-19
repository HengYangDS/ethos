"""Fail-closed semantic merge for source-budget debt ledgers."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git

if TYPE_CHECKING:
    from pathlib import Path

RULES_PATH = ".ethos/rules.toml"
RECORD = "[[quality.source_budget.debt.records]]"
SECTION = "[quality.source_budget.debt]"
RECORD_CHILD_PREFIX = "[quality.source_budget.debt.records."
MAXIMUM_TOTAL = re.compile(r"^maximum_total\s*=\s*\d+\s*$", re.MULTILINE)
_INVALID_RECORD_TABLE = "merged source-budget record must be a table"
_INVALID_RECORD_IDENTITY = "merged source-budget record violates its identity contract"
_MISSING_MAXIMUM_TOTAL = "source-budget ledger has no unique maximum_total declaration"


class ProjectionResolution(TypedDict):
    """Minimal dependency-injected result for semantic rebase recovery."""

    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]


Resolution = Callable[..., ProjectionResolution]
UnmergedPaths = Callable[..., list[str]]


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """One source-budget record, retaining semantic data and its source block."""

    identifier: str
    block: str
    allowance: int
    data: dict[str, object]


def resolve_source_budget_ledger_rebase_conflict(
    root: Path,
    *,
    resolution: Resolution | None = None,
    unmerged_paths: UnmergedPaths | None = None,
) -> ProjectionResolution:
    """Resolve only independent append-only source-budget debt additions.

    ``resolution`` and ``unmerged_paths`` are supplied by the already-loaded
    rebase runtime.  That keeps recovery independent of whichever historical
    source snapshot Git has checked out while replaying the lane.
    """
    result = resolution or projection_resolution
    paths_reader = unmerged_paths or unresolved_paths
    paths = paths_reader(root)
    if paths != [RULES_PATH] or (merged := merge(root, run_git)) is None:
        return result(ok=False, paths=paths)
    (root / RULES_PATH).write_text(merged, encoding="utf-8")
    if run_git(root, "add", RULES_PATH, check=False).returncode:
        return result(ok=False, paths=paths)
    return result(
        ok=True,
        paths=paths,
        gaps=["semantic_ledger_merged:source_budget_debt"],
        next_actions=["rerun source-budget validation after the refreshed lane is complete"],
    )


def projection_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> ProjectionResolution:
    """Return the minimal recovery result when no core helper is injected."""
    return {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": next_actions or [],
    }


def unresolved_paths(root: Path) -> list[str]:
    """Read unresolved paths without importing the projection-rebase core."""
    completed = run_git(root, "diff", "--name-only", "--diff-filter=U", check=False)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def merge(root: Path, git: Callable[..., Any]) -> str | None:
    """Merge independent appended or field-disjoint record changes."""
    texts = [git(root, "show", f":{stage}:{RULES_PATH}", check=False) for stage in (1, 2, 3)]
    if any(result.returncode for result in texts):
        return None
    base, candidate, lane = (parse(result.stdout) for result in texts)
    if not base or not candidate or not lane or len({base[0], candidate[0], lane[0]}) != 1:
        return None
    records = merge_records(base[1], candidate[1], lane[1])
    return replace(texts[1].stdout, records) if records is not None else None


def parse(text: str) -> tuple[str, list[LedgerRecord]] | None:
    """Parse records while preserving each record and its nested TOML tables."""
    try:
        records = tomllib.loads(text)["quality"]["source_budget"]["debt"]["records"]
    except (KeyError, tomllib.TOMLDecodeError, TypeError):
        return None
    start = text.find(SECTION)
    record_start = text.find(RECORD, start)
    if not isinstance(records, list) or not records or start < 0 or record_start < 0:
        return None
    end = next_section(text, record_start)
    blocks = split(text[record_start:end])
    if len(records) != len(blocks):
        return None
    entries: list[LedgerRecord] = []
    for record, block in zip(records, blocks, strict=True):
        if not isinstance(record, dict):
            return None
        identifier, allowance = record.get("id"), record.get("allowance")
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or not isinstance(allowance, int)
            or isinstance(allowance, bool)
            or allowance < 0
        ):
            return None
        entries.append(
            LedgerRecord(identifier, block, allowance, cast("dict[str, object]", record))
        )
    return (
        (text[:start] + text[end:], entries)
        if len({item.identifier for item in entries}) == len(entries)
        else None
    )


def merge_records(
    base: list[LedgerRecord], candidate: list[LedgerRecord], lane: list[LedgerRecord]
) -> list[LedgerRecord] | None:
    """Merge records by stable ID, including a one-sided retirement against an untouched peer."""
    base_by_id = {record.identifier: record for record in base}
    candidate_by_id = {record.identifier: record for record in candidate}
    lane_by_id = {record.identifier: record for record in lane}
    merged: list[LedgerRecord] = []
    for base_record in base:
        candidate_record = candidate_by_id.get(base_record.identifier)
        lane_record = lane_by_id.get(base_record.identifier)
        if candidate_record is None:
            if lane_record == base_record:
                continue
            return None
        if lane_record is None:
            if candidate_record == base_record:
                continue
            return None
        if candidate_record.data == base_record.data:
            merged.append(lane_record)
        elif lane_record.data in (base_record.data, candidate_record.data):
            merged.append(candidate_record)
        elif (
            data := merge_values(base_record.data, candidate_record.data, lane_record.data)
        ) is not None:
            merged.append(record_from_data(data))
        else:
            return None
    candidate_added = [record for record in candidate if record.identifier not in base_by_id]
    lane_added = [record for record in lane if record.identifier not in base_by_id]
    if {record.identifier for record in candidate_added} & {
        record.identifier for record in lane_added
    }:
        return None
    return [*merged, *candidate_added, *lane_added]


def merge_values(base: object, candidate: object, lane: object) -> object | None:
    """Merge recursively only where each side changes distinct semantic leaves."""
    if candidate == base:
        return lane
    if lane in (base, candidate):
        return candidate
    if not isinstance(base, dict) or not isinstance(candidate, dict) or not isinstance(lane, dict):
        return None
    base_data = cast("dict[str, object]", base)
    candidate_data = cast("dict[str, object]", candidate)
    lane_data = cast("dict[str, object]", lane)
    merged: dict[str, object] = {}
    for key in set(base_data) | set(candidate_data) | set(lane_data):
        if key not in base_data or key not in candidate_data or key not in lane_data:
            return None
        value = merge_values(base_data[key], candidate_data[key], lane_data[key])
        if value is None:
            return None
        merged[key] = value
    return merged


def record_from_data(data: object) -> LedgerRecord:
    """Render a field-merged record into canonical TOML owned by this resolver."""
    if not isinstance(data, dict):
        raise TypeError(_INVALID_RECORD_TABLE)
    record = cast("dict[str, object]", data)
    identifier, allowance = record.get("id"), record.get("allowance")
    if (
        not isinstance(identifier, str)
        or not isinstance(allowance, int)
        or isinstance(allowance, bool)
    ):
        raise TypeError(_INVALID_RECORD_IDENTITY)
    return LedgerRecord(identifier, render_record(record), allowance, record)


def render_record(data: dict[str, object]) -> str:
    """Render the narrow TOML record shape used by the source-budget ledger."""
    scalar_lines = [RECORD]
    nested: list[tuple[str, dict[str, object]]] = []
    for key, value in data.items():
        if isinstance(value, dict):
            nested.append((key, cast("dict[str, object]", value)))
        else:
            scalar_lines.append(f"{key} = {toml_value(value)}")
    blocks = ["\n".join(scalar_lines)]
    for key, values in nested:
        lines = [f"[quality.source_budget.debt.records.{key}]"]
        lines.extend(
            f"{child_key} = {toml_value(child_value)}" for child_key, child_value in values.items()
        )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def toml_value(value: object) -> str:
    """Render scalar TOML values admitted by the debt-record schema."""
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    message = f"unsupported source-budget record value: {value!r}"
    raise ValueError(message)


def next_section(text: str, start: int) -> int:
    """Find the next peer table, retaining nested tables owned by a record."""
    cursor = start + len(RECORD)
    while (next_table := text.find("\n[", cursor)) >= 0:
        header_end = text.find("\n", next_table + 1)
        header = text[next_table + 1 : len(text) if header_end < 0 else header_end]
        if header == RECORD or header.startswith(RECORD_CHILD_PREFIX):
            cursor = next_table + 1
            continue
        return next_table
    return len(text)


def split(text: str) -> list[str]:
    """Keep record bodies verbatim, including nested allowance category tables."""
    starts = [match.start() for match in re.finditer(re.escape(RECORD), text)]
    return [
        text[start:end].strip() for start, end in zip(starts, [*starts[1:], len(text)], strict=True)
    ]


def replace(candidate: str, records: list[LedgerRecord]) -> str:
    """Replace the record sequence and recompute its declared aggregate."""
    start = candidate.find(SECTION)
    record_start = candidate.find(RECORD, start)
    end = next_section(candidate, record_start)
    section = candidate[start:record_start]
    section, replacements = MAXIMUM_TOTAL.subn(
        f"maximum_total = {sum(item.allowance for item in records)}", section, count=1
    )
    if replacements != 1:
        raise ValueError(_MISSING_MAXIMUM_TOTAL)
    return (
        candidate[:start]
        + section.rstrip()
        + "\n\n"
        + "\n\n".join(item.block for item in records)
        + "\n\n"
        + candidate[end:].lstrip("\n")
    )
