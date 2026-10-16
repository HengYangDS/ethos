"""Deterministic repairs for repository paradigm gaps.

A repair follows from a gap's obligation and its carrier's current text alone. Gaps
that need judgment, and carriers a repair cannot change without guessing, stay
report-only with the report's canonical repair.
"""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import tomli_w

from ethos.contracts.branch.roles import ROLE_NAME_FIELDS
from ethos.contracts.branch.roles import SIBLING_WORKTREE_FIELD
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.openspec import common_rules_repair
from ethos.repository.paradigm.openspec import schema_repair

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm
    from ethos.repository.paradigm.gap import ParadigmGap

_TABLE = re.compile(r"\s*\[\s*([^\[\]]+?)\s*\]\s*(?:#.*)?")
_PEERS = re.compile(r"\s*\[\[\s*publication\.peers\s*\]\]\s*(?:#.*)?")
_PEER_KEY = "publication.peers."
_STANDARD_ROLES = BranchRolePolicy()
_UNFIXED = object()
# Fields no reader consults any more, so every value they hold can go.
_RETIRED_FIELDS = frozenset({("branch_roles", SIBLING_WORKTREE_FIELD)})

Repair = tuple[str, str]


class CarrierEdit(NamedTuple):
    """One carrier's current text, absent when the carrier does not exist, and its repair."""

    path: str
    before: str | None
    after: str


class RepairPlan(NamedTuple):
    """The carrier edits, follow-up commands and report-only gaps derived from one report."""

    edits: tuple[CarrierEdit, ...]
    repaired: tuple[ParadigmGap, ...]
    actions: tuple[str, ...]
    report_only: tuple[ParadigmGap, ...]


def paradigm_repair_plan(root: Path, gaps: Iterable[ParadigmGap]) -> RepairPlan:
    """Derive every deterministic repair for the gaps, composing edits to one carrier."""
    paradigm = load_repository_paradigm()
    original: dict[str, str | None] = {}
    working: dict[str, str | None] = {}
    unreadable: set[str] = set()
    repaired: list[ParadigmGap] = []
    actions: list[str] = []
    report_only: list[ParadigmGap] = []
    for gap in gaps:
        handler = _HANDLERS.get(gap.obligation)
        path = gap.carrier.partition(":")[0]
        if handler is not None and path not in original and path not in unreadable:
            try:
                original[path] = working[path] = _read(root, path)
            except (OSError, UnicodeError):
                unreadable.add(path)
        repair = (
            handler(paradigm, gap, working[path])
            if handler is not None and path not in unreadable
            else None
        )
        if repair is None:
            report_only.append(gap)
            continue
        working[path], action = repair
        repaired.append(gap)
        if action:
            actions.append(action)
    edits = tuple(
        CarrierEdit(path, original[path], text)
        for path, text in working.items()
        if text is not None and text != original[path]
    )
    return RepairPlan(edits, tuple(repaired), tuple(actions), tuple(report_only))


