"""Decision Record grammar, relationship, and index validation."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ethos.contracts.plan import dependency_cycle
from ethos.repository.registry.docs.links import markdown_links

_SECTIONS = (
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
_FIELDS = (
    "Decision ID",
    "Status",
    "Decision Date",
    "Decision Change Date",
    "Supersedes",
    "Superseded By",
    "Depends On",
)
_ALTERNATIVES = "| Option | Verdict | Pros | Cons | Decision basis |"
_FILE = re.compile(r"^DR-[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
_ID = re.compile(r"^DR-[0-9]{4}$")
_STATUSES = frozenset({"proposed", "accepted", "superseded", "retired"})


def _references(value: str) -> tuple[str, ...]:
    if value.strip().casefold() in {"", "none"}:
        return ()
    return tuple(part.strip().split(" ", 1)[0] for part in value.split(",") if part.strip())


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    path: str
    status: str
    changed: date
    supersedes: tuple[str, ...]
    superseded_by: str | None
    depends_on: tuple[str, ...]


class DecisionRegistry:
    """The sole parser, validator, and index owner for Decision Records."""

    def __init__(self, root: Path, directory: Path) -> None:
        self.root = root
        self.directory = directory
        self.records: list[DecisionRecord] = []

    def validate(self) -> list[str]:
        gaps = [
            f"decision_record_not_flat:{path.relative_to(self.root).as_posix()}"
            for path in sorted(self.directory.rglob("DR-*.md"))
            if path.parent != self.directory
        ]
        for path in sorted(self.directory.glob("DR-*.md")):
            record, record_gaps = self._parse(path)
            gaps.extend(record_gaps)
            if record:
                self.records.append(record)
        grouped: dict[str, list[str]] = {}
        for record in self.records:
            grouped.setdefault(record.decision_id, []).append(record.path)
        duplicates = [
            f"decision_record_id_duplicate:{decision_id}:{','.join(sorted(paths))}"
            for decision_id, paths in sorted(grouped.items())
            if len(paths) > 1
        ]
        return [*gaps, *duplicates] if duplicates else [*gaps, *self._relations(), *self._index()]

    def _parse(self, path: Path) -> tuple[DecisionRecord | None, list[str]]:
        relative = path.relative_to(self.root).as_posix()
        if not _FILE.fullmatch(path.name):
            return None, [f"decision_record_name_invalid:{relative}"]
        text = path.read_text(encoding="utf-8")
        sections = set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))
        try:
            table = text.split("## Record", 1)[1].split("## ", 1)[0]
        except IndexError:
            table = ""
        rows = (
            [cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in table.splitlines()
        )
        fields = {
            cells[0]: cells[1]
            for cells in rows
            if len(cells) == 2 and cells[0] not in {"Field", "---"}
        }
        missing_sections = [section for section in _SECTIONS if section not in sections]
        missing_fields = [field for field in _FIELDS if not fields.get(field)]
        decision_id, status = (fields.get(name, "") for name in ("Decision ID", "Status"))
        successor = _references(fields.get("Superseded By", ""))
        gaps = []

        def fail(condition: object, kind: str, detail: str = "") -> None:
            if condition:
                gaps.append(f"decision_record_{kind}:{relative}{f':{detail}' if detail else ''}")

        fail(missing_sections, "sections_missing", ",".join(missing_sections))
        fail(missing_fields, "fields_missing", ",".join(missing_fields))
        fail(
            "Alternatives Considered" in sections and _ALTERNATIVES not in text,
            "alternatives_invalid",
        )
        fail(
            decision_id and not path.name.startswith(f"{decision_id}-"),
            "identity_mismatch",
            decision_id,
        )
        fail(decision_id and not _ID.fullmatch(decision_id), "id_invalid", decision_id)
        fail(status and status not in _STATUSES, "status_invalid", status)
        fail(status == "superseded" and len(successor) != 1, "successor_required")
        fail(status and status != "superseded" and successor, "successor_forbidden")
        for field in ("Supersedes", "Superseded By", "Depends On"):
            invalid = sorted(
                ref for ref in _references(fields.get(field, "")) if not _ID.fullmatch(ref)
            )
            if invalid:
                gaps.append(f"decision_record_reference_invalid:{relative}:{field}:{','.join(invalid)}")
        if missing_fields:
            return None, gaps
        try:
            changed = date.fromisoformat(fields["Decision Change Date"])
        except ValueError:
            return None, [*gaps, f"decision_record_change_date_invalid:{relative}"]
        if not _ID.fullmatch(decision_id) or status not in _STATUSES or len(successor) > 1:
            return None, gaps
        return DecisionRecord(
            decision_id,
            relative,
            status,
            changed,
            _references(fields["Supersedes"]),
            successor[0] if successor else None,
            _references(fields["Depends On"]),
        ), gaps

    def _relations(self) -> list[str]:
        by_id = {record.decision_id: record for record in self.records}
        gaps = []
        for record in self.records:
            references = (
                ("Supersedes", record.supersedes),
                ("Superseded By", (record.superseded_by,) if record.superseded_by else ()),
                ("Depends On", record.depends_on),
            )
            gaps.extend(
                f"decision_record_reference_missing:{record.decision_id}:{field}:{target}"
                for field, targets in references
                for target in targets
                if target not in by_id
            )
            supersessions = [(predecessor, record.decision_id) for predecessor in record.supersedes]
            if record.superseded_by:
                supersessions.append((record.decision_id, record.superseded_by))
            for predecessor_id, successor_id in supersessions:
                predecessor, successor = by_id.get(predecessor_id), by_id.get(successor_id)
                if predecessor and successor and (
                    predecessor.superseded_by != successor_id
                    or predecessor_id not in successor.supersedes
                ):
                    gaps.append(
                        "decision_record_supersession_not_reciprocal:"
                        f"{predecessor_id}:{successor_id}"
                    )
        cycle = dependency_cycle(
            {
                record_id: tuple(target for target in record.depends_on if target in by_id)
                for record_id, record in by_id.items()
            }
        )
        if cycle:
            gaps.append(f"decision_record_dependency_cycle:{','.join(cycle)}")
        return sorted(set(gaps))

    def _index(self) -> list[str]:
        if not self.records:
            return []
        index = self.directory / "decision-index.md"
        relative = index.relative_to(self.root).as_posix()
        if not index.is_file():
            return [f"decision_index_missing:{relative}"]
        actual = [
            "-".join(Path(target.partition("#")[0]).name.split("-", 2)[:2])
            for _line, target in markdown_links(index)
            if _FILE.fullmatch(target.partition("#")[0])
        ]
        expected_ids = {record.decision_id for record in self.records}
        counts = Counter(actual)
        missing = sorted(expected_ids - counts.keys())
        duplicate = sorted(record_id for record_id, count in counts.items() if count > 1)
        unknown = sorted(counts.keys() - expected_ids)
        if missing or duplicate or unknown:
            return [
                (
                    f"decision_index_coverage_invalid:{relative}:missing={','.join(missing)}:"
                    f"duplicate={','.join(duplicate)}:unknown={','.join(unknown)}"
                )
            ]
        expected = [
            record.decision_id
            for record in sorted(
                self.records,
                key=lambda record: (
                    record.status not in {"accepted", "proposed"},
                    -record.changed.toordinal(),
                    record.decision_id,
                ),
            )
        ]
        if actual == expected:
            return []
        return [f"decision_index_order_invalid:{relative}:{','.join(expected)}"]


def decision_record_gaps(root: Path, docs: Path) -> list[str]:
    """Validate Decision Records through the one registry owner."""
    directory = docs / "decisions"
    return DecisionRegistry(root, directory).validate() if directory.is_dir() else []
