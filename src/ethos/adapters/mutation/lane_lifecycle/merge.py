"""Admit native merge continuation from fresh authority and exact repository state."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from typing import NoReturn

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.selection import incoming_change_gaps
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.merge.effect import apply_merge
from ethos.adapters.repo.merge.effect import recognized_merge
from ethos.adapters.repo.merge.observation import MergeObservation
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.repo.runtime.binding import runtime_binding_check
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

MergeMode = Literal["inspect", "start", "continue", "abort"]


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


def _command(root: Path, mode: str, observed: MergeObservation, token: str, message: str) -> str:
    return shlex.join(
        (
            "ethos",
            "lane",
            "refresh-base",
            "--strategy",
            "merge",
            "--mode",
            mode,
            "--expect-head",
            observed.head,
            "--expect-state",
            token,
            "--subject",
            message,
            "--root",
            str(root.resolve()),
            "--apply",
            "--authorize",
            "--json",
        )
    )


def _authority(root: Path, observed: MergeObservation) -> tuple[dict[str, object], str]:
    policy = load_branch_role_policy(root)
    if policy.role_for_branch(observed.branch) != ROLE_WORK_LANE:
        _fail("protected_root_mutation")
    authority = observe_current_authority(
        root=root, branch=observed.branch, actor=os.environ.get("ETHOS_ACTOR", ""), required=True
    )
    if authority.verdict != "pass":
        _fail(authority.reason)
    runtime = hook_runtime_binding(root)
    if runtime["required_gaps"]:
        _fail(runtime["required_gaps"][0])
    binding = runtime_binding_check(
        {"runtime_binding": runtime_binding(root, hook_binding=runtime)}
    )
    if binding["verdict"] != "pass":
        _fail(str(binding["reason"]))
    return lease_generation(authority.lease), runtime["runtime_digest"]


def _mode_gaps(root: Path, observed: MergeObservation, mode: str, incoming: str) -> list[str]:
    common = [
        gap
        for failed, gap in (
            (bool(observed.competing), "merge_competing_native_operation"),
            ("MERGE_AUTOSTASH" in observed.metadata, "merge_autostash_recovery_unsupported"),
        )
        if failed
    ]
    if common:
        return common
    if mode == "start":
        if observed.parents:
            return ["merge_already_in_progress"]
        dirty = run_git(root, "status", "--porcelain", check=False, observation=True)
        return (
            ["work_lane_dirty"]
            if dirty.returncode or dirty.stdout
            else _ignored_checkout_gaps(root, incoming)
        )
    if not observed.parents:
        return ["merge_not_in_progress"]
    if len(observed.parents) != 1:
        return ["merge_multiple_parents_unsupported"]
    return _continuation_gaps(root, observed, incoming) if mode == "continue" else []


def _ignored_checkout_gaps(root: Path, incoming: str) -> list[str]:
    """Protect ignored content where the incoming tracked tree could replace it."""
    ignored = run_git(
        root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z", observation=True
    ).stdout
    if not ignored:
        return []
    tracked = run_git(root, "ls-tree", "-r", "--name-only", "-z", incoming, observation=True).stdout
    paths = set(filter(None, tracked.split("\0")))
    directories = {str(parent) for path in paths for parent in Path(path).parents}
    collisions = [
        path
        for path in filter(None, ignored.split("\0"))
        if path in paths
        or path in directories
        or any(str(parent) in paths for parent in Path(path).parents)
    ]
    return [f"merge_ignored_content_collision:{path}" for path in sorted(collisions)]


def _continuation_gaps(root: Path, observed: MergeObservation, incoming: str) -> list[str]:
    gaps = [
        gap
        for failed, gap in (
            (observed.parents != (incoming,), "merge_candidate_changed"),
            (bool(observed.conflicts), "merge_unresolved_index"),
        )
        if failed
    ]
    if not gaps and run_git(root, "diff", "--quiet", check=False, observation=True).returncode:
        gaps.append("merge_unstaged_resolution")
    return gaps


@dataclass(frozen=True, slots=True)
class _MergeContext:
    """Bind one operation's current coordinates without persisting permissions."""

    root: Path
    observed: MergeObservation
    lease: dict[str, object]
    candidate_ref: str
    incoming: str
    runtime_digest: str

    def token(self, mode: str, message: str, native: dict[str, object] | None = None) -> str:
        return canonical_json_digest(
            {
                "native": self.observed.projection() if native is None else native,
                "lease": self.lease,
                "candidate_ref": self.candidate_ref,
                "candidate": self.incoming,
                "runtime": self.runtime_digest,
                "mode": mode,
                "subject": message,
            }
        )

    def recheck(self, *, native: bool = True) -> None:
        lease, digest = _authority(self.root, self.observed)
        if lease != self.lease:
            _fail("merge_state_stale")
        if digest != self.runtime_digest:
            _fail("merge_runtime_changed")
        if self.candidate_ref and ref_head(self.root, self.candidate_ref) != self.incoming:
            _fail("merge_candidate_changed")
        if native and observe_merge(self.root) != self.observed:
            _fail("merge_state_stale")


