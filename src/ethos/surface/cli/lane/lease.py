"""Generation-bound Lane Lease commands."""

import pathlib
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import cast

from cyclopts import App
from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.adapters.mutation.lane_lifecycle.lease.acquisition import reacquire_lease
from ethos.adapters.mutation.lane_lifecycle.lease.operation import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease.takeover import execute_lease_takeover
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.semantic import Attestation
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_app = App(name="lease", help="Generation-bound local Lane Lease lifecycle.")
lane_app.command(_app)


class LeaseCommandOptions(BaseModel):
    """Fields shared by Lease-backed commands."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    apply: bool = False
    root: RootOption | None = None
    json_output: JsonFlag = False


class LeaseProofOptions(LeaseCommandOptions):
    """The four exact Lease coordinates required by a transition."""

    generation: Annotated[int, Parameter(name="--generation")]
    expires_at: Annotated[str, Parameter(name="--expires-at")]


class DeclaredLeaseOperationOptions(LeaseProofOptions):
    """A named Lease operation bound to one branch and holder."""

    command: ClassVar[str] = ""
    operation: ClassVar[str] = ""

    branch: Annotated[str, Parameter(name="--branch")]
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]


class _RenewOptions(LeaseCommandOptions):
    """Renew the current Lease; a preview may omit the coordinates and read them."""

    command: ClassVar[str] = "lane lease renew"
    operation: ClassVar[str] = "renew"

    generation: Annotated[int | None, Parameter(name="--generation")] = None
    expires_at: Annotated[str | None, Parameter(name="--expires-at")] = None
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    holder_ref: Annotated[str | None, Parameter(name="--holder-ref")] = None
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400


class _ResumeOptions(_RenewOptions):
    command = "lane lease resume"
    operation = "resume"

    contrary_decision: Annotated[bool, Parameter(name="--contrary-decision-present")] = False


class TakeoverOptions(LeaseProofOptions):
    """An accepted authorization for one exceptional holder change."""

    branch: Annotated[str, Parameter(name="--branch")]
    source_holder_ref: Annotated[str, Parameter(name="--source-holder-ref")]
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]
    source_state: Annotated[Literal["quiesced", "source_lost"], Parameter(name="--source-state")]
    authorization: Annotated[pathlib.Path, Parameter(name="--authorization")]
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400


def emit_lease_result(
    command: str, report: dict[str, object], *, json_output: bool, next_action: str | None = None
) -> None:
    """Project one Lease transition through the command result contract."""
    lease = report.get("lease")
    summary = lease if isinstance(lease, dict) else {}
    emit(
        EthosResult(
            command=command,
            verdict=cast("Any", report["verdict"]),
            state=str(report["state"]),
            summary={
                "branch": report["branch"],
                "generation": integer(summary.get("generation")),
                "holder_ref": str(summary.get("holder_ref") or ""),
                "expires_at": str(summary.get("expires_at") or ""),
            },
            diagnostics=tuple(
                cast("dict[str, Any]", item)
                for item in object_sequence(report.get("diagnostics"))
                if isinstance(item, dict)
            ),
            required_gaps=tuple(string_sequence(report.get("required_gaps"))),
            next_action=(
                next_action
                if next_action is not None
                else "ethos lane status --json"
                if report["verdict"] == "pass"
                else ""
            ),
            data=report,
        ),
        json_output=json_output,
    )


def execute_declared_lease_operation(options: DeclaredLeaseOperationOptions) -> None:
    """Compile declared options into the minimal Lease request."""
    report = execute_lease_operation(
        root=resolve_root(options.root),
        request=LeaseOperationRequest(
            operation=options.operation,
            **options.model_dump(exclude={"root", "json_output"}),
        ),
    )
    emit_lease_result(options.command, report, json_output=options.json_output)


_COORDINATES = ("branch", "holder_ref", "generation", "expires_at")


def current_lease_coordinates(root: pathlib.Path) -> dict[str, object]:
    """Read the current Work Lane's exact Lease coordinates through native state."""
    repo = repository_root(root)
    branch = current_branch(repo)
    lease = lease_generation(leases_by_branch(repo).get(branch, {}))
    return {"branch": branch, **{name: lease[name] for name in _COORDINATES[1:]}}


