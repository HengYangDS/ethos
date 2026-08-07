from __future__ import annotations

import os
import subprocess
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.contracts.semantic import Attestation
    from ethos.repository.hooks import HookRuntimeBinding

import ethos.adapters.mutation.lane_start_rollback as rollback
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.cli import run_json
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import stage_git_paths
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import attach_worktree
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan


class LaneStartContext(NamedTuple):
    """Immutable inputs whose equality defines one lane-start saga."""

    repo: Path
    policy: BranchRolePolicy
    branch: str
    target: Path
    holder_ref: str
    base_commitment_digest: str
    candidate: dict[str, object]
    source_root: Path
    source_change_id: str
    source_commitment_path: str
    source_head: str
    source_branch: str
    run: Callable[..., subprocess.CompletedProcess[str]]
    acquire: Callable[..., dict[str, object]]


def create_lane_start_carrier(context: LaneStartContext) -> dict[str, object]:
    """Initialize detached content, acquire its Lease, then bind the lane ref."""
    candidate_head = str(context.candidate["head"])
    prepared, final_head, carrier_attestation = prepare_lane_start_carrier(context)
    if prepared is not None:
        return rollback.compensate(
            context,
            prepared,
            ownership=("detached", candidate_head, ""),
            gap="worktree_add_failed" if not os.path.lexists(context.target) else None,
        )
    try:
        binding = exact_commitment_fields(
            context.target,
            head=final_head,
            carrier=context.source_commitment_path,
            change_id=context.source_change_id,
        )
        issued_at = datetime.now(UTC)
        lease = context.acquire(
            state_database(context.repo),
            lease=LaneLease(
                lane_incarnation_id=f"lane-incarnation:{uuid.uuid4()}",
                lease_id=f"lease:{uuid.uuid4()}",
                lane_ref=context.branch,
                holder_ref=HolderRef.parse(context.holder_ref),
                epoch=1,
                issued_at=issued_at,
                renewed_at=issued_at,
                expires_at=issued_at + timedelta(days=1),
                expected_head=final_head,
                expected_tree=binding["expected_tree"],
                base_commitment_path=binding["base_commitment_path"],
                base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
                base_commitment_digest=binding["base_commitment_digest"],
                path_scope=(),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        return rollback.compensate(
            context,
            failed_process(str(exc)),
            ownership=("detached", candidate_head, ""),
            gap=str(exc),
        )
    try:
        execute_git_effect(
            context.target,
            lane_start_transition_plan(
                context,
                lease=lease,
                base_head=candidate_head,
                head=final_head,
            ),
            issuer=context.holder_ref,
        )
    except (OSError, ValueError) as error:
        return rollback.compensate(
            context,
            failed_process(str(error)),
            ownership=(
                "detached",
                candidate_head,
                final_head if ref_head(context.repo, context.branch) == final_head else "",
            ),
            lease=lease,
            gap="lane_start_ref_creation_failed",
        )
    try:
        attachment_attestation = attach_worktree(
            context.repo,
            context.target,
            branch=context.branch,
            head=final_head,
            runner=context.run,
        )
    except ValueError as error:
        return rollback.compensate(
            context,
            failed_process(str(error)),
            ownership=("detached", candidate_head, final_head),
            lease=lease,
            gap="lane_start_worktree_binding_failed",
        )
    if not rollback.exact_worktree(
        context.repo,
        target=context.target,
        branch=context.branch,
        head=final_head,
        run=context.run,
    ):
        return rollback.compensate(
            context,
            failed_process("lane_start_worktree_binding_mismatch"),
            ownership=(context.branch, final_head, final_head),
            lease=lease,
            gap="lane_start_worktree_binding_mismatch",
        )
    return complete_lane_start(
        context,
        base_head=candidate_head,
        head=final_head,
        lease=lease,
        carrier_attestation=carrier_attestation,
        attachment_attestation=attachment_attestation,
    )


def complete_lane_start(
    context: LaneStartContext,
    *,
    base_head: str,
    head: str,
    lease: dict[str, object],
    carrier_attestation: Attestation | None,
    attachment_attestation: Attestation,
) -> dict[str, object]:
    """Bind the exact hook runtime and emit the terminal lane-start receipt."""
    try:
        hook_runtime = install_hook_launchers(context.target)
    except (OSError, ValueError) as error:
        return rollback.compensate(
            context,
            failed_process(str(error)),
            ownership=(context.branch, head, head),
            lease=lease,
            gap="lane_start_hook_runtime_binding_failed",
        )
    return started_lane_report(
        context,
        base_head=base_head,
        head=head,
        lease=lease,
        carrier_attestation=carrier_attestation,
        attachment_attestation=attachment_attestation,
        hook_runtime=hook_runtime,
    )


def lane_start_transition_plan(
    context: LaneStartContext,
    *,
    lease: dict[str, object],
    base_head: str,
    head: str,
) -> TransitionPlan:
    """Compile the one exact ref creation owned by a leased lane start."""
    ref = f"refs/heads/{context.branch}"
    effect = GitEffect(
        updates={ref: GitRefUpdate(expected="0" * len(head), desired=head)},
        assertions={
            f"refs/heads/{context.policy.candidate_branch}": base_head,
            **(
                {f"refs/heads/{context.source_branch}": context.source_head}
                if context.source_branch
                else {}
            ),
        },
    )
    authority = load_lease_bound_commitment(context.target, lease=lease)
    return compile_observed_git_effect(
        context.target,
        authority,
        effect,
        head=base_head,
        prior_attestations={},
        policy={
            "operation": "lane.start",
            "branch": context.branch,
            "holder_ref": context.holder_ref,
        },
        values={"lease_generation": lease_generation(lease)},
    )


def prepare_lane_start_carrier(
    context: LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str, Attestation | None]:
    """Create and initialize the detached carrier without minting a lane ref."""
    candidate_head = str(context.candidate["head"])
    if gap := lane_start_drift_gap(
        repo=context.repo,
        candidate=context.candidate,
        source_root=context.source_root,
        source_branch=context.source_branch,
        source_head=context.source_head,
        run=context.run,
    ):
        return failed_process(gap), candidate_head, None
    try:
        add_worktree(
            context.repo,
            context.target,
            branch="detached",
            head=candidate_head,
            runner=context.run,
        )
    except ValueError as error:
        return failed_process(str(error)), candidate_head, None
    failure, final_head = initialize_lane_carrier(context)
    if failure is not None:
        return failure, final_head, None
    coordinates = exact_commitment_fields(
        context.target,
        head=final_head,
        carrier=context.source_commitment_path,
        change_id=context.source_change_id,
    )
    commitment = load_lease_bound_commitment(context.target, lease=coordinates)
    repository = load_repository_commitment(context.target, tree_ref=final_head)
    attestation = issue_native_effect(
        context.target,
        effect=NativeEffect(
            predicate="effect:git-carrier-materialization",
            operation="git.carrier.materialize",
            command=("git", "checkout/add", "write-tree", "commit-tree"),
            subject={
                "change_id": context.source_change_id,
                "carrier": context.source_commitment_path,
            },
            before={"head": candidate_head},
            after={"head": final_head},
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id=repository.id,
    )
    return None, final_head, attestation


def initialize_lane_carrier(
    context: LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Materialize and validate one deterministic initialization HEAD."""
    candidate_head = str(context.candidate["head"])
    failure, tree = (
        materialize_source_carrier(
            target=context.target,
            source_root=context.source_root,
            source_head=context.source_head,
            carrier=context.source_commitment_path,
            run=context.run,
        )
        if context.source_head
        else materialize_fresh_carrier(context)
    )
    if failure is None:
        gap = lane_start_drift_gap(
            repo=context.repo,
            candidate=context.candidate,
            source_root=context.source_root,
            source_branch=context.source_branch,
            source_head=context.source_head,
            run=context.run,
        )
        failure = failed_process(gap) if gap else None
    metadata = (
        commit_metadata(
            context.repo,
            context.source_head or candidate_head,
            run=context.run,
        )
        if failure is None
        else None
    )
    if failure is None and metadata is None:
        failure = failed_process("lane_start_source_commit_metadata_unreadable")
    final_head = candidate_head
    if failure is None:
        committed = context.run(
            context.target,
            "commit-tree",
            tree,
            "-p",
            candidate_head,
            "-m",
            f"materialize {context.source_change_id} carrier",
            check=False,
            env=metadata,
        )
        failure = committed if committed.returncode != 0 else None
        final_head = committed.stdout.strip() if failure is None else candidate_head
    if failure is None and not final_head:
        failure = failed_process("lane_start_final_head_missing")
    if failure is None:
        gap = lane_start_drift_gap(
            repo=context.repo,
            candidate=context.candidate,
            source_root=context.source_root,
            source_branch=context.source_branch,
            source_head=context.source_head,
            run=context.run,
        )
        failure = failed_process(gap) if gap else None
    return failure, final_head


def materialize_source_carrier(
    *,
    target: Path,
    source_root: Path,
    source_head: str,
    carrier: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Copy one safe source Change carrier into a detached target tree."""
    relative = str(PurePosixPath(carrier).parent)
    entries = tree_entries(source_root, source_head, relative, run=run)
    if entries is None:
        return failed_process("source_change_carrier_missing"), ""
    if any(
        mode not in {"100644", "100755"} or kind != "blob" for mode, kind, _oid, _path in entries
    ):
        return failed_process("source_change_carrier_unsafe"), ""
    restored = run(target, "checkout", source_head, "--", relative, check=False)
    if restored.returncode != 0:
        return restored, ""
    target_tree = run(target, "write-tree", check=False)
    if target_tree.returncode != 0:
        return target_tree, ""
    if tree_entries(target, target_tree.stdout.strip(), relative, run=run) != entries:
        return failed_process("source_change_carrier_materialization_mismatch"), ""
    return None, target_tree.stdout.strip()


def materialize_fresh_carrier(
    context: LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Create one official OpenSpec carrier from an explicit Commitment file."""
    command = openspec_base_command()
    if command is None:
        return failed_process("openspec_official_cli_missing"), ""
    created = run_json(
        context.target,
        command,
        ("new", "change", context.source_change_id, "--json"),
    )
    if created["exit_code"] or created["parse_error"]:
        return failed_process("openspec_change_creation_failed"), ""
    target = context.target / context.source_commitment_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(context.source_root.read_bytes())
    try:
        stage_git_paths(
            context.target,
            (str(PurePosixPath(context.source_commitment_path).parent),),
            runner=context.run,
        )
    except ValueError as error:
        return failed_process(str(error)), ""
    status = run_json(
        context.target,
        command,
        ("status", "--change", context.source_change_id, "--json"),
    )
    if (
        status["exit_code"]
        or status["parse_error"]
        or status["json"].get("changeName") != context.source_change_id
    ):
        return failed_process("openspec_change_validation_failed"), ""
    tree = context.run(context.target, "write-tree", check=False)
    return (tree if tree.returncode else None), tree.stdout.strip()


def lane_start_drift_gap(
    *,
    repo: Path,
    candidate: dict[str, object],
    source_root: Path,
    source_branch: str,
    source_head: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    """Return the first observed source or candidate movement during lane start."""
    candidate_branch = str(candidate["branch"])
    candidate_head = str(candidate["head"])
    if ref_head(repo, candidate_branch) != candidate_head:
        return "candidate_head_changed_during_lane_start"
    candidate_path = Path(str(candidate["worktree_path"]))
    if run(candidate_path, "rev-parse", "HEAD", check=False).stdout.strip() != candidate_head:
        return "candidate_worktree_head_changed_during_lane_start"
    if not source_head:
        return ""
    if ref_head(source_root, source_branch) != source_head:
        return "source_head_changed_during_lane_start"
    if run(source_root, "rev-parse", "HEAD", check=False).stdout.strip() != source_head:
        return "source_worktree_head_changed_during_lane_start"
    return ""


def failed_process(message: str) -> subprocess.CompletedProcess[str]:
    """Build one synthetic failed process for a pre-command lane-start check."""
    return subprocess.CompletedProcess(("materialize",), 1, "", message)


def commit_metadata(
    repo: Path, commit: str, *, run: Callable[..., subprocess.CompletedProcess[str]]
) -> dict[str, str] | None:
    """Return exact source metadata for a deterministic initialization commit."""
    metadata = run(
        repo,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        commit,
        check=False,
    )
    if metadata.returncode != 0:
        return None
    try:
        author, author_email, authored_at, committer, committer_email, committed_at = (
            metadata.stdout.rstrip("\n").split("\0")
        )
    except ValueError:
        return None
    return {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": authored_at,
        "GIT_COMMITTER_NAME": committer,
        "GIT_COMMITTER_EMAIL": committer_email,
        "GIT_COMMITTER_DATE": committed_at,
    }


def tree_entries(
    root: Path,
    tree_ref: str,
    relative: str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[tuple[str, str, str, str], ...] | None:
    """Return the exact blobs beneath one tree-relative carrier path."""
    completed = run(root, "ls-tree", "-r", "-z", tree_ref, "--", relative, check=False)
    if completed.returncode != 0:
        return None
    entries: list[tuple[str, str, str, str]] = []
    for record in completed.stdout.split("\0"):
        if not record:
            continue
        try:
            metadata, path = record.split("\t", 1)
            mode, kind, oid = metadata.split()
        except ValueError:
            return None
        entries.append((mode, kind, oid, path))
    return tuple(entries) or None


def started_lane_report(
    context: LaneStartContext,
    *,
    base_head: str,
    head: str,
    lease: dict[str, object],
    carrier_attestation: Attestation | None,
    attachment_attestation: Attestation,
    hook_runtime: HookRuntimeBinding,
) -> dict[str, object]:
    """Build the receipt for an exact, leased, linked Work Lane."""
    return {
        "verdict": "pass",
        "state": "started",
        "branch": context.branch,
        "base": context.policy.candidate_branch,
        "base_head": base_head,
        "head": head,
        "path": context.target.as_posix(),
        "source_root": context.source_root.resolve().as_posix() if context.source_head else "",
        "source_head": context.source_head,
        "source_change_id": context.source_change_id,
        "source_commitment_digest": context.base_commitment_digest,
        "worktree": started_worktree(branch=context.branch, path=context.target, run=context.run),
        "holder_ref": context.holder_ref,
        "base_commitment_digest": context.base_commitment_digest,
        "lease": lease,
        "carrier_attestation": (
            carrier_attestation.model_dump(mode="json") if carrier_attestation else {}
        ),
        "attachment_attestation": attachment_attestation.model_dump(mode="json"),
        "hook_runtime": hook_runtime,
        "runner_bootstrap": runner_bootstrap(context.target),
        "required_gaps": [],
    }


def started_worktree(
    *, branch: str, path: Path, run: Callable[..., subprocess.CompletedProcess[str]]
) -> dict[str, str]:
    """Return the linked-worktree receipt for a started lane."""
    head = run(path, "rev-parse", "HEAD").stdout.strip()
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def runner_bootstrap(target: Path) -> dict[str, str]:
    """Return the non-mutating source-bound runner contract for a new lane."""
    resolved = target.resolve().as_posix()
    return {
        "command": "tools/ci/scripts/run-ethos-lane.sh",
        "project_environment": ".venv",
        "environment_scope": "checkout",
        "uv_cache": "host_or_ci_content_addressed",
        "cache_scope": "host_or_ci",
        "next_action": f"cd {resolved} && tools/ci/scripts/run-ethos-lane.sh status --json",
    }
