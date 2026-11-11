"""Lane Lease transitions, and the handoffs that move a Lease to another holder.

Each operation takes the resolved root and its catalog request, runs the one owner of its effect
and projects that owner's report through `lease_result`, which summarizes the Lease the transition
left and, once it passes, points at the lane's status.
"""

import shlex
from pathlib import Path

from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import export_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import revoke_cross_host_source
from ethos.adapters.mutation.lane_lifecycle.lease.acquisition import reacquire_lease
from ethos.adapters.mutation.lane_lifecycle.lease.operation import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease.takeover import execute_lease_takeover
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.application.lane.result import lane_result
from ethos.contracts.coordination import CrossHostHandoffExportRequest
from ethos.contracts.coordination import CrossHostHandoffImportRequest
from ethos.contracts.coordination import CrossHostHandoffSourceRevocationRequest
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.operations.handoff import ExportRequest
from ethos.contracts.operations.handoff import ImportRequest
from ethos.contracts.operations.handoff import RevokeSourceRequest
from ethos.contracts.operations.handoff import TransferRequest
from ethos.contracts.operations.lease import ReacquireRequest
from ethos.contracts.operations.lease import RenewRequest
from ethos.contracts.operations.lease import ResumeRequest
from ethos.contracts.operations.lease import TakeoverRequest
from ethos.contracts.semantic import Attestation
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import object_sequence
from ethos.result import EthosResult

# The coordinates of a Lease generation, in the order its apply request names them.
_COORDINATES = ("generation", "expires_at", "branch", "holder_ref")


def lease_result(
    command: str, report: dict[str, object], *, next_action: str | None = None
) -> EthosResult:
    """Project one Lease transition: the Lease it left, its diagnostics and the next action.

    The next action is the given one, else the lane's status once the transition passes.
    """
    held = report.get("lease")
    lease = held if isinstance(held, dict) else {}
    summary = {"branch": report["branch"], "generation": integer(lease.get("generation"))}
    summary |= {name: str(lease.get(name) or "") for name in ("holder_ref", "expires_at")}
    diagnostics = object_sequence(report.get("diagnostics"))
    passed = "ethos lane status --json" if report["verdict"] == "pass" else ""
    return lane_result(
        command,
        report | {"next_action": passed if next_action is None else next_action},
        summary=summary,
        diagnostics=tuple(item for item in diagnostics if isinstance(item, dict)),
        data=report,
    )


def current_lease_coordinates(root: Path) -> dict[str, object]:
    """Read the current Work Lane's exact Lease coordinates through native state."""
    repo = repository_root(root)
    branch = current_branch(repo)
    lease = lease_generation(leases_by_branch(repo).get(branch, {}))
    return {"branch": branch, **{name: lease[name] for name in _COORDINATES if name != "branch"}}


def _coordinates(root: Path, request: RenewRequest | ResumeRequest) -> dict[str, object]:
    """Return the request's coordinates; a preview reads those it omits from the current Lease."""
    given = request.model_dump(include=set(_COORDINATES))
    read = None in given.values() and not request.apply
    current = current_lease_coordinates(root) if read else given
    return {name: current[name] if value is None else value for name, value in given.items()}


def _current_lease(command: str, root: Path, request: RenewRequest | ResumeRequest) -> EthosResult:
    """Run one Lease operation on all four coordinates, refusing an apply that omits any.

    A preview without a Lease generation refuses as missing, and a passing preview names the
    exact request that applies it.
    """
    given = _coordinates(root, request)
    branch, unset = given["branch"] or "", None in given.values()
    if unset or not isinstance(given["generation"], int) or given["generation"] < 1:
        gap = "lease_coordinates_required" if unset else f"work_lane_lease_missing:{branch}"
        refusal = {"verdict": "block", "state": "blocked", "branch": branch, "lease": {}}
        return lease_result(command, refusal | {"required_gaps": [gap]})
    fields = request.model_dump(exclude=set(_COORDINATES))
    operation = LeaseOperationRequest(operation=command.rpartition(" ")[2], **fields, **given)
    report = execute_lease_operation(root=root, request=operation)
    if request.apply or report["verdict"] != "pass":
        return lease_result(command, report)
    flags = [
        part for name in _COORDINATES for part in (f"--{name.replace('_', '-')}", str(given[name]))
    ]
    argv = ["ethos", *command.split(), *flags, "--root", root.as_posix(), "--apply"]
    return lease_result(command, report, next_action=shlex.join(argv))


def renew_lease(root: Path, request: RenewRequest) -> EthosResult:
    """Renew one exact unexpired local Lease generation; a preview reads the current one."""
    return _current_lease("lane lease renew", root, request)


def resume_lease(root: Path, request: ResumeRequest) -> EthosResult:
    """Resume an expired Lease for the same holder and generation; a preview reads it."""
    return _current_lease("lane lease resume", root, request)


def reacquire_lane_lease(root: Path, request: ReacquireRequest) -> EthosResult:
    """Derive or acquire missing coordination without changing retained content.

    A passing preview asks a person to decide on the acquisition it derived.
    """
    fields = request.model_dump(exclude={"expect_head"})
    report = reacquire_lease(root=root, expect_head=request.expect_head or "", **fields)
    decision = not request.apply and report["verdict"] == "pass"
    return lane_result(
        "lane lease reacquire", report | {"user_decision_required": decision}, data=report
    )


def take_over_lease(root: Path, request: TakeoverRequest) -> EthosResult:
    """Apply one accepted exact-CAS Lease takeover under the Attestation that authorizes it."""
    authorization = Attestation.model_validate_json(
        request.authorization.read_text(encoding="utf-8")
    )
    fields = request.model_dump(exclude={"authorization"})
    takeover = LeaseTakeoverRequest(authorization=authorization, **fields)
    return lease_result("lane lease takeover", execute_lease_takeover(root=root, request=takeover))


def transfer_lease(root: Path, request: TransferRequest) -> EthosResult:
    """Transfer one exact local Lease generation to a new holder."""
    transfer = LeaseOperationRequest(operation="transfer", **request.model_dump())
    return lease_result(
        "lane handoff transfer", execute_lease_operation(root=root, request=transfer)
    )


def export_handoff(root: Path, request: ExportRequest) -> EthosResult:
    """Export content-addressed Git and context state for another common directory."""
    export = CrossHostHandoffExportRequest(root=root.as_posix(), **request.model_dump())
    return lease_result("lane handoff export", export_cross_host_handoff(export))


def import_handoff(root: Path, request: ImportRequest) -> EthosResult:
    """Import a verified package and create destination-local coordination."""
    package = CrossHostHandoffImportRequest(root=root.as_posix(), **request.model_dump())
    return lease_result("lane handoff import", import_cross_host_handoff(package))


def revoke_handoff_source(root: Path, request: RevokeSourceRequest) -> EthosResult:
    """Revoke the exact source Lease after destination acknowledgement."""
    revocation = CrossHostHandoffSourceRevocationRequest(
        root=root.as_posix(), **request.model_dump()
    )
    return lease_result("lane handoff revoke-source", revoke_cross_host_source(revocation))
