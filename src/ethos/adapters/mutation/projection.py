"""Prepare and admit complete native projection patches from one unchanged input closure."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.mutation.carrier_edit import apply_carrier_edits
from ethos.adapters.projections.compiler import render_projections
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import current_tracked_head
from ethos.repository.paradigm.repair import CarrierEdit
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations

if TYPE_CHECKING:
    from pathlib import Path


def project_repository(
    root: Path,
    *,
    check: bool = False,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str = "",
    preview_patch: str | None = None,
) -> dict[str, object]:
    """Compile real native inputs once, then preview, check or admit the complete exact patch."""
    try:
        return _project_repository(
            root,
            check=check,
            apply=apply,
            authorize=authorize,
            expect_head=expect_head,
            preview_patch=preview_patch,
        )
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        return {
            "verdict": "block",
            "state": "blocked",
            "applied": False,
            "required_gaps": [str(error) or "projection_unavailable"],
            "next_action": "repair the reported projection input and obtain a fresh preview",
        }


def _project_repository(
    root: Path,
    *,
    check: bool,
    apply: bool,
    authorize: bool,
    expect_head: str,
    preview_patch: str | None,
) -> dict[str, object]:
    if check and apply:
        message = "projection_mode_conflict"
        raise ValueError(message)
    head = current_tracked_head(root)
    if expect_head and expect_head != head:
        message = "expect_head_mismatch"
        raise ValueError(message)
    if apply and (not authorize or not expect_head or preview_patch is None):
        message = "projection_exact_authorization_required"
        raise ValueError(message)
    declarations = _declarations(root)
    relations = projection_relations(
        {path: data.decode("utf-8") for path, data in declarations.items()}
    )
    if not relations:
        message = "projection_declaration_missing"
        raise ValueError(message)
    materials = declarations | {
        path: read_regular_bytes(
            root,
            path,
            unsafe_gap="projection_input_unsafe",
            unstable_gap="projection_input_changed",
            size_gap="projection_input_size_exceeded",
        )
        for item in relations
        for path in item.materials
        if path != item.output and path not in declarations
    }
    files = {path: data.decode("utf-8") for path, data in materials.items()}
    rendered = render_projections(root, relations, files, dict(files))
    edits = []
    for item in relations:
        target = root / item.output
        before = None
        if target.exists() or target.is_symlink():
            before = read_regular_bytes(
                root,
                item.output,
                unsafe_gap="projection_output_unsafe",
                unstable_gap="projection_output_changed",
                size_gap="projection_output_size_exceeded",
            ).decode("utf-8")
        after = rendered[item.output] if item.kind == "cue" else item.render(files[item.source])
        edits.append(CarrierEdit(item.output, before, after))
    if (
        current_tracked_head(root) != head
        or _declarations(root) != declarations
        or any(
            read_regular_bytes(
                root,
                path,
                unsafe_gap="projection_input_unsafe",
                unstable_gap="projection_input_changed",
                size_gap="projection_input_size_exceeded",
            )
            != data
            for path, data in materials.items()
        )
    ):
        message = "projection_input_changed"
        raise ValueError(message)
    report = apply_carrier_edits(
        root=root,
        edits=tuple(edits),
        apply=apply,
        preview_patch=preview_patch,
        next_action=(
            "ethos lane project --apply --authorize --expect-head "
            + head
            + " --patch <preview.patch> --json"
        ),
    )
    changed = report["edits"]
    if check and report["verdict"] == "pass" and isinstance(changed, list) and changed:
        report = {
            **report,
            "verdict": "block",
            "state": "drifted",
            "required_gaps": [
                "generated_projection_drift:" + str(edit["path"]) for edit in changed
            ],
        }
    return {**report, "head": head, "output_count": len(relations)}


def _declarations(root: Path) -> dict[str, bytes]:
    """Select relation bytes once through the same bounded no-follow input reader."""
    return {
        path: read_regular_bytes(
            root,
            path,
            unsafe_gap="projection_input_unsafe",
            unstable_gap="projection_input_changed",
            size_gap="projection_input_size_exceeded",
        )
        for path in PROJECTION_DECLARATIONS
        if (root / path).exists() or (root / path).is_symlink()
    }