def _read(root: Path, path: str) -> str | None:
    """Read a carrier as UTF-8 text; only a missing file reads as absent."""
    try:
        return (root / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _normalization(paradigm: RepositoryParadigm, gap: ParadigmGap, text: str | None) -> Repair:
    """Make the shared rule the last catch-all pattern and the shared defaults apply to [*]."""
    if gap.carrier == ".gitattributes":
        body = (text or "").rstrip("\n")
        rule = paradigm.normalization.gitattributes
        return (f"{body}\n{rule}\n" if body else f"{rule}\n"), ""
    return _editorconfig(text, paradigm.normalization.editorconfig.model_dump()), ""


def _editorconfig(text: str | None, expected: dict[str, str]) -> str:
    """Set the defaults in the last [*] section, or add one ahead of narrower sections."""
    settings = [f"{key} = {value}" for key, value in expected.items()]
    if text is None or not text.strip():
        return "\n".join(["root = true", "", "[*]", *settings]) + "\n"
    lines = text.rstrip("\n").split("\n")
    headers = [index for index, line in enumerate(lines) if _section(line) is not None]
    sections = [index for index in headers if _section(lines[index]) == "*"]
    if not sections:
        if headers:
            lines[headers[0] : headers[0]] = ["[*]", *settings, ""]
        else:
            lines.extend(["", "[*]", *settings])
        return "\n".join(lines) + "\n"
    start = sections[-1]
    end = next((index for index in headers if index > start), len(lines))
    position = end
    while position > start + 1 and not lines[position - 1].strip():
        position -= 1
    for key, value in expected.items():
        found = next(
            (
                index
                for index in range(start + 1, end)
                if lines[index].partition("=")[0].strip().lower() == key
            ),
            None,
        )
        if found is None:
            lines.insert(position, f"{key} = {value}")
            end += 1
            position += 1
        else:
            lines[found] = f"{key} = {value}"
    return "\n".join(lines) + "\n"


def _section(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip()
    return None


def _formatter(paradigm: RepositoryParadigm, gap: ParadigmGap, text: str | None) -> Repair | None:
    """Create a missing formatter carrier, or set the one setting the report names."""
    path, _, key = gap.carrier.partition(":")
    if not path.endswith(".toml"):
        return None
    carriers = {tool.id: tool.carrier for tool in paradigm.tool}
    settings = next(
        (
            dict(formatter.settings)
            for formatter in paradigm.formatter
            if carriers[formatter.tool] == path
        ),
        None,
    )
    if settings is None:
        return None
    if text is None:
        return tomli_w.dumps(_nested(settings)), ""
    repaired: str | None = text
    for name, value in settings.items():
        if repaired is not None and (not key or name == key):
            repaired = _set_toml_value(repaired, name, value)
    if repaired is None:
        return None
    return repaired, f"git add {path}" if repaired == text else ""


def _nested(settings: Mapping[str, object]) -> dict[str, Any]:
    """Turn dotted setting names into the TOML tables that carry them."""
    nested: dict[str, Any] = {}
    for key, value in settings.items():
        *tables, leaf = key.split(".")
        target = nested
        for table in tables:
            target = target.setdefault(table, {})
        target[leaf] = value
    return nested


def _set_toml_value(text: str, key: str, value: object) -> str | None:
    """Set one dotted TOML key in place, keeping comments and every other line."""
    *tables, leaf = key.split(".")
    table = ".".join(tables)
    line = tomli_w.dumps({leaf: value}).rstrip("\n")
    lines = text.rstrip("\n").split("\n")
    headers = [index for index, current in enumerate(lines) if current.lstrip().startswith("[")]
    start = 0
    if table:
        found_table = next((index for index in headers if _table(lines[index]) == table), None)
        if found_table is None:
            lines.extend(["", f"[{table}]", line])
            return _verified("\n".join(lines) + "\n")
        start = found_table + 1
    end = next((index for index in headers if index >= start), len(lines))
    found = next((index for index in range(start, end) if _key(lines[index]) == leaf), None)
    if found is not None:
        lines[found] = line
    else:
        position = end
        while position > start and not lines[position - 1].strip():
            position -= 1
        lines.insert(position, line)
    return _verified("\n".join(lines) + "\n")


def _table(line: str) -> str | None:
    match = _TABLE.fullmatch(line)
    return match.group(1) if match else None


def _key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "[")) or "=" not in stripped:
        return None
    return stripped.partition("=")[0].strip().strip("\"'")


def _verified(text: str) -> str | None:
    """Keep a repaired document only when it still parses as TOML."""
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    return text


def _front_matter(
    _paradigm: RepositoryParadigm, _gap: ParadigmGap, text: str | None
) -> Repair | None:
    """Remove the <!-- and --> lines that wrap a document's leading YAML front matter."""
    lines = (text or "").split("\n")
    if lines[:2] != ["<!--", "---"]:
        return None
    closing = next((index for index in range(2, len(lines)) if lines[index] == "---"), None)
    if closing is None or lines[closing + 1 : closing + 2] != ["-->"]:
        return None
    return "\n".join([*lines[1 : closing + 1], *lines[closing + 2 :]]), ""


