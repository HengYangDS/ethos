"""Decision Record grammar and newest-current index checks."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ethos.contracts.plan import dependency_cycle
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
_DECISION_FILE = re.compile(r"^DR-[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
_DECISION_ID = re.compile(r"^DR-[0-9]{4}$")
_DECISION_STATUSES = frozenset({"proposed", "accepted", "superseded", "retired"})
_RECORD_FIELD_COUNT = 2


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """One parsed durable ruling used only for registry validation."""

    decision_id: str
    path: str
    status: str
    changed: date
    supersedes: tuple[str, ...]
    superseded_by: str | None
    depends_on: tuple[str, ...]


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
    identity_gaps = _identity_gaps(records)
    gaps.extend(identity_gaps)
    if not identity_gaps:
        gaps.extend(_relationship_gaps(records))
        gaps.extend(_index_gaps(root, decisions / "decision-index.md", records))
    return gaps


def _decision_record(root: Path, path: Path) -> tuple[DecisionRecord | None, list[str]]:
    relative = path.relative_to(root).as_posix()
    if not _DECISION_FILE.fullmatch(path.name):
        return None, [f"decision_record_name_invalid:{relative}"]
    text = path.read_text(encoding="utf-8")
    sections = set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))
    fields = _record_fields(text)
    gaps = _section_gaps(relative, sections)
    gaps.extend(_field_gaps(relative, fields))
    if "Alternatives Considered" in sections and _ALTERNATIVE_HEADER not in text:
        gaps.append(f"decision_record_alternatives_invalid:{relative}")
    gaps.extend(_identity_and_lifecycle_gaps(relative, path, fields))
    gaps.extend(_reference_format_gaps(relative, fields))
    if (
        all(fields.get(field) for field in _required_fields())
        and _decision_date(fields["Decision Change Date"]) is None
    ):
        gaps.append(f"decision_record_change_date_invalid:{relative}")
    return _parsed_record(relative, fields), gaps


def _required_fields() -> tuple[str, ...]:
    return (
        "Decision ID",
        "Status",
        "Decision Date",
        "Decision Change Date",
        "Supersedes",
        "Superseded By",
        "Depends On",
    )


def _section_gaps(relative: str, sections: set[str]) -> list[str]:
    missing = [section for section in _REQUIRED_SECTIONS if section not in sections]
    if not missing:
        return []
    return [f"decision_record_sections_missing:{relative}:{','.join(missing)}"]


def _field_gaps(relative: str, fields: dict[str, str]) -> list[str]:
    absent = [field for field in _required_fields() if not fields.get(field)]
    if not absent:
        return []
    return [f"decision_record_fields_missing:{relative}:{','.join(absent)}"]


def _identity_and_lifecycle_gaps(
    relative: str,
    path: Path,
    fields: dict[str, str],
) -> list[str]:
    decision_id = fields.get("Decision ID", "")
    status = fields.get("Status", "")
    successor = _decision_references(fields.get("Superseded By", ""))
    gaps: list[str] = []
    if decision_id and not path.name.startswith(f"{decision_id}-"):
        gaps.append(f"decision_record_identity_mismatch:{relative}:{decision_id}")
    if decision_id and not _DECISION_ID.fullmatch(decision_id):
        gaps.append(f"decision_record_id_invalid:{relative}:{decision_id}")
    if status and status not in _DECISION_STATUSES:
        gaps.append(f"decision_record_status_invalid:{relative}:{status}")
    if status == "superseded" and len(successor) != 1:
        gaps.append(f"decision_record_successor_required:{relative}")
    if status and status != "superseded" and successor:
        gaps.append(f"decision_record_successor_forbidden:{relative}")
    return gaps


def _reference_format_gaps(relative: str, fields: dict[str, str]) -> list[str]:
    gaps: list[str] = []
    for field in ("Supersedes", "Superseded By", "Depends On"):
        references = _decision_references(fields.get(field, ""))
        invalid = sorted(
            reference for reference in references if not _DECISION_ID.fullmatch(reference)
        )
        if invalid:
            gaps.append(f"decision_record_reference_invalid:{relative}:{field}:{','.join(invalid)}")
    return gaps


def _parsed_record(relative: str, fields: dict[str, str]) -> DecisionRecord | None:
    if any(not fields.get(field) for field in _required_fields()):
        return None
    decision_id = fields["Decision ID"]
    status = fields["Status"]
    changed = _decision_date(fields["Decision Change Date"])
    successor = _decision_references(fields["Superseded By"])
    if (
        changed is None
        or not _DECISION_ID.fullmatch(decision_id)
        or status not in _DECISION_STATUSES
        or len(successor) > 1
    ):
        return None
    return DecisionRecord(
        decision_id=decision_id,
        path=relative,
        status=status,
        changed=changed,
        supersedes=_decision_references(fields["Supersedes"]),
        superseded_by=successor[0] if successor else None,
        depends_on=_decision_references(fields["Depends On"]),
    )


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


def _decision_references(value: str) -> tuple[str, ...]:
    if value.strip().casefold() in {"", "none"}:
        return ()
    return tuple(part.strip().split(" ", 1)[0] for part in value.split(",") if part.strip())


def _identity_gaps(records: list[DecisionRecord]) -> list[str]:
    paths: dict[str, list[str]] = {}
    for record in records:
        paths.setdefault(record.decision_id, []).append(record.path)
    return [
        f"decision_record_id_duplicate:{decision_id}:{','.join(sorted(record_paths))}"
        for decision_id, record_paths in sorted(paths.items())
        if len(record_paths) > 1
    ]


def _relationship_gaps(records: list[DecisionRecord]) -> list[str]:
    by_id = {record.decision_id: record for record in records}
    gaps: list[str] = []
    for record in records:
        references = (
            ("Supersedes", record.supersedes),
            ("Superseded By", (record.superseded_by,) if record.superseded_by else ()),
            ("Depends On", record.depends_on),
        )
        for field, targets in references:
            gaps.extend(
                f"decision_record_reference_missing:{record.decision_id}:{field}:{target}"
                for target in targets
                if target not in by_id
            )
        if record.superseded_by in by_id:
            successor = by_id[record.superseded_by]
            if record.decision_id not in successor.supersedes:
                gaps.append(
                    "decision_record_supersession_not_reciprocal:"
                    f"{record.decision_id}:{successor.decision_id}"
                )
        for predecessor_id in record.supersedes:
            predecessor = by_id.get(predecessor_id)
            if predecessor is not None and predecessor.superseded_by != record.decision_id:
                gaps.append(
                    "decision_record_supersession_not_reciprocal:"
                    f"{predecessor_id}:{record.decision_id}"
                )
    cycle = _dependency_cycle(by_id)
    if cycle:
        gaps.append(f"decision_record_dependency_cycle:{','.join(cycle)}")
    return sorted(set(gaps))


def _dependency_cycle(records: dict[str, DecisionRecord]) -> tuple[str, ...]:
    graph = {
        decision_id: tuple(target for target in record.depends_on if target in records)
        for decision_id, record in records.items()
    }
    return dependency_cycle(graph)


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
    actual_ids = ["-".join(Path(target).name.split("-", 2)[:2]) for target in linked]
    expected_id_set = {record.decision_id for record in records}
    counts = Counter(actual_ids)
    missing = sorted(expected_id_set - counts.keys())
    duplicate = sorted(decision_id for decision_id, count in counts.items() if count > 1)
    unknown = sorted(counts.keys() - expected_id_set)
    relative = index.relative_to(root).as_posix()
    if missing or duplicate or unknown:
        return [
            (
                f"decision_index_coverage_invalid:{relative}:"
                f"missing={','.join(missing)}:duplicate={','.join(duplicate)}:"
                f"unknown={','.join(unknown)}"
            )
        ]
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
    return [f"decision_index_order_invalid:{relative}:{','.join(expected_ids)}"]
