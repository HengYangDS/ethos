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
from ethos.adapters.mutation.lane_lifecycle.merge_actions import merge_command
from ethos.adapters.mutation.lane_lifecycle.merge_actions import merge_recovery_action
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.selection import incoming_change_gaps
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object_sandbox import isolated_git_objects
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.merge.effect import apply_merge
from ethos.adapters.repo.merge.effect import prepared_merge
from ethos.adapters.repo.merge.effect import recognized_merge
from ethos.adapters.repo.merge.observation import MergeObservation
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.repo.runtime.binding import runtime_binding_check
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

MergeMode = Literal["inspect", "start", "continue", "abort"]


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


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
    return _continuation_gaps(root, observed) if mode == "continue" else []


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


def _continuation_gaps(root: Path, observed: MergeObservation) -> list[str]:
    gaps = ["merge_unresolved_index"] if observed.conflicts else []
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
    source_head: str
    explicit_source_ref: str | None = None

    def request(
        self,
        mode: str,
        message: str,
        *,
        runtime: str | None = None,
        native: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Bind original request semantics independently of later runtime selection."""
        parents = (
            self.observed.parents if native is None else string_sequence(native.get("parents"))
        )
        incoming = parents[0] if mode == "continue" and len(parents) == 1 else self.incoming
        return {
            "lease": self.lease,
            **(
                {
                    "candidate_ref": self.candidate_ref,
                    "candidate": incoming,
                    "source_head": self.source_head,
                }
                if self.candidate_ref
                else {}
            ),
            "runtime": self.runtime_digest if runtime is None else runtime,
            "mode": mode,
            "subject": message,
        }

    def token(self, mode: str, message: str, native: dict[str, object] | None = None) -> str:
        return canonical_json_digest(
            {
                "native": self.observed.projection() if native is None else native,
                **self.request(mode, message, native=native),
            }
        )

    def recheck(self, *, native: bool = True) -> None:
        lease, digest = _authority(self.root, self.observed)
        if lease != self.lease:
            _fail("merge_state_stale")
        if digest != self.runtime_digest:
            _fail("merge_runtime_changed")
        if self.candidate_ref and ref_head(self.root, self.candidate_ref) != self.source_head:
            _fail("merge_candidate_changed")
        if native and observe_merge(self.root) != self.observed:
            _fail("merge_state_stale")


def _context(
    root: Path,
    observed: MergeObservation,
    mode: MergeMode,
    source_ref: str | None = None,
    prepared: Attestation | None = None,
) -> _MergeContext:
    lease, digest = _authority(root, observed)
    policy = load_branch_role_policy(root)
    if source_ref is not None and (
        mode == "abort"
        or not source_ref.startswith("refs/heads/")
        or run_git(root, "check-ref-format", source_ref, check=False, observation=True).returncode
        or policy.role_for_branch(source_ref.removeprefix("refs/heads/")) != ROLE_WORK_LANE
    ):
        _fail("merge_source_ref_invalid")
    selected = ("continue" if observed.parents else "start") if mode == "inspect" else mode
    candidate_ref = (
        ""
        if selected == "abort"
        else source_ref or (f"refs/heads/{policy.candidate_branch}" if selected == "start" else "")
    )
    source_head = ref_head(root, candidate_ref) if candidate_ref else ""
    if candidate_ref and not source_head:
        _fail("merge_source_ref_missing" if source_ref is not None else "candidate_branch_missing")
    incoming = source_head or (observed.parents[0] if len(observed.parents) == 1 else "")
    if source_ref is not None and observed.parents:
        if len(observed.parents) != 1 or not is_ancestor(root, observed.parents[0], source_head):
            _fail("merge_source_ref_changed")
        incoming = observed.parents[0]
    if prepared is not None:
        incoming = str(prepared.payload.body["observation"]["parents"][0])
    return _MergeContext(
        root, observed, lease, candidate_ref, incoming, digest, source_head, source_ref
    )


def _result(observed: MergeObservation, result: dict[str, object]) -> dict[str, object]:
    return lifecycle_report(
        observed.branch,
        str(result["head"]),
        str(result["state"]),
        [],
        **{name: value for name, value in result.items() if name not in {"head", "state"}},
    )


def _stage_admission(root: Path, head: str, incoming: str) -> dict[str, object]:
    """Separate newly authored resolution from the parents' native composition."""
    index = run_git(root, "write-tree", check=False, observation=True)
    if index.returncode:
        _fail("staged_tree_unavailable")
    with isolated_git_objects(root) as git:
        merged = git("merge-tree", "--write-tree", head, incoming)
        baseline = merged.stdout.partition("\n")[0]
        if merged.returncode not in (0, 1) or not baseline:
            _fail("merge_authoring_observation_unavailable")
        verified = git("rev-parse", "--verify", f"{baseline}^{{tree}}")
        if verified.returncode or verified.stdout.strip() != baseline:
            _fail("merge_authoring_observation_unavailable")
        delta = git("diff", "--no-renames", "--name-only", "-z", baseline, index.stdout.strip())
        if delta.returncode:
            _fail("merge_authoring_observation_unavailable")
        paths = tuple(filter(None, delta.stdout.split("\0")))
        intent = git(
            "diff",
            "--no-renames",
            "--name-only",
            "-z",
            incoming,
            index.stdout.strip(),
            "--",
            "openspec/changes",
        )
        if intent.returncode:
            _fail("merge_authoring_observation_unavailable")
        authored_intent = set(filter(None, intent.stdout.split("\0")))
        paths = tuple(
            path
            for path in paths
            if not path.startswith("openspec/changes/") or path in authored_intent
        )
    admission = prewrite_guard(
        root=root,
        paths=[Path(path) for path in paths],
        editor_root=root,
        require_editor_root=True,
        staged=True,
        require_workspace=True,
    )
    official = string_mapping(admission["openspec"])
    if gaps := incoming_change_gaps(root, str(official.get("change")), incoming, paths):
        _fail(gaps[0])
    if official.get("verdict") == "pass" and admission["verdict"] != "pass":
        _fail(next(iter(string_sequence(admission["required_gaps"])), "merge_scope_unavailable"))
    return official


def _admit_mode(context: _MergeContext, mode: MergeMode) -> None:
    if gaps := _mode_gaps(context.root, context.observed, mode, context.incoming):
        _fail(gaps[0])
    if mode != "abort":
        official = (
            _stage_admission(context.root, context.observed.head, context.incoming)
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


def _preview(
    context: _MergeContext, mode: MergeMode, message: str, prepared: Attestation | None
) -> dict[str, object]:
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
    head = observed.head
    if prepared is not None:
        body = prepared.payload.body
        request = body["request"]
        if request != context.request("continue", message, runtime=str(request["runtime"])):
            _fail("merge_request_stale")
        head, token, selected = (
            str(body["observation"]["head"]),
            str(body["subject"]["state_digest"]),
            "continue",
        )
        context.recheck()
    else:
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
        next_action=merge_command(
            root, selected, head, token, message, context.explicit_source_ref
        ),
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
            request_matches=lambda before, request: (
                before.get("head") == expect_head
                and request
                == context.request(mode, message, runtime=str(request["runtime"]), native=before)
                and canonical_json_digest({"native": before, **request}) == expect_state
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
            source_head=context.source_head,
            actor=os.environ.get("ETHOS_ACTOR", ""),
            lease=context.lease,
            message=message,
            recheck=context.recheck,
            recheck_authority=lambda: context.recheck(native=False),
            state_digest=token,
            request=context.request(mode, message),
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
    source_ref: str | None = None,
) -> dict[str, object]:
    """Preview or execute exactly one supported native merge step."""
    observed: MergeObservation | None = None
    try:
        observed = observe_merge(root)
        prepared = (
            prepared_merge(root, observed)
            if not apply and mode in {"inspect", "continue"}
            else None
        )
        if prepared is not None:
            request = prepared.payload.body["request"]
            source_ref = source_ref or (
                str(request["candidate_ref"]) if request.get("candidate_ref") else None
            )
            subject = subject or str(request["subject"])
        context = _context(
            root, observed, "continue" if prepared is not None else mode, source_ref, prepared
        )
        message = subject or "chore: merge candidate contribution"
        if not apply:
            return _preview(context, mode, message, prepared)
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
            next_action=merge_recovery_action(root, mode, gap),
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