def _peer_remote(
    _paradigm: RepositoryParadigm, gap: ParadigmGap, text: str | None
) -> Repair | None:
    """Name one peer's Git remote after the peer and name the matching local rename."""
    identity = gap.carrier.partition(":")[2].removeprefix(_PEER_KEY)
    lines = (text or "").rstrip("\n").split("\n")
    for start in (index for index, line in enumerate(lines) if _PEERS.fullmatch(line)):
        end = next(
            (
                index
                for index in range(start + 1, len(lines))
                if lines[index].lstrip().startswith("[")
            ),
            len(lines),
        )
        try:
            peer = tomllib.loads("\n".join(lines[start + 1 : end]))
        except tomllib.TOMLDecodeError:
            return None
        if peer.get("id") != identity:
            continue
        line = tomli_w.dumps({"git_remote": identity}).rstrip("\n")
        keys = {_key(lines[index]): index for index in range(start + 1, end)}
        if "git_remote" in keys:
            lines[keys["git_remote"]] = line
        else:
            lines.insert(keys["id"] + 1, line)
        previous = peer.get("git_remote")
        action = (
            f"git remote rename {previous} {identity}"
            if isinstance(previous, str) and previous and previous != identity
            else ""
        )
        return "\n".join(lines) + "\n", action
    return None


def _restated_field(
    paradigm: RepositoryParadigm, gap: ParadigmGap, text: str | None
) -> Repair | None:
    """Delete a workspace field that restates the value the paradigm fixes, or that is retired.

    Any other value needs judgment; a legacy branch name in particular stays until
    closeout has renamed its ref.
    """
    table, _, name = gap.carrier.partition(":")[2].partition(".")
    try:
        declared = tomllib.loads(text or "")
    except tomllib.TOMLDecodeError:
        return None
    section = declared.get(table)
    if not isinstance(section, dict) or name not in section:
        return None
    if (table, name) not in _RETIRED_FIELDS and section[name] != _fixed(paradigm, table, name):
        return None
    lines = (text or "").rstrip("\n").split("\n")
    start = next((index for index, line in enumerate(lines) if _table(line) == table), len(lines))
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith("[")),
        len(lines),
    )
    found = [index for index in range(start + 1, end) if _key(lines[index]) == name]
    # Only a field on exactly one line of its own table is deleted. Any other shape leaves
    # the text as it was, which the comparison below refuses.
    repaired = "\n".join(line for index, line in enumerate(lines) if found != [index]) + "\n"
    expected = {**declared, table: {key: value for key, value in section.items() if key != name}}
    try:
        exact = tomllib.loads(repaired) == expected
    except tomllib.TOMLDecodeError:
        return None
    return (repaired, "") if exact else None


def _fixed(paradigm: RepositoryParadigm, table: str, name: str) -> object:
    """Return the value the paradigm fixes for one workspace field, or one nothing equals."""
    if table == "branch_roles" and name in ROLE_NAME_FIELDS:
        return getattr(_STANDARD_ROLES, name)
    if (table, name) == ("commit_policy", "subject_pattern"):
        return paradigm.commit.subject_pattern()
    return _UNFIXED


_HANDLERS: dict[str, Callable[[RepositoryParadigm, ParadigmGap, str | None], Repair | None]] = {
    "text-normalization": _normalization,
    "formatter-binding": _formatter,
    "formatter-setting": _formatter,
    "front-matter": _front_matter,
    "peer-remote": _peer_remote,
    "branch-roles": _restated_field,
    "commit-grammar": _restated_field,
    "openspec-schema": schema_repair,
    "openspec-rules": common_rules_repair,
}
