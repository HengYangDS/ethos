"""Exact patch materialization and source/producer effect admission."""

from __future__ import annotations

import shlex
import shutil
import tempfile
from pathlib import Path

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_blobs
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import Projection
from ethos.repository.policy.projections import projection_effect_gaps
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.references.carriers import REFERENCE_CARRIERS
from ethos.repository.policy.references.closure import product_reference_gaps
from ethos.repository.policy.references.declarations import command_owner_sources_from_files
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import deleted_input_gaps
from ethos.repository.policy.references.observation import product_references_from_files

_UNIFIED_DIFF_HEADER_PART_COUNT = 4
_OWNER_SUFFIXES = (".json", ".py", ".toml")


def patch_admission(
    *,
    root: Path,
    requested_paths: tuple[str, ...],
    baseline_head: str,
    patch: str,
) -> dict[str, object]:
    """Validate a patch against its baseline scope and product closure."""
    if not patch:
        return {
            "verdict": "pass",
            "state": "not_requested",
            "reason": "not_requested",
            "baseline_head": baseline_head,
            "paths": [],
            "references": {},
        }
    changes, parse_gap = _unified_patch_changes(patch)
    patch_paths = sorted({str(change["path"]) for change in changes})
    requested = sorted(set(requested_paths))
    reason = parse_gap
    if not reason and patch_paths != requested:
        reason = "prewrite_patch_paths_mismatch"
    if not reason and not baseline_head:
        reason = "prewrite_patch_baseline_missing"
    if not reason and not _patch_applies(root, patch, check_preimage=True):
        reason = "prewrite_patch_preimage_mismatch"
    references: dict[str, set[str]] = {}
    unknown: list[str] = []
    effects: dict[str, str] = {}
    outputs: list[str] = []
    if not reason:
        try:
            baseline_files = _baseline_reference_files(root, baseline_head)
            baseline_references = native_owned_references_from_files(baseline_files)
            references, effect_gaps, unknown, effects, outputs = _patch_references(
                root,
                patch,
                changes,
                context_files=baseline_files,
                declared_commands=baseline_references["command"],
            )
            reason = effect_gaps[0] if effect_gaps else ""
        except (OSError, UnicodeError, ValueError):
            reason = "prewrite_patch_postimage_failed"
    if not reason:
        gaps = product_reference_gaps(baseline_references, references)
        reason = gaps[0] if gaps else ""
    return {
        "verdict": "block" if reason else "unknown" if unknown else "pass",
        "state": "blocked" if reason else "unknown" if unknown else "admitted",
        "reason": reason or (unknown[0] if unknown else "baseline_product_closure_matched"),
        "effects": effects,
        "origin_outputs": outputs,
        "unknown_inputs": unknown,
        "coverage": "changed_references_and_explicit_native_inputs",
        "baseline_head": baseline_head,
        "paths": patch_paths,
        "references": {key: sorted(value) for key, value in references.items() if value},
    }


def _patch_applies(root: Path, patch: str, *, check_preimage: bool = False) -> bool:
    command = ["apply", "--whitespace=error-all", "-"]
    if check_preimage:
        command.insert(2, "--check")
    return run_git(root, *command, stdin=patch, text=True, check=False).returncode == 0


def projection_preimages(root: Path, head: str) -> dict[str, str]:
    """Read exact committed producer declarations even when their work copies vanished."""
    if not head:
        return {}
    return {
        path: completed.stdout
        for path in PROJECTION_DECLARATIONS
        if (completed := run_git(root, "show", f"{head}:{path}", check=False)).returncode == 0
    }


def _baseline_reference_files(root: Path, head: str) -> dict[str, str]:
    """Read declared carrier inputs in one object batch, preserving exact newlines."""
    return {
        path: text
        for path, text in _object_files(root, head).items()
        if any(carrier.matches(path) for carrier in REFERENCE_CARRIERS)
    }


def _object_files(
    root: Path, revision: str, extra_paths: frozenset[str] = frozenset()
) -> dict[str, str]:
    if not revision:
        return {}
    records = run_git(root, "ls-tree", "-r", "-z", revision, text=False).stdout
    entries = {}
    for record in filter(None, records.split(b"\0")):
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind == b"blob" and mode in {b"100644", b"100755"}:
            entries[raw_path.decode("utf-8")] = oid.decode("ascii")
    selected = {
        path: oid
        for path, oid in entries.items()
        if path.endswith(_OWNER_SUFFIXES) or path in extra_paths
    }
    files = _read_text_objects(root, selected)
    producers = projection_relations(files)
    dependent = {path for item in producers for path in (item.source, item.output)}
    files.update(
        _read_text_objects(
            root,
            {path: entries[path] for path in sorted(dependent - files.keys()) if path in entries},
        )
    )
    return files


