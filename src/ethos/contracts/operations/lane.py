"""The `ethos lane` lifecycle requests and their operations.

A Work Lane is read by `status`, its write admitted by `prewrite`, started, refreshed onto the
candidate and its completed Change archived; `housekeeping` and `candidate` keep the worktrees
around it. Each apply writes only what its preview reported, and `start` and `candidate` also
write the host's worktree registry.
"""

from typing import Literal

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Authorize
from ethos.contracts.operations.declaration import Change
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import ExpectHead
from ethos.contracts.operations.declaration import Reason
from ethos.contracts.operations.declaration import Subject
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch

# The step of a merge refresh: inspect it, start it, continue it once resolved, or abort it.
MergeMode = Literal["inspect", "start", "continue", "abort"]
_HOST = "local-write host-write"
_STATE = "The state digest that the preview reported."


class StatusRequest(CommandRequest):
    """Read the Work Lane topology, its foreign lanes and the next coordination step."""


class HousekeepingRequest(CommandRequest):
    """Inventory detached worktrees below the controlled temporary roots, or remove clean ones."""

    apply: Apply = False
    authorize: Authorize = False


class CandidateRequest(CommandRequest):
    """Bootstrap the candidate worktree, refresh it from accepted, or materialize a projection."""

    path: str | None = described(None, "The candidate worktree to create, by default the policy's.")
    expect_head: ExpectHead = None
    refresh_from_accepted: bool = switch("Refresh the candidate from the accepted head.")
    materialize: bool = switch("Materialize a retained candidate projection.")
    preserved_preimage: str = described("", "The retained commit whose projection to admit.")
    retention_ref: str = described("", "The ref that retains the preserved commit.")
    reason: Reason = ""
    expect_state: str | None = described(None, _STATE)
    apply: Apply = False
    authorize: Authorize = False
    confirm_irreversible: bool = switch("Confirm dropping candidate commits accepted lacks.")


class PrewriteRequest(CommandRequest):
    """Ask whether the exact paths may be written in the worktree or the index."""

    paths: tuple[str, ...] = described(..., "The paths to write, relative to the root.")
    editor_root: str | None = described(None, "The worktree that the editor writes in.")
    require_editor_root: bool = switch("Refuse a write unless the editor root is the bound root.")
    patch: str | None = described(None, "A file holding the patch, or `-` for standard input.")
    target: Literal["worktree", "index"] = described("worktree", "Admit a worktree or index write.")
    change: Change = None


class StartRequest(CommandRequest):
    """Start, or resume, one owned Work Lane under a local lease."""

    name: str = described(..., "The lane's name.")
    path: str | None = described(None, "The worktree to create, by default the policy's.")
    base: str | None = described(None, "The exact commit to start from, by default the candidate.")
    holder_ref: str = described(..., "The holder of the lane's lease, such as `agent:<id>`.")
    apply: Apply = False


class RefreshBaseRequest(CommandRequest):
    """Refresh the current Work Lane onto the candidate by rebase, or merge a source into it."""

    expect_head: ExpectHead = None
    strategy: Literal["rebase", "merge"] = described("rebase", "Rebase onto the base, or merge.")
    source_ref: str | None = described(None, "The ref to merge instead of the candidate.")
    mode: MergeMode = described("inspect", "The merge step: inspect, start, continue or abort.")
    expect_state: str | None = described(None, _STATE)
    subject: Subject = None
    apply: Apply = False
    authorize: Authorize = False


class ArchiveChangeRequest(CommandRequest):
    """Archive one completed Change through one exact Git effect, or return its archive."""

    change: Change
    expect_head: ExpectHead
    subject: Subject = None
    compensate: bool = switch("Return the Change's unlanded archive instead.")
    apply: Apply = False


STATUS = Command(
    name="lane status",
    summary="Inspect Work Lane topology and foreign lanes.",
    request=StatusRequest,
    operations=(
        operation(
            "lane.status",
            "Report the lane topology, its foreign lanes and the next coordination step.",
            select="",
            effects="read",
        ),
    ),
)
HOUSEKEEPING = Command(
    name="lane housekeeping",
    summary="Remove only clean detached worktrees below controlled temporary roots.",
    request=HousekeepingRequest,
    operations=modes(
        "lane.housekeeping",
        "Inventory the detached worktrees below the controlled temporary roots.",
        "Remove the clean detached worktrees that are still as the inventory found them.",
        request="",
        authorization="authorize",
        destructive=True,
    ),
)
CANDIDATE = Command(
    name="lane candidate",
    summary="Bootstrap, inspect, refresh, or materialize the local candidate train.",
    request=CandidateRequest,
    operations=(
        *modes(
            "lane.candidate",
            "Report the candidate worktree that a bootstrap would create.",
            "Create the candidate worktree at the expected head.",
            select="materialize=false refresh_from_accepted=false",
            request="path expect_head",
            writes=_HOST,
        ),
        *modes(
            "lane.candidate.refresh",
            "Report whether the candidate can refresh from the accepted head.",
            "Move the candidate to the accepted head; dropping its own commits needs confirming.",
            select="refresh_from_accepted=true materialize=false",
            request="expect_head",
            authorization="confirm-irreversible",
            destructive=True,
            writes=_HOST,
        ),
        *modes(
            "lane.candidate.materialize",
            "Admit a retained candidate projection and report its state digest.",
            "Materialize the retained projection in the candidate worktree at the exact state.",
            select="materialize=true refresh_from_accepted=false",
            request="preserved_preimage retention_ref reason expect_head expect_state",
            authorization="authorize",
            writes=_HOST,
        ),
    ),
)
PREWRITE = Command(
    name="lane prewrite",
    summary="Check exact worktree or index write admission without applying it.",
    request=PrewriteRequest,
    positionals=("paths",),
    hyphen=("patch",),
    stdin="patch",
    operations=(
        operation(
            "lane.prewrite",
            "Report whether the paths may be written, and the recovery when they may not.",
            select="",
            request="paths editor_root require_editor_root patch target change",
            effects="read local-evidence-write",
            exit_kind="verdict",
        ),
    ),
)
START = Command(
    name="lane start",
    summary="Start an owned Work Lane and acquire a local lease.",
    request=StartRequest,
    positionals=("name",),
    operations=modes(
        "lane.start",
        "Report the lane, worktree and lease that a start would create or resume.",
        "Create or resume the lane's branch and worktree and acquire its lease.",
        request="name path base holder_ref",
        writes=_HOST,
    ),
)
REFRESH_BASE = Command(
    name="lane refresh-base",
    summary="Refresh the current Work Lane onto the configured candidate branch.",
    request=RefreshBaseRequest,
    operations=modes(
        "lane.refresh-base",
        "Report the refresh, or the merge step, and the exact request that applies it.",
        "Rebase the lane onto its base, or take the merge step, at the expected head.",
        request="expect_head strategy source_ref mode expect_state subject",
        authorization="authorize",
    ),
)
ARCHIVE_CHANGE = Command(
    name="lane archive-change",
    summary="Archive one completed Change, or with --compensate return its unlanded archive.",
    request=ArchiveChangeRequest,
    operations=modes(
        "lane.archive-change",
        "Report whether the Change can be archived, or its archive returned.",
        "Archive the Change, or return its archive, in one commit at the expected head.",
        request="change expect_head subject compensate",
    ),
)
LANE = (STATUS, HOUSEKEEPING, CANDIDATE, PREWRITE, START, REFRESH_BASE, ARCHIVE_CHANGE)
