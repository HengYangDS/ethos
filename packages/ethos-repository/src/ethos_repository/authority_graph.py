from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

RELATION_TYPES = {"authority", "derived_view", "decision", "superseded_vocabulary"}


def _graph_path(root: Path) -> Path:
    return root / "docs" / "_meta" / "authority_graph.toml"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _node_to_entry(node: dict[str, Any]) -> dict[str, object]:
    return {
        "id": str(node.get("id", "")),
        "owner": str(node.get("owner", "")),
        "canonical_for": _string_list(node.get("canonical_for")),
        "derived_from": _string_list(node.get("derived_from")),
        "supersedes": _string_list(node.get("supersedes")),
        "superseded_by": [],
        "doc_refs": _string_list(node.get("doc_refs")),
        "evidence_refs": _string_list(node.get("evidence_refs")),
        "stable_path": str(node.get("stable_path", "")),
        "relation_type": str(node.get("relation_type", "")),
    }


def _list_field_gaps(node: dict[str, Any], entry_id: str) -> list[str]:
    gaps: list[str] = []
    for field in ("canonical_for", "derived_from", "supersedes", "doc_refs", "evidence_refs"):
        if field in node and not isinstance(node[field], list):
            gaps.append(f"{entry_id or '<missing>'}:{field}_not_list")
    return gaps


def _is_evidence_ref(relative: str) -> bool:
    return relative.startswith(("docs/evidence/", "claims/"))


def authority_graph_report(root: Path | None = None) -> dict[str, object]:
    repo = root or Path.cwd()
    path = _graph_path(repo)
    if not path.exists():
        return {
            "ok": False,
            "path": path.relative_to(repo).as_posix(),
            "entries": [],
            "required_gaps": ["authority_graph_missing"],
        }
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "ok": False,
            "path": path.relative_to(repo).as_posix(),
            "entries": [],
            "required_gaps": [f"authority_graph_invalid_toml:{exc}"],
        }

    raw_nodes = payload.get("node", [])
    entries = [_node_to_entry(node) for node in raw_nodes]
    by_id = {str(entry["id"]): entry for entry in entries}
    gaps: list[str] = []
    if len(by_id) != len(entries):
        gaps.append("authority_graph_duplicate_ids")
    for node, entry in zip(raw_nodes, entries, strict=False):
        entry_id = str(entry["id"])
        gaps.extend(_list_field_gaps(node, entry_id))
        for field in ("id", "owner", "stable_path", "relation_type"):
            if not entry[field]:
                gaps.append(f"{entry_id or '<missing>'}:{field}_missing")
        if entry["relation_type"] and entry["relation_type"] not in RELATION_TYPES:
            gaps.append(f"{entry_id}:relation_type_invalid:{entry['relation_type']}")
        stable_path = repo / str(entry["stable_path"])
        if entry["stable_path"] and not stable_path.exists():
            gaps.append(f"{entry_id}:stable_path_missing:{entry['stable_path']}")
        for doc_ref in entry["doc_refs"]:
            doc_path = repo / str(doc_ref)
            if not doc_path.exists():
                gaps.append(f"{entry_id}:doc_ref_missing:{doc_ref}")
        if not entry["evidence_refs"]:
            gaps.append(f"{entry_id}:evidence_refs_missing")
        for evidence_ref in entry["evidence_refs"]:
            evidence_path = repo / str(evidence_ref)
            if not _is_evidence_ref(str(evidence_ref)):
                gaps.append(f"{entry_id}:evidence_ref_not_evidence:{evidence_ref}")
            elif not evidence_path.exists():
                gaps.append(f"{entry_id}:evidence_ref_missing:{evidence_ref}")
        for source in entry["derived_from"]:
            if source not in by_id:
                gaps.append(f"{entry_id}:derived_from_missing:{source}")
        for superseded in entry["supersedes"]:
            if superseded not in by_id:
                gaps.append(f"{entry_id}:supersedes_missing:{superseded}")
                continue
            superseded_by = by_id[superseded]["superseded_by"]
            assert isinstance(superseded_by, list)
            superseded_by.append(entry_id)
        if entry["relation_type"] == "derived_view":
            derived_from = {str(source) for source in entry["derived_from"]}
            authority_sources = {
                str(source_id)
                for source_id, source in by_id.items()
                if source["relation_type"] == "authority"
            }
            if not derived_from & authority_sources:
                gaps.append(f"{entry_id}:derived_view_missing_authority_derivation")

    for entry in entries:
        superseded_by = entry["superseded_by"]
        assert isinstance(superseded_by, list)
        superseded_by.sort()

    return {
        "ok": not gaps,
        "path": path.relative_to(repo).as_posix(),
        "entries": entries,
        "required_gaps": gaps,
    }