def _read_text_objects(root: Path, entries: dict[str, str]) -> dict[str, str]:
    return dict(
        zip(
            entries,
            (blob.decode("utf-8") for blob in read_blobs(root, tuple(entries.values()))),
            strict=True,
        )
    )


def staged_artifact_admission(root: Path, baseline: str) -> dict[str, object]:
    """Observe the prospective index tree; working files never substitute for staged bytes."""
    selected = run_git(root, "write-tree", check=False)
    if selected.returncode:
        return {"verdict": "unknown", "reason": "staged_tree_unavailable", "effects": {}}
    tree = selected.stdout.strip()
    try:
        before = _object_files(root, baseline)
        prior_paths = frozenset(
            path for item in projection_relations(before) for path in (item.source, item.output)
        )
        after = _object_files(root, tree, prior_paths)
        effects = _indexed_effects(root)
        postimages = {path: after.get(path) for path in effects}
        # Non-carrier changes have no text observation, but are not deletions.
        postimages = {
            path: value
            for path, value in postimages.items()
            if path in before or path in after or effects[path] == "delete"
        }
        gaps, unknown = _effect_gaps(projection_relations(before), after, postimages)
    except (OSError, ValueError, UnicodeError) as exc:
        return {
            "verdict": "unknown",
            "reason": f"staged_artifact_observation_unknown:{exc}",
            "effects": {},
        }
    reason = gaps[0] if gaps else unknown[0] if unknown else "staged_artifact_effects_matched"
    report = {
        "verdict": "block" if gaps else "unknown" if unknown else "pass",
        "reason": reason,
        "effects": effects,
        "index_tree": tree,
        "baseline_head": baseline,
        "origin_outputs": sorted(
            {item.output for item in (*projection_relations(before), *projection_relations(after))}
        ),
        "required_gaps": [*gaps, *unknown],
    }
    return revalidate_staged_admission(root, report)


def revalidate_staged_admission(root: Path, report: dict[str, object]) -> dict[str, object]:
    """Fence an observed index result at its consuming admission boundary."""
    if not report.get("index_tree"):
        return report
    coordinates = (
        ("tree", "index_tree", ("write-tree",)),
        ("head", "baseline_head", ("rev-parse", "--verify", "HEAD")),
    )
    for name, field, args in coordinates:
        observed = run_git(root, *args, check=False)
        if observed.returncode or observed.stdout.strip() != report[field]:
            gap = f"staged_{name}_changed_during_admission"
            previous = report.get("required_gaps", [])
            gaps = list(previous) if isinstance(previous, list) else []
            return {
                **report,
                "verdict": "block",
                "reason": gap,
                "required_gaps": list(dict.fromkeys([gap, *gaps])),
            }
    return report


def _indexed_effects(root: Path) -> dict[str, str]:
    """Read exact index effects without rename heuristics or working-tree postimages."""
    statuses = run_git(root, "diff", "--cached", "--name-status", "--no-renames", "-z", check=False)
    if statuses.returncode:
        message = "staged_diff_unavailable"
        raise ValueError(message)
    parts = statuses.stdout.rstrip("\0").split("\0") if statuses.stdout else []
    if len(parts) % 2:
        message = "staged_diff_invalid"
        raise ValueError(message)
    return {
        path: "delete" if kind == "D" else "create" if kind == "A" else "modify"
        for kind, path in zip(parts[::2], parts[1::2], strict=True)
    }


def _unified_patch_changes(patch: str) -> tuple[list[dict[str, object]], str]:
    changes: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in patch.splitlines():
        if line.startswith(("GIT binary patch", "Binary files ")):
            return changes, "prewrite_patch_binary_unsupported"
        if line.startswith("diff --git "):
            current = _new_patch_change(line)
            if current is None:
                return changes, "prewrite_patch_invalid"
            changes.append(current)
        elif current is not None:
            _update_patch_change(current, line)
    if not changes or any(not change["path"] for change in changes):
        return changes, "prewrite_patch_invalid"
    return changes, ""


def _new_patch_change(line: str) -> dict[str, object] | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None
    if len(parts) != _UNIFIED_DIFF_HEADER_PART_COUNT:
        return None
    return {
        "old_path": _patch_path(parts[2]),
        "path": _patch_path(parts[3]),
        "new": False,
        "deleted": False,
    }


