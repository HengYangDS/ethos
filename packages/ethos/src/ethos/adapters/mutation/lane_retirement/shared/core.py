from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos_core.contracts.lifecycle.core import MutationRequest

if TYPE_CHECKING:
    from pathlib import Path

GitRunner = Callable[..., Any]


def _run_git_adapter(root: Path, *args: str, check: bool = True) -> Any:
    return run_git(root, *args, check=check)


@dataclass(frozen=True, slots=True)
class RetirementRuntime:
    """Explicit adapter binding for Work Lane retirement operations."""

    run_git: GitRunner = _run_git_adapter


def remove_linked_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    expect_head: str | None,
    runtime: RetirementRuntime | None = None,
    runner: GitRunner | None = None,
) -> dict[str, object]:
    """Delete a lane ref head-bound, then remove its previously clean worktree."""
    git = runner or (runtime or RetirementRuntime()).run_git
    ref = f"refs/heads/{lane['branch']}"
    result = git(repo, "update-ref", "-d", ref, str(expect_head), check=False)
    if result.returncode:
        return {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["branch_delete_failed"],
            "stderr": result.stderr.strip(),
        }
    result = git(repo, "worktree", "remove", "--force", str(lane["path"]), check=False)
    if not result.returncode:
        return {}
    restore = git(repo, "update-ref", ref, str(expect_head), "0" * 40, check=False)
    return {
        "ok": False,
        "state": "blocked",
        "required_gaps": [
            "worktree_remove_failed",
            *(["branch_restore_failed"] if restore.returncode else []),
        ],
        "stderr": result.stderr.strip(),
        "rollback_stderr": restore.stderr.strip(),
    }


def delete_json_projection_lease(repo: Path, *, subject: str) -> int:
    """Remove a Work Lane lease from the JSON local-state projection."""
    path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    rows = payload.get("leases")
    if not isinstance(rows, list):
        return 0
    kept = [
        row
        for row in rows
        if not isinstance(row, dict)
        or str(row.get("branch") or row.get("subject") or "") != subject
    ]
    removed = len(rows) - len(kept)
    if not removed:
        return 0
    payload = dict(payload)
    payload["leases"] = kept
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return removed


def retire_authority_guidance(gaps: list[str]) -> dict[str, str]:
    """Return next-action guidance for holder-bound Work Lane retirement gaps."""
    if "foreign_work_lane_retire_authority_required" not in gaps:
        return {}
    return {"next_action": "set ETHOS_ACTOR to the current holder_ref or obtain handoff"}


def current_holder_ref() -> str:
    """Read the sole local holder identity input for retirement commands."""
    return os.environ.get("ETHOS_ACTOR", "").strip()


def lane_holder_ref(lane: dict[str, object]) -> str:
    """Project the holder identity from a normalized lane lease payload."""
    lease = lane.get("lease")
    return str(lease.get("holder_ref") or "") if isinstance(lease, dict) else ""


def selected_holder_ref(selected: list[dict[str, object]]) -> str:
    """Project the selected lane holder, preserving the empty-selection contract."""
    return lane_holder_ref(selected[0]) if selected else ""


def holder_authority_gaps(selected: list[dict[str, object]]) -> list[str]:
    """Reject retirement unless the invocation holder owns the selected lane."""
    if not selected:
        return []
    required = selected_holder_ref(selected)
    return (
        []
        if required and current_holder_ref() == required
        else ["foreign_work_lane_retire_authority_required"]
    )


def has_changed_paths(root: Path, *, runner: GitRunner) -> bool:
    """Fail closed when Git cannot prove the linked Work Lane is clean."""
    try:
        completed = runner(root, "status", "--porcelain", "--untracked-files=all", check=False)
    except OSError:
        return True
    return completed.returncode != 0 or bool(completed.stdout.strip())


def expected_head_gaps(head: str, expect_head: str | None) -> list[str]:
    """Require a caller-supplied compare-and-swap head."""
    expected = (expect_head or "").strip()
    if not expected:
        return ["expect_head_required"]
    return ["expect_head_mismatch"] if head and expected != head else []


def retirement_report(  # noqa: PLR0913, RUF100 - shared exact result dimensions
    *,
    command: str,
    action: str,
    branch: str | None,
    expect_head: str | None,
    apply: bool,
    confirmed: bool,
    state: str,
    gaps: list[str],
    holder_ref: str = "",
    required_holder_ref: str = "",
    extra_state: dict[str, object] | None = None,
    fields: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build one retirement result and its canonical mutation envelope."""
    required = sorted(set(gaps))
    return {
        "ok": not required,
        "state": state,
        "branch": branch or "",
        **(fields or {}),
        "mutation": retire_mutation_envelope(
            command=command,
            action=action,
            branch=branch,
            expect_head=expect_head,
            apply=apply,
            confirmed=confirmed,
            required_gaps=required,
            holder_ref=holder_ref,
            required_holder_ref=required_holder_ref,
            extra_state=extra_state,
        ),
        "required_gaps": required,
        **retire_authority_guidance(required),
    }


def retire_mutation_envelope(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    command: str,
    action: str,
    branch: str | None,
    expect_head: str | None,
    apply: bool,
    confirmed: bool,
    required_gaps: list[str],
    holder_ref: str = "",
    required_holder_ref: str = "",
    extra_state: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the canonical retirement request/decision while retaining migration hints."""
    invocation = holder_ref.strip()
    legacy_binding = {
        "invocation_holder_ref": invocation,
        "expect_head": (expect_head or "").strip(),
        "ref": f"refs/heads/{branch}" if branch else "",
        **(
            {
                "holder_bound": str(bool(invocation)).lower(),
                "invocation_source": "ETHOS_ACTOR",
                "required_holder_ref": required_holder_ref,
            }
            if required_holder_ref
            else {}
        ),
    }
    expected_state: dict[str, object] = {
        "ref": str(legacy_binding["ref"]),
        "head": str(legacy_binding["expect_head"]),
        "invocation_holder_ref": holder_ref,
        "required_holder_ref": required_holder_ref,
        **(extra_state or {}),
    }
    return {
        **legacy_binding,
        **mutation_envelope(
            MutationRequest(
                command=command,
                apply=apply,
                authorized=confirmed,
                expect_head=expect_head,
            ),
            action=action,
            resource=str(legacy_binding["ref"] or branch or "work-lane"),
            expected_state=expected_state,
            verdict="allow" if not required_gaps else "block",
            required_gaps=tuple(sorted(set(required_gaps))),
            state="ready" if not required_gaps else "blocked",
            identity_basis="holder_ref_equality" if required_holder_ref else "not_evaluated",
            evidence_boundary="current_git_lane_and_lease_observation",
            enforcement_boundary="git_ref_and_worktree_transition",
            verifier_provenance="current_runner",
        ),
        "legacy_binding_authoritative": False,
    }
