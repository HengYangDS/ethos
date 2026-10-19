"""Derive exact reference-preserving archive bytes from trusted Git source."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from pathlib import PurePosixPath
from subprocess import TimeoutExpired
from typing import TYPE_CHECKING

from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.lifecycle.archive_binding import archived_change_from_path
from ethos.adapters.openspec.selection import requested_change
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.verdict import report_verdict
from ethos.repository.openspec.identifiers import TEMPORAL_SUFFIX_PATTERN
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from collections.abc import Mapping

type TreeEntries = dict[str, tuple[str, str, str]]


def relocate_documents(
    root: Path,
    *,
    documents: Mapping[str, str],
    files: Mapping[str, str],
    postimage_files: Mapping[str, str],
    moves: Mapping[str, str],
    reference_targets: tuple[str, ...] = (),
) -> dict[str, str]:
    """Derive exact Markdown destination changes through the existing native parser."""
    expected: set[str | None] = {moves.get(path, path) for path in documents}
    payload = _observe(
        root,
        {
            "documents": [
                {"before": path, "after": moves.get(path, path), "content": text}
                for path, text in documents.items()
            ],
            "canonical": [],
            "files": dict(files),
            "postimage_files": dict(postimage_files),
            "moves": list(moves.items()),
            **({"reference_targets": list(reference_targets)} if reference_targets else {}),
        },
    )
    rows = _result_rows(payload, "documents", expected, complete=True)
    return {row["path"]: row["content"] for row in rows}


def archive_relocation(
    root: Path,
    *,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Return permitted derived bytes and their exact native archive preimages."""
    pairs = {
        parsed for path in changed_paths if (parsed := archived_change_from_path(path)) is not None
    }
    if not pairs:
        return {}, {}
    before = _entries(root, source_head, environment)
    after = _entries(root, tree, environment)
    valid = [
        (target, change)
        for target, change in pairs
        if any(path.startswith(active_change_root(change) + "/") for path in before)
    ]
    if not valid:
        return {}, {}
    if len(valid) != 1:
        message = "archive_reference_change_ambiguous"
        raise ValueError(message)
    target, change = valid[0]
    active = active_change_root(change)
    original = _source_documents(root, before, after, active, target)
    documents_at_archive, task_transition = _task_completion_inputs(
        root, original, before, after, active, target, tree, environment
    )
    documents = [
        {"before": path, "after": target + path.removeprefix(active), "content": content.decode()}
        for path, content in documents_at_archive.items()
    ]
    if not documents:
        return {}, {}
    canonical = _canonical_inputs(
        root, source_head, original, before, after, active, changed_paths, environment
    )
    payload = _observe(
        root,
        {
            "documents": documents,
            "canonical": canonical,
            "files": {path: value[0] for path, value in before.items()},
            "postimage_files": {path: value[0] for path, value in after.items()},
            "moves": [[active, target]],
            "change": change,
            **({"task_transition": task_transition} if task_transition else {}),
        },
    )
    rows = _result_rows(payload, "documents", {row["after"] for row in documents}, complete=True)
    corrected = {row["path"]: row["content"].encode() for row in rows}
    native = {row["after"]: documents_at_archive[row["before"]] for row in documents}
    for row in _result_rows(payload, "canonical", {row["after"] for row in canonical}):
        path = row["path"]
        corrected[path], native[path] = row["content"].encode(), row["original"].encode()
    updates, preimages = {}, {}
    for path, content in corrected.items():
        actual = _blob(root, tree, path, environment)
        if actual not in {native[path], content}:
            message = f"archive_reference_content_changed:{path}"
            raise ValueError(message)
        if content != native[path]:
            updates[path], preimages[path] = content, native[path]
    return updates, preimages


