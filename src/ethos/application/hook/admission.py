"""The hook-time reports: write admission, an introduced range, a ref update and a ref move.

Each takes the resolved root and its catalog request and projects one admission report into a
result with the report's own verdict and gaps; only a report that does not pass names a recovery.
"""

import os
from collections.abc import Callable
from pathlib import Path

from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.application.peer_identity import peer_identity_backstop
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.operations.hook import AdmitRequest
from ethos.contracts.operations.hook import CommitRangeRequest
from ethos.contracts.operations.hook import RefTransactionRequest
from ethos.contracts.operations.hook import RefUpdateRequest
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

_LANE_PREWRITE_ACTION = "ethos lane prewrite <path>"


def _report_result(
    command: str,
    report: dict[str, object],
    summary: dict[str, object],
    next_action_for: Callable[[Verdict], str],
) -> EthosResult:
    verdict = report_verdict(report)
    return EthosResult(
        command=command,
        verdict=verdict,
        state=str(report["state"]),
        summary=summary,
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_action=next_action_for(verdict),
        user_decision_required=bool(report.get("user_decision_required")),
        data=report,
    )


def _decision_action(report: dict[str, object]) -> str:
    decision = report.get("decision")
    return str(decision.get("action") or "") if isinstance(decision, dict) else ""


def admit_write(root: Path, request: AdmitRequest) -> EthosResult:
    """Evaluate hook-time write admission before a host mutates tracked files.

    The request is the admission request without its root; relative paths stay relative, since
    the admission report resolves them against the root as it resolves every target.
    """
    report = hook_admission_report(
        request=HookAdmissionRequest(root=root.as_posix(), **request.model_dump())
    )
    return _report_result(
        "hook admit",
        report,
        {"layer": report["layer"], "role": report["role"], "decision": _decision_action(report)},
        lambda verdict: (
            "" if verdict == "pass" else str(report.get("next_action") or _LANE_PREWRITE_ACTION)
        ),
    )


def admit_commit_range(root: Path, request: CommitRangeRequest) -> EthosResult:
    """Evaluate commit policy over one exact range, or check it for a protected peer's identity."""
    if request.check == "peer-identity":
        report = peer_identity_backstop(
            root,
            proposed=request.proposed_head,
            remote_head=request.remote_head,
            remote=request.remote,
            environ=os.environ,
        )
        summary = {"check": request.check, "state": str(report["state"])}
        return _report_result("hook commit-range", report, summary, lambda _verdict: "")
    report = commit_range_admission_report(
        root,
        target_ref=request.target_ref,
        proposed_head=request.proposed_head,
        remote_head=request.remote_head,
        remote_name=request.remote,
        trusted_baseline=request.trusted_baseline,
    )
    return _report_result(
        "hook commit-range",
        report,
        {key: report[key] for key in ("target_ref", "update_kind", "checked_commit_count")},
        lambda verdict: "" if verdict == "pass" else f"ethos status --root {root} --json",
    )


def admit_ref_update(root: Path, request: RefUpdateRequest) -> EthosResult:
    """Observe exact ref-role, introduced-range and OpenSpec obligations without host state."""
    report = ref_update_admission_report(
        root,
        target_ref=request.target_ref,
        proposed_head=request.proposed_head,
        remote_head=request.remote_head,
        remote_name=request.remote,
        trusted_baseline=request.trusted_baseline,
    )
    return _report_result(
        "hook ref-update",
        report,
        {key: report[key] for key in ("target_ref", "role", "policy_ref", "proposed_commit")},
        lambda _verdict: str(report["next_action"]),
    )


def admit_ref_transaction(root: Path, request: RefTransactionRequest) -> EthosResult:
    """Evaluate a local ref update before Git commits it to the ref store.

    Bound to Git's reference-transaction hook, this closes the candidate-train bypass: a raw
    `git merge --ff-only work/x dev` (or `git branch -f` or `reset`) could move the accepted
    branch directly, skipping candidate validation. Any accepted-branch advance that is not both
    candidate-contained and proof-bound is blocked, so landing and its closeout are the only way
    to advance the accepted branch.
    """
    ref, old, new, phase = request.ref_name, request.old_value, request.new_value, request.phase
    branch = ref.removeprefix("refs/heads/")
    try:
        policy = resolve_ref_move_policy(root, ref, old, new)
    except (TypeError, ValueError):
        report: dict[str, object] = {
            "verdict": "block",
            "state": "blocked",
            "phase": phase,
            "hook": "reference-transaction",
            "ref": ref,
            "branch": branch,
            "old_value": old,
            "new_value": new,
            "decision": {"action": "block", "reason": "ref_move_policy_unavailable"},
            "required_gaps": ["ref_move_policy_unavailable"],
        }
    else:
        judge = (
            work_lane_ref_transition_report
            if policy.role_for_branch(branch) == "work_lane"
            else ref_move_admission_report
        )
        report = judge(root=root, phase=phase, ref_name=ref, old_value=old, new_value=new)
    return _report_result(
        "hook ref-transaction",
        report,
        {"branch": report["branch"], "decision": _decision_action(report)},
        lambda verdict: (
            str(report.get("next_action") or "ethos land --closeout") if verdict != "pass" else ""
        ),
    )
