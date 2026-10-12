"""Bind supporting-file relocation to exact native scope and preserved references."""

from __future__ import annotations

from pathlib import PurePosixPath
from stat import S_IMODE
from stat import S_ISREG
from typing import TYPE_CHECKING

from ethos.adapters.openspec.configuration import official_config_report
from ethos.adapters.openspec.lifecycle.scope import canonical_repair_context_valid
from ethos.adapters.openspec.lifecycle.validation import validation_result_gaps
from ethos.adapters.openspec.relocation import relocate_documents
from ethos.adapters.repo.git import run_git
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.audit import accepted_spec_root_gaps
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def supporting_file_relocation(
    root: Path, postimages: Mapping[str, str | None], *, postimage_root: Path
) -> dict[str, object]:
    """Recognize one exact Markdown move out of canonical specs, never a policy waiver."""
    proposal = _relocation_proposal(root, postimages)
    if proposal is None:
        return {}
    source, destination, configuration = proposal
    profile = load_repository_profile(root)
    policy = profile.declaration.openspec if profile.declaration is not None else None
    gaps = accepted_spec_root_gaps(root / "openspec/specs", policy=policy)
    repaired_gap = f"openspec_specs_root_entry_unexpected:{PurePosixPath(source).name}"
    if repaired_gap not in gaps:
        return {}
    paths = run_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
    files, documents = {}, {}
    for path in filter(None, paths.split("\0")):
        candidate = root / path
        if not candidate.exists() and not candidate.is_symlink():
            continue
        regular = S_ISREG(candidate.lstat().st_mode) and candidate.resolve().is_relative_to(
            root.resolve()
        )
        files[path] = "100644" if regular else "120000"
        if regular and candidate.suffix == ".md":
            documents[path] = candidate.read_text(encoding="utf-8")
    if source not in documents:
        return {}
    after_files = {path: mode for path, mode in files.items() if path != source}
    after_files[destination] = "100644"
    relocated = relocate_documents(
        root,
        documents=documents,
        files=files,
        postimage_files=after_files,
        moves={source: destination},
        reference_targets=(source,),
    )
    expected: dict[str, str | None] = {source: None, destination: relocated.pop(destination)}
    expected.update({path: text for path, text in relocated.items() if text != documents[path]})
    if dict(postimages) != expected or any(
        S_IMODE((postimage_root / path).lstat().st_mode)
        != S_IMODE((root / (source if path == destination else path)).lstat().st_mode)
        for path, text in expected.items()
        if text is not None
    ):
        return {}
    # Native shape checks root members independently. This exact move removes one
    # rejected regular member; every other shape-bearing member remains unchanged.
    remaining = [gap for gap in gaps if gap != repaired_gap]
    if not set(remaining) < set(gaps):
        return {}
    return {
        "source": source,
        "destination": destination,
        "paths": sorted(expected),
        "removed_gaps": [repaired_gap],
        "remaining_shape_gaps": remaining,
        "configuration_digest": configuration["input_digest"],
        "evidence_boundary": "exact_native_reference_relocation_and_unchanged_root_members",
    }


def _relocation_proposal(
    root: Path, postimages: Mapping[str, str | None]
) -> tuple[str, str, dict[str, object]] | None:
    """Resolve the original member and its distinct current native template owner."""
    deleted = [
        path
        for path, text in postimages.items()
        if text is None and PurePosixPath(path).parent.as_posix() == "openspec/specs"
    ]
    if len(deleted) != 1:
        return None
    source = deleted[0]
    member = root / source
    if member.suffix != ".md" or member.name == "README.md" or not S_ISREG(member.lstat().st_mode):
        return None
    destinations = [
        path
        for path, text in postimages.items()
        if text is not None and not (root / path).exists() and not (root / path).is_symlink()
    ]
    if len(destinations) != 1:
        return None
    destination = destinations[0]
    configuration = official_config_report(root)
    schema = configuration.get("schema")
    template_root = f"openspec/schemas/{schema}/templates"
    declared_schema = f"repository:openspec/schemas/{schema}/schema.yaml"
    inputs = configuration.get("inputs")
    if (
        configuration.get("verdict") != "pass"
        or not isinstance(schema, str)
        or PurePosixPath(destination).parent.as_posix() != template_root
        or PurePosixPath(destination).suffix != ".md"
        or not isinstance(inputs, list)
        or not any(
            isinstance(item, dict) and item.get("path") == declared_schema for item in inputs
        )
        or any(
            isinstance(item, dict) and item.get("path") == f"repository:{destination}"
            for item in inputs
        )
        or not (root / template_root).resolve().is_relative_to(root.resolve())
    ):
        return None
    return source, destination, configuration


def supporting_relocation_scope(
    *,
    role: str,
    requested_paths: tuple[str, ...],
    repair: object,
    official: dict[str, object],
) -> dict[str, object]:
    """Admit a verified supporting move for one complete current official Change."""
    if role != ROLE_WORK_LANE or not isinstance(repair, dict):
        return {}
    paths = tuple(string_sequence(repair.get("paths")))
    removed = tuple(string_sequence(repair.get("removed_gaps")))
    change = str(official.get("change") or "")
    commands = official.get("commands")
    commands = commands if isinstance(commands, dict) else {}
    validate, status, listed = (commands.get(key) for key in ("validate", "status", "list"))
    gaps = string_sequence(official.get("required_gaps"))
    configuration = official.get("official_config")
    if (
        not paths
        or set(paths) != set(requested_paths)
        or len(removed) != 1
        or removed[0] not in gaps
        or not canonical_repair_context_valid(official, change=change, exact_repair_gaps=removed)
        or not isinstance(listed, dict)
        or listed.get("exit_code") != 0
        or listed.get("parse_error")
        or not isinstance(listed.get("json"), dict)
        or not isinstance(status, dict)
        or status.get("exit_code") != 0
        or status.get("parse_error")
        or not isinstance(status.get("json"), dict)
        or status["json"].get("changeName") != change
        or not isinstance(validate, dict)
        or not isinstance(validate.get("json"), dict)
        or validate.get("parse_error")
        or set(validation_result_gaps(validate)) != set(gaps) - set(removed)
        or not isinstance(configuration, dict)
        or repair.get("configuration_digest") != configuration.get("input_digest")
    ):
        return {}
    return {
        "verdict": "pass",
        "state": "openspec_supporting_file_relocation",
        "changed_paths": list(requested_paths),
        "material_patterns": [],
        "material_paths": list(requested_paths),
        "changes": [{"name": change, "path": active_change_root(change)}],
        "covered_paths": [{"path": path, "changes": [change]} for path in requested_paths],
        "uncovered_paths": [],
        "authorized_paths": list(paths),
        "required_gaps": [],
        "advisory_gaps": [],
        "removed_gaps": list(removed),
        "evidence_boundary": repair["evidence_boundary"],
        "next_action": "openspec validate --all --strict --json",
    }
