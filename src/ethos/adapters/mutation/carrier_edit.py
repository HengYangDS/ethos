"""Apply exact carrier text edits through the existing Work Lane effect boundary."""

from __future__ import annotations

import stat
import subprocess
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import run_git
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.repository.paradigm.repair import CarrierEdit


class _Image(NamedTuple):
    content: bytes | None
    executable: bool = False


def apply_carrier_edits(
    *,
    root: Path,
    edits: tuple[CarrierEdit, ...],
    apply: bool = False,
    next_action: str = "",
    preview_patch: str | None = None,
) -> dict[str, object]:
    """Preview live byte preimages or admit and apply their exact native Git patch.

    The caller retains CarrierEdit.before until acceptance or recovery. Preview
    writes only disposable diff inputs, never working files, index or refs.
    Apply performs no staging, ref update or automatic compensation.
    """
    repo = root.resolve()
    selected = tuple(
        sorted((edit for edit in edits if edit.before != edit.after), key=lambda edit: edit.path)
    )
    planned: dict[str, object] = {
        "verdict": "pass",
        "state": "planned" if selected else "conforming",
        "applied": False,
        "patch": "",
        "edits": [
            {
                "path": edit.path,
                "created": edit.before is None,
                "removed": edit.after is None,
            }
            for edit in selected
        ],
        "required_gaps": [],
        "next_action": next_action if selected else "",
        "user_decision_required": False,
    }
    try:
        if len({edit.path for edit in edits}) != len(edits):
            return _blocked(planned, ["carrier_edit_duplicate_path"])
        before = {edit.path: _read_image(repo, edit.path) for edit in selected}
        gaps = _preimage_gaps(selected, before)
        if gaps:
            return _blocked(planned, gaps)
        patch = _native_patch(selected, before)
        planned["patch"] = patch
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return _blocked(planned, ["carrier_edit_preview_unavailable"], error=error)
    if preview_patch is not None and preview_patch != patch:
        return _blocked(planned, ["carrier_edit_preview_patch_mismatch"])
    if not apply or not selected:
        return planned
    return _apply(repo, selected, before, patch, planned)


def _blocked(
    planned: dict[str, object],
    gaps: list[str],
    *,
    error: BaseException | None = None,
) -> dict[str, object]:
    result = {
        **planned,
        "verdict": "block",
        "state": "blocked",
        "applied": False,
        "required_gaps": gaps,
        "next_action": "Reobserve the exact carrier inputs and obtain a fresh preview.",
        "lifecycle_effect_outcome": lifecycle_effect_outcome(kind="zero_effect"),
    }
    if error is not None:
        result["failure"] = _failure(error)
    return result


def _read_image(root: Path, relative: str) -> _Image:
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or path.as_posix() != relative
        or ".." in path.parts
        or "\\" in relative
        or "\0" in relative
        or path.parts[0] == ".git"
    ):
        message = "carrier_edit_unsafe_path"
        raise ValueError(message)
    target = root
    for part in path.parts[:-1]:
        target /= part
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            return _Image(None)
        if not stat.S_ISDIR(mode):
            message = "carrier_edit_unsafe_path"
            raise ValueError(message)
    target = root / relative
    try:
        observed = target.lstat()
    except FileNotFoundError:
        return _Image(None)
    content = read_regular_bytes(
        root,
        relative,
        unsafe_gap=f"carrier_edit_unsafe_path:{relative}",
        unstable_gap=f"carrier_edit_unstable_path:{relative}",
        size_gap=f"carrier_edit_size_exceeded:{relative}",
    )
    if target.lstat().st_mode != observed.st_mode:
        message = "carrier_edit_mode_changed"
        raise ValueError(message)
    return _Image(content, bool(observed.st_mode & stat.S_IXUSR))


def _preimage_gaps(edits: tuple[CarrierEdit, ...], images: dict[str, _Image]) -> list[str]:
    return [
        f"carrier_edit_preimage_changed:{edit.path}"
        for edit in edits
        if images[edit.path].content != _bytes(edit.before)
    ]


def _bytes(text: str | None) -> bytes | None:
    return text.encode("utf-8") if text is not None else None


