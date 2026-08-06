"""Decision Record grammar and newest-current index checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ethos.repository.registry.docs.links import markdown_links

_REQUIRED_SECTIONS = (
    "Record",
    "Context",
    "Invariants",
    "Alternatives Considered",
    "Decision",
    "Consequences",
    "Proof Or Evidence",
    "Revisit Trigger",
    "Decision Change Ledger",
)
_ALTERNATIVE_HEADER = "| Option | Verdict | Pros | Cons | Decision basis |"
_DECISION_FILE = re.compile(r"^DR-[0-9]{4}-.+\.md$")
_RECORD_FIELD_COUNT = 2


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """One parsed durable ruling used only for registry validation."""

    decision_id: str
    path: str
    status: str
    changed: date


def decision_record_gaps(root: Path, docs: Path) -> list[str]:
    """Validate flat records and the one newest-current-first index."""
    decisions = docs / "decisions"
    if not decisions.is_dir():
        return []
    nested = sorted(
        path.relative_to(root).as_posix()
        for path in decisions.rglob("DR-*.md")
        if path.parent != decisions
    )
    gaps = [f"decision_record_not_flat:{path}" for path in nested]
    records: list[DecisionRecord] = []
    for path in sorted(decisions.glob("DR-*.md")):
        record, record_gaps = _decision_record(root, path)
        gaps.extend(record_gaps)
        if record is not None:
            records.append(record)
    gaps.extend(_index_gaps(root, decisions / "decision-index.md", records))
    return gaps


def _decision_record(root: Path, path: Path) -> tuple[DecisionRecord | None, list[str]]:
    relative = path.relative_to(root).as_posix()
    if not _DECISION_FILE.fullmatch(path.name):
        return None, [f"decision_record_name_invalid:{relative}"]
    text = path.read_text(encoding="utf-8")
    sections = set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))
    missing = [section for section in _REQUIRED_SECTIONS if section not in sections]
    gaps = [f"decision_record_sections_missing:{relative}:{','.join(missing)}"] if missing else []
    record = _record_fields(text)
    required = ("Decision ID", "Status", "Decision Date", "Decision Change Date")
    absent = [field for field in required if not record.get(field)]
    if absent:
        gaps.append(f"decision_record_fields_missing:{relative}:{','.join(absent)}")
    if "Alternatives Considered" in sections and _ALTERNATIVE_HEADER not in text:
        gaps.append(f"decision_record_alternatives_invalid:{relative}")
    decision_id = record.get("Decision ID", "")
    if decision_id and not path.name.startswith(f"{decision_id}-"):
        gaps.append(f"decision_record_identity_mismatch:{relative}:{decision_id}")
    changed = _decision_date(record.get("Decision Change Date", ""))
    if not absent and changed is None:
        gaps.append(f"decision_record_change_date_invalid:{relative}")
    parsed = None
    if not absent and changed is not None:
        parsed = DecisionRecord(
            decision_id=decision_id,
            path=relative,
            status=record["Status"],
            changed=changed,
        )
    return parsed, gaps


def _decision_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _record_fields(text: str) -> dict[str, str]:
    try:
        table = text.split("## Record", 1)[1].split("## ", 1)[0]
    except IndexError:
        return {}
    fields: dict[str, str] = {}
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == _RECORD_FIELD_COUNT and cells[0] not in {"Field", "---"}:
            fields[cells[0]] = cells[1]
    return fields


def _index_gaps(root: Path, index: Path, records: list[DecisionRecord]) -> list[str]:
    if not records:
        return []
    if not index.is_file():
        return [f"decision_index_missing:{index.relative_to(root).as_posix()}"]
    linked = [
        target.partition("#")[0]
        for _line, target in markdown_links(index)
        if _DECISION_FILE.fullmatch(target.partition("#")[0])
    ]
    linked_ids = [Path(target).name.split("-", 2)[:2] for target in linked]
    actual_ids = ["-".join(parts) for parts in linked_ids]
    expected = sorted(
        records,
        key=lambda record: (
            record.status not in {"accepted", "proposed"},
            -record.changed.toordinal(),
            record.decision_id,
        ),
    )
    expected_ids = [record.decision_id for record in expected]
    if actual_ids == expected_ids:
        return []
    relative = index.relative_to(root).as_posix()
    return [f"decision_index_order_invalid:{relative}:{','.join(expected_ids)}"]