def _task_completion_inputs(
    root: Path,
    original: dict[str, bytes],
    before: TreeEntries,
    after: TreeEntries,
    active: str,
    target: str,
    tree: str,
    environment: Mapping[str, str] | None,
) -> tuple[dict[str, bytes], dict[str, str]]:
    """Pass a sole final task carrier to the official parser for validation."""
    source = f"{active}/tasks.md"
    destination = f"{target}/tasks.md"
    if source not in original:
        return original, {}
    archived = (
        original[source]
        if before[source][2] == after[destination][2]
        else _blob(root, tree, destination, environment)
    )
    if archived != original[source] and any(
        path.endswith("/tasks.md") and path != source for path in original
    ):
        message = f"archive_reference_task_transition_ambiguous:{destination}"
        raise ValueError(message)
    documents = original if archived == original[source] else {**original, source: archived}
    return documents, {
        "path": destination,
        "source": source,
        "before": original[source].decode(),
        "after": archived.decode(),
    }


def archived_reference_repair_paths(
    root: Path,
    *,
    head: str,
    change: str,
    archive_path: str,
    authorized_paths: tuple[str, ...],
    requested_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Select exact tracked Markdown consumers of one attested archive move."""
    members = tuple(
        path
        for path in authorized_paths
        if archived_change_from_path(path) == (archive_path, change)
    )
    if not members or not requested_paths:
        return ()
    active = active_change_root(change)
    postimage = _entries(root, head, None)
    preimage = dict(postimage)
    for path in members:
        if entry := postimage.get(path):
            preimage[active + path.removeprefix(archive_path)] = entry

    originals: dict[str, bytes] = {}
    documents: list[dict[str, str]] = []
    for path in dict.fromkeys(requested_paths):
        entry = postimage.get(path)
        if not path.endswith(".md") or entry is None or entry[0] not in {"100644", "100755"}:
            continue
        content = _blob(root, head, path, None)
        if active.encode() not in content:
            continue
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as error:
            message = f"archive_reference_consumer_encoding_invalid:{path}"
            raise ValueError(message) from error
        originals[path] = content
        documents.append({"before": path, "after": path, "content": decoded})
    if not documents:
        return ()
    observed = _observe(
        root,
        {
            "documents": documents,
            "canonical": [],
            "files": {path: entry[0] for path, entry in preimage.items()},
            "postimage_files": {path: entry[0] for path, entry in postimage.items()},
            "moves": [[active, archive_path]],
            "change": change,
        },
    )
    rows = _result_rows(observed, "documents", set(originals), complete=True)
    return tuple(
        sorted(row["path"] for row in rows if row["content"].encode() != originals[row["path"]])
    )


def _source_documents(
    root: Path, before: TreeEntries, after: TreeEntries, active: str, target: str
) -> dict[str, bytes]:
    members = {path: item for path, item in before.items() if path.startswith(active + "/")}
    destination = {
        active + path.removeprefix(target): item
        for path, item in after.items()
        if path.startswith(target + "/")
    }
    if members.keys() != destination.keys() or any(
        item[:2] != destination[path][:2] for path, item in members.items()
    ):
        message = "archive_reference_members_changed"
        raise ValueError(message)
    if any(item[0] not in {"100644", "100755"} for item in members.values()):
        message = "archive_reference_source_kind_unsupported"
        raise ValueError(message)
    markdown = {
        path: item
        for path, item in members.items()
        if path.endswith(".md") and item[0] in {"100644", "100755"} and item[1] == "blob"
    }
    if any(item != destination[path] for path, item in members.items() if path not in markdown):
        message = "archive_reference_content_changed"
        raise ValueError(message)
    return dict(
        zip(markdown, read_objects(root, tuple(item[2] for item in markdown.values())), strict=True)
    )


def _canonical_inputs(
    root: Path,
    source_head: str,
    original: dict[str, bytes],
    before: TreeEntries,
    after: TreeEntries,
    active: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None,
) -> list[dict[str, str | None]]:
    canonical = []
    for path, content in original.items():
        if not path.startswith(active + "/specs/") or not path.endswith("/spec.md"):
            continue
        output = "openspec/specs/" + path.removeprefix(active + "/specs/")
        if output not in after or output not in changed_paths:
            continue
        if after[output][:2] not in {("100644", "blob"), ("100755", "blob")}:
            message = f"archive_reference_canonical_type_invalid:{output}"
            raise ValueError(message)
        canonical.append(
            {
                "before": path,
                "after": output,
                "id": path.removeprefix(active + "/specs/").removesuffix("/spec.md"),
                "delta": content.decode(),
                "previous": _blob(root, source_head, output, environment).decode()
                if output in before
                else None,
            }
        )
    return canonical


def _observe(root: Path, inputs: dict[str, object]) -> dict[str, object]:
    command = openspec_base_command(execution_probe=False)
    if command is None:
        message = "openspec_official_cli_missing"
        raise ValueError(message)
    try:
        observed = run_command(
            root,
            (command[0], str(Path(__file__).with_suffix(".mjs")), command[1]),
            stdin=json.dumps(inputs),
            timeout=60,
        )
    except TimeoutExpired as error:
        message = "archive_reference_observation_timeout"
        raise ValueError(message) from error
    if observed.returncode:
        detail = next(
            (
                line.removeprefix("Error: ").strip()
                for line in observed.stderr.splitlines()
                if line.startswith("Error: archive_reference_")
            ),
            "archive_reference_observation_failed",
        )
        if detail == "archive_reference_observation_failed":
            detail += ":" + observed.stderr.strip()
        raise ValueError(detail)
    payload = json.loads(observed.stdout)
    if not isinstance(payload, dict) or set(payload) != {"documents", "canonical"}:
        message = "archive_reference_projection_invalid"
        raise ValueError(message)
    return payload


def _result_rows(
    payload: dict[str, object], key: str, allowed: set[str | None], *, complete: bool = False
) -> list[dict[str, str]]:
    rows = payload[key]
    fields = {"path", "content"} | ({"original"} if key == "canonical" else set())
    valid = isinstance(rows, list) and all(
        isinstance(row, dict)
        and set(row) == fields
        and all(isinstance(value, str) for value in row.values())
        for row in rows
    )
    if not valid:
        message = "archive_reference_projection_invalid"
        raise ValueError(message)
    paths = [row["path"] for row in rows]
    if (
        len(set(paths)) != len(paths)
        or not set(paths).issubset(allowed)
        or (complete and set(paths) != allowed)
    ):
        message = "archive_reference_projection_invalid"
        raise ValueError(message)
    return rows


def _entries(root: Path, revision: str, environment: Mapping[str, str] | None) -> TreeEntries:
    observed = run_git(root, "ls-tree", "-rz", revision, text=False, check=False, env=environment)
    if observed.returncode:
        message = "archive_reference_tree_unavailable"
        raise ValueError(message)
    entries: TreeEntries = {}
    for record in observed.stdout.split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            entries[path.decode()] = mode, kind, oid
    return entries


def _blob(root: Path, revision: str, path: str, environment: Mapping[str, str] | None) -> bytes:
    result = run_git(root, "show", f"{revision}:{path}", text=False, check=False, env=environment)
    if result.returncode:
        message = f"archive_reference_blob_unavailable:{path}"
        raise ValueError(message)
    return result.stdout


def active_change_relocation(
    root: Path,
    postimage: Path | None,
    effects: dict[str, str],
    *,
    baseline: str,
    tree: str = "",
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Observe one complete byte-and-mode preserving dated active source move."""
    names = {
        parts[2]
        for path in effects
        if len(parts := PurePosixPath(path).parts) >= 4 and parts[:2] == ("openspec", "changes")
    }
    dated = {name for name in names if logical_change_identifier_issue(name) == "temporal_suffix"}
    if not dated:
        return {}
    gap = "openspec_active_change_relocation_unverified"
    if len(dated) != 1:
        raise ValueError(gap)
    source_change = dated.pop()
    target_change = TEMPORAL_SUFFIX_PATTERN.sub("", source_change)
    if logical_change_identifier_issue(target_change) or names != {source_change, target_change}:
        raise ValueError(gap)
    source_root, target_root = (
        f"openspec/changes/{source_change}",
        active_change_root(target_change),
    )
    before = _entries(root, baseline, environment)
    if any(path.startswith(target_root + "/") for path in before):
        raise ValueError(gap)
    if tree:
        after = _entries(root, tree, environment)
        originals = _active_tree_members(before, source_root, gap)
        candidates = _active_tree_members(after, target_root, gap)
        remains = any(path.startswith(source_root + "/") for path in after)
    elif postimage is not None:
        destination = root / target_root
        if destination.exists() or destination.is_symlink():
            raise ValueError(gap)
        originals = _active_source_members(root, root / source_root, gap)
        candidates = _active_source_members(postimage, postimage / target_root, gap)
        remains = any(
            path.is_file() or path.is_symlink() for path in (postimage / source_root).rglob("*")
        )
    else:
        raise ValueError(gap)
    expected = {
        f"openspec/changes/{change}/{relative}": effect
        for relative in originals
        for change, effect in ((source_change, "delete"), (target_change, "create"))
    }
    if (
        ".openspec.yaml" not in originals
        or effects != expected
        or remains
        or candidates != originals
    ):
        raise ValueError(gap)
    return {
        "source_change": source_change,
        "target_change": target_change,
        "authorized_paths": sorted(expected),
    }


def _active_tree_members(entries: TreeEntries, prefix: str, gap: str) -> TreeEntries:
    """Use native blob identities and modes, never a mutable working postimage."""
    members = {
        path.removeprefix(prefix + "/"): entry
        for path, entry in entries.items()
        if path.startswith(prefix + "/")
    }
    if any(
        entry[0] not in {"100644", "100755"} or entry[1] != "blob" for entry in members.values()
    ):
        raise ValueError(gap)
    return members


def _active_source_members(root: Path, source: Path, gap: str) -> dict[str, tuple[int, bytes]]:
    """Read complete regular members; no hidden, linked or unknown-kind exception."""
    if not source.is_dir() or any(
        path.is_symlink() for path in (source, *source.parents) if path.is_relative_to(root)
    ):
        raise ValueError(gap)
    members = {}
    for path in source.rglob("*"):
        observed = path.lstat()
        if stat.S_ISDIR(observed.st_mode):
            continue
        mode = stat.S_IMODE(observed.st_mode)
        if not stat.S_ISREG(observed.st_mode) or mode not in {0o644, 0o755}:
            raise ValueError(gap)
        members[path.relative_to(source).as_posix()] = mode, path.read_bytes()
    return members


def active_change_relocation_scope(
    root: Path, *, role: str, requested_paths: tuple[str, ...], report: dict[str, object]
) -> dict[str, object]:
    """Admit only the observed identity move, not edits or later qualification."""
    relocation = report.get("active_change_relocation")
    if role != ROLE_WORK_LANE or not isinstance(relocation, dict):
        return {}
    source, target = relocation["source_change"], relocation["target_change"]
    selected = requested_change()
    matched = (
        report_verdict(report) == "pass"
        and sorted(set(requested_paths)) == relocation["authorized_paths"]
        and selected in {None, source, target}
    )
    gaps = [] if matched else ["openspec_active_change_relocation_scope_mismatch"]
    if matched and not report.get("index_tree"):
        observed = run_git(root, "rev-parse", "--verify", "HEAD", check=False)
        if observed.returncode or observed.stdout.strip() != report.get("baseline_head"):
            gaps = ["openspec_active_change_relocation_head_changed"]
            matched = False
    return {
        "verdict": "pass" if matched else "block",
        "state": "active_change_relocation",
        "changed_paths": list(requested_paths),
        "material_paths": list(requested_paths) if matched else [],
        "authorized_paths": relocation["authorized_paths"] if matched else [],
        "changes": [{"name": target}],
        "required_gaps": gaps,
        "next_action": "" if matched else "unset ETHOS_CHANGE",
        "evidence_boundary": "exact_source_identity_repair_only",
        "openspec": {"verdict": "unknown", "state": "identity_repair_only", "required_gaps": []},
    }