def _native_patch(edits: tuple[CarrierEdit, ...], before: dict[str, _Image]) -> str:
    """Let Git own creation, deletion, literal paths and missing-final-newline syntax."""
    if not edits:
        return ""
    context = max(
        (text.count("\n") + 1 for edit in edits for text in (edit.before, edit.after) if text),
        default=1,
    )
    with tempfile.TemporaryDirectory(prefix="ethos-carrier-edit-") as temporary:
        workspace = Path(temporary)
        for prefix in ("a", "b"):
            (workspace / prefix).mkdir()
        for edit in edits:
            for prefix, text in (("a", edit.before), ("b", edit.after)):
                if text is None:
                    continue
                target = workspace / prefix / edit.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(text.encode("utf-8"))
                target.chmod(0o755 if before[edit.path].executable else 0o644)
        completed = run_git(
            workspace,
            "-c",
            "core.quotePath=false",
            "diff",
            "--no-index",
            "--no-prefix",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--binary",
            "--full-index",
            f"--unified={context}",
            "--",
            "a",
            "b",
            text=False,
            check=False,
            observation=True,
        )
        if completed.returncode != 1 or not completed.stdout:
            message = "carrier_edit_native_diff_failed"
            raise ValueError(message)
        return completed.stdout.decode("utf-8")


def _git_state(root: Path) -> dict[str, bytes | None]:
    """Read the native coordinates and raw index without refreshing it."""
    index_path = Path(
        run_git(
            root, "rev-parse", "--path-format=absolute", "--git-path", "index", observation=True
        ).stdout.strip()
    )
    try:
        index = index_path.read_bytes()
    except FileNotFoundError:
        index = None
    head = run_git(
        root, "rev-parse", "--verify", "--quiet", "HEAD", text=False, check=False, observation=True
    )
    if head.returncode not in (0, 1):
        message = "carrier_edit_head_unavailable"
        raise ValueError(message)
    return {
        "head": head.stdout,
        "head_ref": run_git(
            root, "symbolic-ref", "--quiet", "HEAD", text=False, check=False, observation=True
        ).stdout,
        "refs": run_git(
            root,
            "for-each-ref",
            "--format=%(refname) %(objectname) %(symref)",
            text=False,
            observation=True,
        ).stdout,
        "raw_index": index,
    }