def _context(root: Path, observed: MergeObservation, mode: MergeMode) -> _MergeContext:
    lease, digest = _authority(root, observed)
    policy = load_branch_role_policy(root)
    candidate_ref = "" if mode == "abort" else f"refs/heads/{policy.candidate_branch}"
    incoming = ref_head(root, candidate_ref) if candidate_ref else ""
    if candidate_ref and not incoming:
        _fail("candidate_branch_missing")
    return _MergeContext(
        root,
        observed,
        lease,
        candidate_ref,
        incoming,
        digest,
    )


def _result(observed: MergeObservation, result: dict[str, object]) -> dict[str, object]:
    return lifecycle_report(
        observed.branch,
        str(result["head"]),
        str(result["state"]),
        [],
        **{name: value for name, value in result.items() if name not in {"head", "state"}},
    )


def _stage_admission(root: Path) -> dict[str, object]:
    paths = run_git(root, "diff", "--cached", "--name-only", "-z", observation=True).stdout
    admission = prewrite_guard(
        root=root,
        paths=[Path(path) for path in paths.split("\0") if path],
        editor_root=root,
        require_editor_root=True,
        staged=True,
        require_workspace=True,
    )
    official = string_mapping(admission["openspec"])
    if official.get("verdict") == "pass" and admission["verdict"] != "pass":
        _fail(next(iter(string_sequence(admission["required_gaps"])), "merge_scope_unavailable"))
    return official


def _admit_mode(context: _MergeContext, mode: MergeMode) -> None:
    if gaps := _mode_gaps(context.root, context.observed, mode, context.incoming):
        _fail(gaps[0])
    if mode != "abort":
        official = (
            _stage_admission(context.root)
            if mode == "continue"
            else openspec_governance_report(context.root, lifecycle=True)
        )
        if official.get("verdict") != "pass":
            _fail(
                next(
                    iter(string_sequence(official.get("required_gaps"))),
                    "openspec_scope_unavailable",
                )
            )
    if mode == "continue" and (
        gaps := incoming_change_gaps(context.root, str(official.get("change")), context.incoming)
    ):
        _fail(gaps[0])


def _preview(context: _MergeContext, mode: MergeMode, message: str) -> dict[str, object]:
    observed, root = context.observed, context.root
    if mode == "inspect" and observed.parents and observed.conflicts:
        return lifecycle_report(
            observed.branch,
            observed.head,
            "merge_pending",
            ["merge_unresolved_index"],
            observation=observed.projection(),
            next_action=shlex.join(
                (
                    "ethos",
                    "lane",
                    "prewrite",
                    *observed.conflicts,
                    "--editor-root",
                    str(root),
                    "--require-editor-root",
                    "--root",
                    str(root),
                    "--json",
                )
            ),
            resolution_instruction="After admission, resolve and stage the listed conflicts.",
            recovery_action=shlex.join(
                (
                    "ethos",
                    "lane",
                    "refresh-base",
                    "--strategy",
                    "merge",
                    "--mode",
                    "abort",
                    "--root",
                    str(root),
                    "--json",
                )
            ),
            user_decision_required=True,
        )
    selected = ("continue" if observed.parents else "start") if mode == "inspect" else mode
    _admit_mode(context, selected)
    if selected == "start" and is_ancestor(root, context.incoming, observed.head):
        return lifecycle_report(
            observed.branch, observed.head, "base_current", [], next_action="ethos land --json"
        )
    token = context.token(selected, message)
    return lifecycle_report(
        observed.branch,
        observed.head,
        f"ready_to_{selected}_merge",
        [],
        observation=observed.projection(),
        state_digest=token,
        incoming=context.incoming,
        next_action=_command(root, selected, observed, token, message),
        user_decision_required=True,
    )


