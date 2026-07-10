from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import run_git

if TYPE_CHECKING:
    from pathlib import Path


class GitRunner(Protocol):
    def __call__(self, root: Path, *args: str, check: bool = True) -> Any: ...


def _run_git_adapter(root: Path, *args: str, check: bool = True) -> Any:
    return run_git(root, *args, check=check)


@dataclass(frozen=True)
class RetirementRuntime:
    """Explicit adapter binding for Work Lane retirement operations."""

    run_git: GitRunner = _run_git_adapter


def remove_linked_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    expect_head: str | None,
    runtime: RetirementRuntime | None = None,
) -> dict[str, object]:
    """Delete a lane ref head-bound, then remove its previously clean worktree."""
    active_runtime = runtime or RetirementRuntime()
    ref = f"refs/heads/{lane['branch']}"
    delete = active_runtime.run_git(
        repo,
        "update-ref",
        "-d",
        ref,
        str(expect_head),
        check=False,
    )
    if delete.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["branch_delete_failed"],
            "stderr": delete.stderr.strip(),
        }
    remove = active_runtime.run_git(
        repo,
        "worktree",
        "remove",
        "--force",
        str(lane["path"]),
        check=False,
    )
    if remove.returncode == 0:
        return {}
    restore = active_runtime.run_git(
        repo,
        "update-ref",
        ref,
        str(expect_head),
        "0" * 40,
        check=False,
    )
    gaps = ["worktree_remove_failed"]
    if restore.returncode != 0:
        gaps.append("branch_restore_failed")
    return {
        "ok": False,
        "state": "blocked",
        "required_gaps": gaps,
        "stderr": remove.stderr.strip(),
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
    kept: list[object] = []
    removed = 0
    for row in rows:
        branch = ""
        if isinstance(row, dict):
            branch = str(row.get("branch") or row.get("subject") or "")
        if branch == subject:
            removed += 1
        else:
            kept.append(row)
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


def retire_mutation_binding(
    *,
    branch: str | None,
    expect_head: str | None,
    holder_ref: str = "",
    required_holder_ref: str = "",
) -> dict[str, str]:
    """Build the common mutation binding envelope for lane retirement commands."""
    holder_ref = holder_ref.strip()
    mutation = {
        "invocation_holder_ref": holder_ref,
        "expect_head": (expect_head or "").strip(),
        "ref": f"refs/heads/{branch}" if branch else "",
    }
    if required_holder_ref:
        mutation.update(
            {
                "holder_bound": str(bool(holder_ref)).lower(),
                "invocation_source": "ETHOS_ACTOR",
                "required_holder_ref": required_holder_ref,
            }
        )
    return mutation


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
    legacy_binding = retire_mutation_binding(
        branch=branch,
        expect_head=expect_head,
        holder_ref=holder_ref,
        required_holder_ref=required_holder_ref,
    )
    expected_state: dict[str, object] = {
        "ref": str(legacy_binding["ref"]),
        "head": str(legacy_binding["expect_head"]),
        "invocation_holder_ref": holder_ref,
        "required_holder_ref": required_holder_ref,
        **(extra_state or {}),
    }
    canonical = mutation_envelope(
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
    )
    return {**legacy_binding, **canonical, "legacy_binding_authoritative": False}