def execute_current_lease_operation(options: _RenewOptions) -> None:
    """Preview on the current Lease when coordinates are omitted; apply only on all four."""
    given = {name: getattr(options, name) for name in _COORDINATES}
    root = resolve_root(options.root)
    if None in given.values():
        if options.apply:
            gap = "lease_coordinates_required"
            report = _refusal(str(given["branch"] or ""), gap)
            emit_lease_result(options.command, report, json_output=options.json_output)
            return
        current = current_lease_coordinates(root)
        given = {name: current[name] if value is None else value for name, value in given.items()}
    if not isinstance(given["generation"], int) or given["generation"] < 1:
        report = _refusal(str(given["branch"]), f"work_lane_lease_missing:{given['branch']}")
        emit_lease_result(options.command, report, json_output=options.json_output)
        return
    fields = options.model_dump(exclude={"root", "json_output", *_COORDINATES})
    request = LeaseOperationRequest(operation=options.operation, **fields, **given)
    report = execute_lease_operation(root=root, request=request)
    apply = (
        f"ethos {options.command} --generation {given['generation']}"
        f" --expires-at {given['expires_at']} --branch {given['branch']}"
        f" --holder-ref {given['holder_ref']} --root {root.as_posix()} --apply"
    )
    preview = not options.apply and report["verdict"] == "pass"
    emit_lease_result(
        options.command,
        report,
        json_output=options.json_output,
        next_action=apply if preview else None,
    )


# Every option is optional for a preview, so the commands default to these frozen instances.
_RENEW_DEFAULTS = _RenewOptions()
_RESUME_DEFAULTS = _ResumeOptions()


def _refusal(branch: str, gap: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "lease": {},
        "required_gaps": [gap],
    }


@_app.command(name="renew")
def lane_lease_renew(
    options: Annotated[_RenewOptions, Parameter(name="*")] = _RENEW_DEFAULTS,
) -> None:
    """Renew one exact unexpired local Lease generation; a preview reads the current one."""
    execute_current_lease_operation(options)


@_app.command(name="resume")
def lane_lease_resume(
    options: Annotated[_ResumeOptions, Parameter(name="*")] = _RESUME_DEFAULTS,
) -> None:
    """Resume an expired Lease for the same holder and generation; a preview reads it."""
    execute_current_lease_operation(options)


@_app.command(name="reacquire")
def lane_lease_reacquire(
    *,
    path: pathlib.Path,
    holder_ref: str,
    root: RootOption | None = None,
    expect_head: str = "",
    expect_snapshot: str = "",
    expires_at: str = "",
    authorize: bool = False,
    apply: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Derive or acquire missing coordination without changing retained content."""
    report = reacquire_lease(
        root=resolve_root(root),
        path=path,
        holder_ref=holder_ref,
        expect_head=expect_head,
        expect_snapshot=expect_snapshot,
        expires_at=expires_at,
        authorize=authorize,
        apply=apply,
    )
    emit(
        EthosResult(
            command="lane lease reacquire",
            verdict=report_verdict(report),
            state=str(report["state"]),
            required_gaps=tuple(string_sequence(report.get("required_gaps"))),
            next_action=str(report.get("next_action") or ""),
            data=report,
            user_decision_required=not apply and report["verdict"] == "pass",
        ),
        json_output=json_output,
    )


@_app.command(name="takeover")
def lane_lease_takeover(options: Annotated[TakeoverOptions, Parameter(name="*")]) -> None:
    """Apply one accepted exact-CAS Lease takeover."""
    report = execute_lease_takeover(
        root=resolve_root(options.root),
        request=LeaseTakeoverRequest(
            branch=options.branch,
            source_holder_ref=options.source_holder_ref,
            target_holder_ref=options.target_holder_ref,
            generation=options.generation,
            expires_at=options.expires_at,
            source_state=options.source_state,
            authorization=Attestation.model_validate_json(
                options.authorization.read_text(encoding="utf-8")
            ),
            ttl_seconds=options.ttl_seconds,
            apply=options.apply,
        ),
    )
    emit_lease_result("lane lease takeover", report, json_output=options.json_output)