def _execute(
    context: _MergeContext,
    mode: MergeMode,
    *,
    authorized: bool,
    expect_head: str | None,
    expect_state: str | None,
    message: str,
) -> dict[str, object]:
    root, observed = context.root, context.observed
    if not authorized:
        _fail("authorization_required")
    if mode == "inspect" or not expect_head or not expect_state:
        _fail("merge_exact_request_required")
    with FileLock(str(git_path(root, "ethos-merge.lock")), timeout=0):
        context.recheck()
        previous = recognized_merge(
            root,
            expect_state,
            mode,
            recheck=lambda: context.recheck(native=False),
            request_matches=lambda before: (
                before.get("head") == expect_head
                and context.token(mode, message, before) == expect_state
            ),
        )
        if previous is not None:
            return _result(observed, previous)
        if expect_head != observed.head:
            _fail("expect_head_mismatch")
        token = context.token(mode, message)
        if expect_state != token:
            _fail("merge_state_stale")
        _admit_mode(context, mode)
        result = apply_merge(
            root,
            observed,
            mode=mode,
            incoming=context.incoming,
            candidate_ref=context.candidate_ref,
            actor=os.environ.get("ETHOS_ACTOR", ""),
            lease=context.lease,
            message=message,
            recheck=context.recheck,
            recheck_authority=lambda: context.recheck(native=False),
            state_digest=token,
        )
    return _result(observed, result)


def merge_work_lane(
    *,
    root: Path,
    mode: MergeMode = "inspect",
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    expect_state: str | None = None,
    subject: str | None = None,
) -> dict[str, object]:
    """Preview or execute exactly one supported native merge step."""
    observed: MergeObservation | None = None
    try:
        observed = observe_merge(root)
        context = _context(root, observed, mode)
        message = subject or "chore: merge candidate contribution"
        if not apply:
            return _preview(context, mode, message)
        return _execute(
            context,
            mode,
            authorized=authorized,
            expect_head=expect_head,
            expect_state=expect_state,
            message=message,
        )
    except (OSError, ValueError, Timeout) as error:
        gap = "merge_operation_busy" if isinstance(error, Timeout) else str(error)
        unknown = isinstance(error, (OSError, ProcessExecutionError)) or "unknown" in gap
        report = lifecycle_report(
            observed.branch if observed else "",
            observed.head if observed else "",
            "blocked",
            [gap],
            next_action=_recovery_action(root, mode, gap),
            boundary="native merge continuation",
            why=gap,
            observation=observed.projection() if observed else {},
            **(
                {"process_failure": error.evidence()}
                if isinstance(error, ProcessExecutionError)
                else {}
            ),
            user_decision_required=True,
        )
        return report | {"verdict": "unknown", "state": "unknown"} if unknown else report


def _recovery_action(root: Path, mode: MergeMode, gap: str) -> str:
    """Derive a fresh coordinate request or name the exact external prerequisite."""
    if gap in {
        "authorization_required",
        "merge_exact_request_required",
        "expect_head_mismatch",
        "merge_state_stale",
        "merge_runtime_changed",
        "merge_candidate_changed",
    }:
        return shlex.join(
            (
                "ethos",
                "lane",
                "refresh-base",
                "--strategy",
                "merge",
                "--mode",
                mode,
                "--root",
                str(root.resolve()),
                "--json",
            )
        )
    if gap.startswith("merge_ignored_content_collision:"):
        return "Preserve the reported ignored content, then request a new merge preview."
    if gap == "merge_operation_busy":
        return "Wait for the current merge operation to finish, then replay the exact request."
    if gap == "merge_unstaged_resolution":
        return "Admit and stage the intended resolution, then request a fresh continue preview."
    return "Resolve the reported authority/native-state boundary; retain recovery material."
