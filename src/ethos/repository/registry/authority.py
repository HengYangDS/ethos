from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any
from typing import TypedDict

from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_list
from ethos.normalization.coercion import string_mapping

RELATION_TYPES = {"authority", "derived_view", "decision", "superseded_vocabulary"}


class AuthorityEntry(TypedDict):
    """Normalized authority-graph record consumed by validation."""

    id: str
    owner: str
    canonical_for: list[str]
    derived_from: list[str]
    supersedes: list[str]
    superseded_by: list[str]
    doc_refs: list[str]
    evidence_refs: list[str]
    stable_path: str
    relation_type: str


def _graph_path(root: Path) -> Path:
    return root / "docs" / "_meta" / "authority_graph.toml"


def _node_to_entry(node: dict[str, object]) -> AuthorityEntry:
    return {
        "id": str(node.get("id", "")),
        "owner": str(node.get("owner", "")),
        "canonical_for": string_list(node.get("canonical_for")),
        "derived_from": string_list(node.get("derived_from")),
        "supersedes": string_list(node.get("supersedes")),
        "superseded_by": [],
        "doc_refs": string_list(node.get("doc_refs")),
        "evidence_refs": string_list(node.get("evidence_refs")),
        "stable_path": str(node.get("stable_path", "")),
        "relation_type": str(node.get("relation_type", "")),
    }


def _list_field_gaps(node: dict[str, Any], entry_id: str) -> list[str]:
    gaps: list[str] = []
    gaps.extend(
        f"{entry_id or '<missing>'}:{field}_not_list"
        for field in ("canonical_for", "derived_from", "supersedes", "doc_refs", "evidence_refs")
        if field in node and not isinstance(node[field], list)
    )
    return gaps


def _is_evidence_ref(relative: str) -> bool:
    return relative.startswith("evidence/")


def _authority_graph_result(
    path: Path,
    repo: Path,
    entries: list[AuthorityEntry],
    gaps: list[str],
) -> dict[str, object]:
    return {
        "ok": not gaps,
        "path": path.relative_to(repo).as_posix(),
        "entries": entries,
        "required_gaps": gaps,
    }


def _validate_entry_definition(entry: AuthorityEntry, entry_id: str, gaps: list[str]) -> None:
    gaps.extend(
        f"{entry_id or '<missing>'}:{field}_missing"
        for field in ("id", "owner", "stable_path", "relation_type")
        if not entry[field]
    )
    if entry["relation_type"] and entry["relation_type"] not in RELATION_TYPES:
        gaps.append(f"{entry_id}:relation_type_invalid:{entry['relation_type']}")


def _validate_entry_paths(
    repo: Path, entry: AuthorityEntry, entry_id: str, gaps: list[str]
) -> None:
    stable_path = repo / entry["stable_path"]
    if entry["stable_path"] and not stable_path.exists():
        gaps.append(f"{entry_id}:stable_path_missing:{entry['stable_path']}")
    gaps.extend(
        f"{entry_id}:doc_ref_missing:{doc_ref}"
        for doc_ref in entry["doc_refs"]
        if not (repo / doc_ref).exists()
    )


def _validate_evidence_refs(
    repo: Path, entry: AuthorityEntry, entry_id: str, gaps: list[str]
) -> None:
    if not entry["evidence_refs"]:
        gaps.append(f"{entry_id}:evidence_refs_missing")
    for evidence_ref in entry["evidence_refs"]:
        if not _is_evidence_ref(evidence_ref):
            gaps.append(f"{entry_id}:evidence_ref_not_evidence:{evidence_ref}")
        elif not (repo / evidence_ref).exists():
            gaps.append(f"{entry_id}:evidence_ref_missing:{evidence_ref}")


def _validate_derived_references(
    entry: AuthorityEntry,
    entry_id: str,
    by_id: dict[str, AuthorityEntry],
    gaps: list[str],
) -> None:
    gaps.extend(
        f"{entry_id}:derived_from_missing:{source}"
        for source in entry["derived_from"]
        if source not in by_id
    )


def _project_supersession(
    entry: AuthorityEntry,
    entry_id: str,
    by_id: dict[str, AuthorityEntry],
    gaps: list[str],
) -> None:
    for superseded in entry["supersedes"]:
        if superseded not in by_id:
            gaps.append(f"{entry_id}:supersedes_missing:{superseded}")
            continue
        by_id[superseded]["superseded_by"].append(entry_id)


def _validate_derived_view(
    entry: AuthorityEntry,
    entry_id: str,
    authority_ids: set[str],
    gaps: list[str],
) -> None:
    if entry["relation_type"] != "derived_view":
        return
    derived_from = set(entry["derived_from"])
    if not derived_from & authority_ids:
        gaps.append(f"{entry_id}:derived_view_missing_authority_derivation")


def _validate_entry(
    repo: Path,
    node: dict[str, Any],
    entry: AuthorityEntry,
    by_id: dict[str, AuthorityEntry],
    authority_ids: set[str],
    gaps: list[str],
) -> None:
    entry_id = entry["id"]
    gaps.extend(_list_field_gaps(node, entry_id))
    _validate_entry_definition(entry, entry_id, gaps)
    _validate_entry_paths(repo, entry, entry_id, gaps)
    _validate_evidence_refs(repo, entry, entry_id, gaps)
    _validate_derived_references(entry, entry_id, by_id, gaps)
    _project_supersession(entry, entry_id, by_id, gaps)
    _validate_derived_view(entry, entry_id, authority_ids, gaps)


def _validate_entries(
    repo: Path,
    raw_nodes: list[dict[str, Any]],
    entries: list[AuthorityEntry],
    by_id: dict[str, AuthorityEntry],
) -> list[str]:
    gaps: list[str] = []
    if len(by_id) != len(entries):
        gaps.append("authority_graph_duplicate_ids")
    authority_ids = {
        entry_id for entry_id, entry in by_id.items() if entry["relation_type"] == "authority"
    }
    for node, entry in zip(raw_nodes, entries, strict=False):
        _validate_entry(repo, node, entry, by_id, authority_ids, gaps)
    return gaps


def _sort_supersession_projections(entries: list[AuthorityEntry]) -> None:
    for entry in entries:
        entry["superseded_by"].sort()


def authority_graph_report(root: Path | None = None) -> dict[str, object]:
    repo = root or Path.cwd()
    path = _graph_path(repo)
    if not path.exists():
        return _authority_graph_result(path, repo, [], ["authority_graph_missing"])
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return _authority_graph_result(path, repo, [], [f"authority_graph_invalid_toml:{exc}"])

    raw_nodes = [string_mapping(node) for node in object_sequence(payload.get("node"))]
    entries = [_node_to_entry(node) for node in raw_nodes]
    by_id = {entry["id"]: entry for entry in entries}
    gaps = _validate_entries(repo, raw_nodes, entries, by_id)
    _sort_supersession_projections(entries)
    return _authority_graph_result(path, repo, entries, gaps)