def _apply(
    root: Path,
    edits: tuple[CarrierEdit, ...],
    before: dict[str, _Image],
    patch: str,
    planned: dict[str, object],
) -> dict[str, object]:
    try:
        git_before = _git_state(root)
        admission = prewrite_guard(
            root=root,
            paths=[root / edit.path for edit in edits],
            editor_root=root,
            require_editor_root=True,
            patch=patch,
        )
        planned = {**planned, "admission": admission}
        if report_verdict(admission) != "pass":
            return {
                **_blocked(planned, list(string_sequence(admission.get("required_gaps")))),
                "verdict": report_verdict(admission),
                "next_action": str(admission.get("next_action") or ""),
                "user_decision_required": bool(admission.get("user_decision_required", False)),
            }
        current = {edit.path: _read_image(root, edit.path) for edit in edits}
        preservation = _preservation(git_before, _git_state(root))
        gaps = [
            f"carrier_edit_preimage_changed:{path}"
            for path, image in before.items()
            if current[path] != image
        ]
        gaps.extend(
            f"carrier_edit_git_state_changed:{name}"
            for name, unchanged in preservation.items()
            if not unchanged
        )
        gaps.extend(_authority_gaps(root, admission))
        if gaps:
            return {**_blocked(planned, gaps), "preservation": preservation}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return _blocked(planned, ["carrier_edit_prewrite_unavailable"], error=error)
    error = None
    diagnostics: dict[str, object] = {}
    try:
        completed = run_git(
            root,
            "apply",
            "--whitespace=error-all",
            "-",
            stdin=patch.encode("utf-8"),
            text=False,
            check=False,
            timeout=30,
        )
        diagnostics = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout.decode("utf-8", errors="replace"),
            "stderr": completed.stderr.decode("utf-8", errors="replace"),
        }
    except (
        OSError,
        ProcessExecutionError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as caught:
        error = caught
    return _finish(root, edits, before, git_before, planned, diagnostics, error)


def _authority_gaps(root: Path, admission: dict[str, object]) -> list[str]:
    """Reobserve the original authority after patch admission, without a second grant."""
    expected = string_mapping(admission.get("mutation_authority"))
    if not expected:
        return ["carrier_edit_mutation_authority_missing"]
    observed = observe_current_authority(
        root=root,
        branch=str(expected.get("branch") or ""),
        actor=str(expected.get("invocation_holder_ref") or ""),
        required=bool(expected.get("required", True)),
        head_source=str(expected.get("head_source") or "head"),
    ).projection()
    return [
        f"carrier_edit_authority_changed:{name}"
        for name in (
            "verdict",
            "holder_ref",
            "invocation_holder_ref",
            "generation",
            "current_head",
            "binding_head",
        )
        if expected.get(name) != observed.get(name)
    ]


def _preservation(
    before: dict[str, bytes | None], after: dict[str, bytes | None]
) -> dict[str, bool]:
    return {name: value == after[name] for name, value in before.items()}


def _finish(
    root: Path,
    edits: tuple[CarrierEdit, ...],
    before: dict[str, _Image],
    git_before: dict[str, bytes | None],
    planned: dict[str, object],
    diagnostics: dict[str, object],
    error: BaseException | None,
) -> dict[str, object]:
    effects: dict[str, str] = {}
    gaps: list[str] = []
    for edit in edits:
        try:
            image = _read_image(root, edit.path)
        except (OSError, ValueError):
            effects[edit.path] = "unknown"
            gaps.append(f"carrier_edit_postimage_unavailable:{edit.path}")
            continue
        expected = _Image(
            _bytes(edit.after), before[edit.path].executable if edit.after is not None else False
        )
        effects[edit.path] = (
            "postimage"
            if image == expected
            else "preimage"
            if image == before[edit.path]
            else "diverged"
        )
        if image != expected:
            gaps.append(f"carrier_edit_postimage_mismatch:{edit.path}")
    try:
        preservation: dict[str, bool | None] = dict(_preservation(git_before, _git_state(root)))
    except (OSError, ValueError, subprocess.SubprocessError):
        preservation = dict.fromkeys(git_before)
    gaps.extend(
        f"carrier_edit_git_state_{'unavailable' if unchanged is None else 'changed'}:{name}"
        for name, unchanged in preservation.items()
        if unchanged is not True
    )
    if error is not None or diagnostics.get("exit_code") != 0:
        gaps.insert(0, "carrier_edit_native_apply_unconfirmed")
    successful = not gaps
    changed = any(state in {"postimage", "diverged"} for state in effects.values())
    unknown = "unknown" in effects.values() or None in preservation.values()
    action = (
        ""
        if successful
        else "Reobserve each effect; obtain fresh exact-path admission for recovery."
    )
    outcome: dict[str, object] = dict(
        lifecycle_effect_outcome(
            kind="mutation_uncompensated" if changed else "zero_effect", next_action=action
        )
    )
    if successful:
        outcome.update(compensation_state="not_required", residue_state="absent")
    elif unknown:
        outcome.update(
            effect_state="unknown", compensation_state="not_attempted", residue_state="retained"
        )
    result: dict[str, object] = {
        **planned,
        "verdict": "pass" if successful else "unknown" if unknown or error else "block",
        "state": "applied"
        if successful
        else "effect_unconfirmed"
        if unknown or error
        else "partial_effect"
        if changed
        else "blocked",
        "applied": successful,
        "required_gaps": gaps,
        "next_action": action,
        "preservation": preservation,
        "effects": effects,
        "native_apply": diagnostics,
        "partial_transition": not successful and (changed or unknown),
        "lifecycle_effect_outcome": outcome,
        "recovery": {
            "automatic": False,
            "preimage_owner": "caller:CarrierEdit.before",
            "retention_condition": "until this exact effect is accepted or recovery completes",
            "restorable_paths": []
            if successful
            else [path for path, state in effects.items() if state == "postimage"],
            "contested_paths": [
                path for path, state in effects.items() if state in {"diverged", "unknown"}
            ],
            "boundary": (
                "Never replay an inverse patch over intervening bytes; "
                "reobserve and re-admit its exact inputs."
            ),
        },
    }
    if error is not None:
        result["failure"] = _failure(error)
    return result


def _failure(error: BaseException) -> dict[str, object]:
    return (
        error.evidence()
        if isinstance(error, ProcessExecutionError)
        else {"type": type(error).__name__, "message": str(error)}
    )
