from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from subprocess import CompletedProcess

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.resolution._shared import LEGACY_ARTIFACT_ROOT
from ethos_core.contracts.lifecycle.core import MutationRequest

type GitRunner = Callable[..., CompletedProcess[str]]


def remove_linked_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    expect_head: str | None,
    runner: GitRunner | None = None,
) -> dict[str, object]:
    runner = runner or run_git
    branch, path = str(lane.get("branch") or ""), str(lane.get("path") or "")
    expected = (expect_head or "").strip()
    gaps = _linked_lane_reobservation_gaps(branch, path, expected, runner)
    if gaps:
        return _blocked(gaps)
    removed = runner(repo, "worktree", "remove", path, check=False)
    if removed.returncode != 0:
        return _blocked(["worktree_remove_failed"], removed.stderr)
    deleted = runner(repo, "update-ref", "-d", f"refs/heads/{branch}", expected, check=False)
    if deleted.returncode != 0:
        return _blocked(["branch_delete_failed_after_worktree_removed"], deleted.stderr)
    return {}


def _linked_lane_reobservation_gaps(branch, path, expect_head, runner):
    gaps = []
    if not branch:
        gaps.append("retirement_branch_missing")
    if not expect_head:
        gaps.append("expect_head_required")
    lane_path = Path(path) if path else Path()
    if not path or not lane_path.is_dir():
        return [*gaps, "retirement_worktree_path_unavailable"]
    if any((lane_path / LEGACY_ARTIFACT_ROOT).glob("*/manifest.json")):
        return [*gaps, "lane_resolution_legacy_retention_present"]
    observations = (
        (("rev-parse", f"refs/heads/{branch}"), "retirement_ref", expect_head),
        (("rev-parse", "HEAD"), "retirement_worktree_head", expect_head),
        (("status", "--porcelain", "--untracked-files=all"), "retirement_worktree_status", ""),
    )
    for args, gap, expected in observations:
        result = runner(lane_path, *args, check=False)
        value = result.stdout.strip()
        if result.returncode != 0:
            gaps.append(f"{gap}_unavailable")
        elif expected and value != expected:
            gaps.append(f"{gap}_stale")
        elif gap == "retirement_worktree_status" and value:
            gaps.append("work_lane_dirty")
    return sorted(set(gaps))


def _blocked(gaps, stderr=""):
    report: dict[str, object] = {"ok": False, "state": "blocked", "required_gaps": gaps}
    if stderr.strip():
        report["stderr"] = stderr.strip()
    return report


def delete_json_projection_lease(repo: Path, *, subject: str) -> int:
    path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict) or not isinstance(payload.get("leases"), list):
        return 0
    rows = payload["leases"]
    kept = [row for row in rows if _projection_subject(row) != subject]
    removed = len(rows) - len(kept)
    if removed:
        payload["leases"] = kept
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return removed


def _projection_subject(row):
    return str(row.get("branch") or row.get("subject") or "") if isinstance(row, dict) else ""


def retire_authority_guidance(gaps: list[str]) -> dict[str, str]:
    if "foreign_work_lane_retire_authority_required" not in gaps:
        return {}
    return {"next_action": "set ETHOS_ACTOR to the current holder_ref or obtain handoff"}


def current_holder_ref() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip()


def lane_holder_ref(lane: dict[str, object]) -> str:
    lease = lane.get("lease")
    return str(lease.get("holder_ref") or "") if isinstance(lease, dict) else ""


def selected_holder_ref(selected: list[dict[str, object]]) -> str:
    return lane_holder_ref(selected[0]) if selected else ""


def holder_authority_gaps(selected: list[dict[str, object]]) -> list[str]:
    required = selected_holder_ref(selected)
    if not selected or (required and current_holder_ref() == required):
        return []
    return ["foreign_work_lane_retire_authority_required"]


def has_changed_paths(root: Path) -> bool:
    try:
        result = run_git(root, "status", "--porcelain", "--untracked-files=all", check=False)
        return result.returncode != 0 or bool(result.stdout.strip())
    except OSError:
        return True


def retire_mutation_binding(
    *,
    branch: str | None,
    expect_head: str | None,
    holder_ref: str = "",
    required_holder_ref: str = "",
) -> dict[str, str]:
    holder_ref = holder_ref.strip()
    binding = {"invocation_holder_ref": holder_ref, "expect_head": (expect_head or "").strip()}
    binding["ref"] = f"refs/heads/{branch}" if branch else ""
    if required_holder_ref:
        binding.update(
            holder_bound=str(bool(holder_ref)).lower(),
            invocation_source="ETHOS_ACTOR",
            required_holder_ref=required_holder_ref,
        )
    return binding


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
    binding = retire_mutation_binding(
        branch=branch,
        expect_head=expect_head,
        holder_ref=holder_ref,
        required_holder_ref=required_holder_ref,
    )
    expected_state: dict[str, object] = {"ref": binding["ref"], "head": binding["expect_head"]}
    expected_state.update(invocation_holder_ref=holder_ref, required_holder_ref=required_holder_ref)
    expected_state.update(extra_state or {})
    canonical = mutation_envelope(
        MutationRequest(command, apply, confirmed, expect_head),
        action=action,
        resource=binding["ref"] or branch or "work-lane",
        expected_state=expected_state,
        verdict="allow" if not required_gaps else "block",
        required_gaps=tuple(sorted(set(required_gaps))),
        state="ready" if not required_gaps else "blocked",
        identity_basis="holder_ref_equality" if required_holder_ref else "not_evaluated",
        evidence_boundary="current_git_lane_and_lease_observation",
        enforcement_boundary="git_ref_and_worktree_transition",
        verifier_provenance="current_runner",
    )
    return {**binding, **canonical, "legacy_binding_authoritative": False}
