"""Run one heavy local command once the host's queue admits it, and read that queue.

Every admitted run reports the command's exit status in `data.exit_status`, which the `process`
exit of `host run` exits with; a run the queue does not admit is a gap like any other. The one read
lists the declaration, the load and every live ticket, and prints no repository path.
"""

from pathlib import Path

from ethos.adapters.actor import process_actor
from ethos.adapters.gates.host_admission import host_queue
from ethos.adapters.gates.host_admission import run_admitted
from ethos.adapters.gates.host_work import claim_work_directory
from ethos.adapters.gates.proof_slot import effective_load_limit
from ethos.adapters.gates.proof_slot import host_load
from ethos.contracts.codes.gaps import repair_for
from ethos.contracts.operations.host import RunRequest
from ethos.contracts.operations.host import StatusRequest
from ethos.result import EthosResult


def run_host_command(root: Path, request: RunRequest) -> EthosResult:
    """Run the command when the host admits it, with its worker cap, and report its status.

    A run that names its work directory claims it first, so a directory that carries another
    owner's mark costs no place in the queue.
    """
    gap, next_action = "host_run_command_missing", "ethos host run -- <command...>"
    if request.command:
        owner = process_actor()
        try:
            if request.work is not None:
                claim_work_directory(root, request.work, owner=owner, operation="host.run")
            status = run_admitted(
                request.command,
                repository=root,
                operation="host.run",
                owner=owner,
                seconds=request.wait,
            )
        except ValueError as error:
            gap = str(error)
            next_action = (
                "read the queue with `ethos host status --json`, then wait"
                if gap.startswith("host_admission_contended")
                else repair_for(gap) or "repair this host's root, or declare more host slots"
            )
        else:
            return EthosResult(
                command="host run",
                verdict="block" if status else "pass",
                state="completed",
                required_gaps=(f"host_command_failed:{status}",) if status else (),
                data={"exit_status": status},
            )
    return EthosResult(
        command="host run",
        verdict="block",
        state="gapped",
        required_gaps=(gap,),
        next_action=next_action,
    )


def inspect_host_queue(root: Path, request: StatusRequest) -> EthosResult:
    """Read the declaration, the load and every live ticket, and check the guests' CPUs.

    The read removes nothing and names no repository path: another repository's holder appears
    with its operation, executable, pid and start time, never its owner mark.
    """
    try:
        queue, declaration, cpus = host_queue()
        limit, limit_source = effective_load_limit()
    except ValueError as error:
        return _read_gap(str(error))
    data: dict[str, object] = {
        "declaration": {
            "slots": declaration.slots,
            "reserved_cpus": declaration.reserved_cpus,
            "load_limit": limit,
            "limit_source": limit_source,
            "cpus": cpus,
            "worker_cap": declaration.worker_cap(cpus),
        },
        "load": host_load(),
        "queue": queue.entries(reader=root),
    }
    gaps, next_action = _reservation(data, request.guest_cpus, declaration.reserved_cpus, cpus)
    return EthosResult(
        command="host status",
        verdict="block" if gaps else "pass",
        state="observed",
        required_gaps=gaps,
        next_action=next_action,
        data=data,
    )


def _reservation(
    data: dict[str, object], guest_cpus: int | None, reserved_cpus: int, cpus: int
) -> tuple[tuple[str, ...], str]:
    """Record whether the guests' count fits the reservation, and name the repair when it does not.

    The count is the request's, read by its caller from the guests' own configuration; ETHOS
    reads no hypervisor, and the check runs on this read rather than at admission, which cannot
    know the guests. A declaration reserves fewer CPUs than the host has, so the repair is the
    value to declare where one holds the guests, and the guests' own sizes where none does.
    """
    if guest_cpus is None:
        return (), ""
    if guest_cpus < 0:
        return ("host_reservation_invalid",), "pass the guests' count as a non-negative number"
    fits, reservable = guest_cpus <= reserved_cpus, cpus - 1
    data["reservation"] = {
        "guest_cpus": guest_cpus,
        "reserved_cpus": reserved_cpus,
        "reservable_cpus": reservable,
        "fits": fits,
    }
    if fits:
        return (), ""
    next_action = (
        f"raise reserved_cpus in host.toml to {guest_cpus}"
        if guest_cpus <= reservable
        else f"resize the guests to {reservable} virtual CPUs or fewer in total: "
        f"no reserved_cpus on {cpus} holds {guest_cpus}"
    )
    return ("host_reservation_exceeded",), next_action


def _read_gap(gap: str) -> EthosResult:
    """Return the read's result when this host has no readable root or declaration."""
    return EthosResult(
        command="host status",
        verdict="block",
        state="gapped",
        required_gaps=(gap,),
        next_action="repair this host's root or its host.toml declaration",
    )