def _update_patch_change(change: dict[str, object], line: str) -> None:
    if line.startswith("--- "):
        change["old_path"] = _patch_path(line[4:].split("\t", 1)[0])
        change["new"] = change["old_path"] == "/dev/null"
    elif line.startswith("+++ "):
        path = _patch_path(line[4:].split("\t", 1)[0])
        change["deleted"] = path == "/dev/null"
        if path != "/dev/null":
            change["path"] = path


def _patch_path(raw: str) -> str:
    if raw == "/dev/null":
        return raw
    return raw.removeprefix("a/").removeprefix("b/")


def _patch_references(
    root: Path,
    patch: str,
    changes: list[dict[str, object]],
    *,
    context_files: dict[str, str],
    declared_commands: tuple[str, ...] | frozenset[str] = (),
) -> tuple[dict[str, set[str]], list[str], list[str], dict[str, str], list[str]]:
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        for change in changes:
            old_path = str(change["old_path"])
            if old_path == "/dev/null":
                continue
            relative = Path(old_path)
            if relative.is_absolute() or ".." in relative.parts:
                msg = "prewrite patch path escapes root"
                raise ValueError(msg)
            source = root / relative
            if not source.is_file():
                msg = "prewrite patch preimage missing"
                raise ValueError(msg)
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if not _patch_applies(workspace, patch):
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        postimages: dict[str, str | None] = {}
        for change in changes:
            path = str(change["path"])
            relative = Path(path)
            if relative.is_absolute() or ".." in relative.parts:
                msg = "prewrite patch path escapes root"
                raise ValueError(msg)
            target = workspace / relative
            postimages[path] = target.read_text(encoding="utf-8") if target.is_file() else None
        files = {
            path: text
            for path, text in postimages.items()
            if text is not None and any(carrier.matches(path) for carrier in REFERENCE_CARRIERS)
        }
        references = product_references_from_files(
            files,
            context_files=context_files,
            declared_commands=declared_commands,
            include_declarations=False,
        )
        references["command"].update(command_owner_sources_from_files(files))
        gaps, unknown, outputs = _source_effect_gaps(root, context_files, postimages)
        effects = {
            str(change["path"]): "delete"
            if change["deleted"]
            else "create"
            if change["new"]
            else "modify"
            for change in changes
        }
        return references, gaps, unknown, effects, outputs


def _source_effect_gaps(
    root: Path,
    context_files: dict[str, str],
    postimages: dict[str, str | None],
) -> tuple[list[str], list[str], list[str]]:
    """Resolve effective native inputs from current files and exact patch postimages."""
    effective = {
        path: (root / path).read_text(encoding="utf-8")
        for path in context_files
        if (root / path).is_file() and (root / path).resolve().is_relative_to(root.resolve())
    }
    for path in PROJECTION_DECLARATIONS:
        if (root / path).is_file():
            effective[path] = (root / path).read_text(encoding="utf-8")
    before = _prior_projection_relations(context_files, effective, postimages)
    effective.update({path: text for path, text in postimages.items() if text is not None})
    deleted = frozenset(path for path, text in postimages.items() if text is None)
    for path in deleted:
        effective.pop(path, None)
    after = projection_relations(effective)
    for relation in (*before, *after):
        for path in (relation.source, relation.output):
            source = root / path
            if path not in postimages and source.is_file():
                if not source.resolve().is_relative_to(root.resolve()):
                    msg = f"projection_input_outside_root:{path}"
                    raise ValueError(msg)
                effective[path] = source.read_text(encoding="utf-8")
    gaps, unknown = _effect_gaps(before, effective, postimages)
    return gaps, unknown, sorted({item.output for item in (*before, *after)})


def _prior_projection_relations(
    baseline: dict[str, str], current: dict[str, str], postimages: dict[str, str | None]
) -> tuple[Projection, ...]:
    """Retain known owners while an exact patch repairs invalid working syntax."""
    observed = list(projection_relations(baseline))
    for path in PROJECTION_DECLARATIONS.keys() & current.keys():
        try:
            observed.extend(projection_relations({path: current[path]}))
        except ValueError:
            if path not in postimages:
                raise
    return tuple(dict.fromkeys(observed))


def _effect_gaps(
    before: tuple[Projection, ...],
    effective: dict[str, str],
    postimages: dict[str, str | None],
) -> tuple[list[str], list[str]]:
    """Evaluate producer consistency and surviving consumers once for every input plane."""
    after = projection_relations(effective)
    deleted = frozenset(path for path, value in postimages.items() if value is None)
    gaps = projection_effect_gaps(before, after, effective, postimages)
    dangling, unknown = deleted_input_gaps(effective, deleted)
    return sorted({*gaps, *dangling}), unknown
