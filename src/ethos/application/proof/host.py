"""Host-only gate observation without repository proof authority."""

from __future__ import annotations

import os
from contextlib import ExitStack
from dataclasses import asdict
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.actor import process_actor
from ethos.adapters.gates.host_admission import admitted_host_work
from ethos.adapters.gates.host_admission import exported
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import readiness_tier
from ethos.adapters.gates.runner import run_gate_graph
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from ethos.contracts.outcome import Outcome
from ethos.contracts.outcome import OutcomeError
from ethos.contracts.outcome import gate_outcome
from ethos.contracts.outcome import outcome_of
from ethos.contracts.proof.plan import execution_source_gaps
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import PlanNode
    from ethos.repository.policy.gates import ResolvedGatePolicy


def host_probe_boundary(*, host: bool, probe: bool) -> dict[str, object]:
    """Describe optional host-readiness flags without minting proof truth."""
    return {
        "requested": host or probe,
        "host": host,
        "probe": probe,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "not_requested" if not (host or probe) else "boundary_recorded",
    }


def observe_gate_execution(
    root: Path,
    *,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    expect_head: str | None = None,
) -> dict[str, Any]:
    """Execute one source-bound quality observation without granting mutation authority."""
    head = current_tracked_head(root)
    exact = full or expect_head is not None
    tree = current_tree(root, head) if head and exact else ""
    source: dict[str, str] = {}
    checks: list[dict[str, Any]] = []
    gaps = ["proof_head_missing"] if not head else []
    after = failure = Outcome()
    if expect_head is not None and expect_head != head:
        gaps.append("expected_head_mismatch")
    policy = None
    admission: dict[str, object] | None = None
    not_run: list[str] = []

    def resolve() -> ResolvedGatePolicy:
        return resolve_gate_policy(
            root,
            tree_ref=head,
            gate_ids=gate_ids,
            full=full,
            selected_obligations=bool(gate_ids) and not full,
        )

    try:
        policy = resolve() if not gaps else None
        if policy is not None:
            gaps.extend(policy.gaps)
        if not gaps and exact:
            source = observe_execution_source(root, head, tree)
            gaps.extend(
                execution_source_gaps({"tree": tree, "values": {"execution_source": source}})
            )
        if not gaps and policy is not None:
            admission, results = _admitted_gates(root, policy, LocalGateRunner(candidate=not exact))
            checks = [asdict(result) for result in results]
            consequences = policy.result_gaps(checks, source_tree=tree)
            after = Outcome.of(gate_outcome(checks).verdict, *consequences)
            if exact and (
                current_tracked_head(root) != head
                or observe_execution_source(root, head, tree) != source
                or resolve().digest != policy.digest
            ):
                gaps.append("proof_execution_source_changed")
    except ValueError as error:
        failure = outcome_of(error)
        checks, not_run = _kept(error, checks)
    observed = Outcome.of("pass", *gaps).combine(gate_outcome(checks), after, failure)
    return {
        "verdict": observed.verdict,
        "head": head,
        "policy_digest": policy.digest if policy is not None else "",
        "execution_source": source,
        "executed": bool(checks),
        "checks": checks,
        "not_run": not_run,
        "required_gaps": list(observed.gaps),
        "diagnostics": list(observed.causes),
        **({"admission": admission} if admission is not None else {}),
    }


class _AdmissionRefusedError(OutcomeError):
    """A refused host admission, with the readiness results that ran and the gates that did not."""

    def __init__(
        self, refused: ValueError, ran: tuple[ActionRunResult, ...], not_run: tuple[str, ...]
    ) -> None:
        super().__init__(outcome_of(refused))
        self.ran = ran
        self.not_run = not_run


def _kept(
    error: ValueError, checks: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return the checks a failure keeps and the gates it names as not run.

    A refused admission keeps the readiness results that ran before it and names every other gate.
    Any other failure keeps the checks it had and names none: what it ran is not known.
    """
    if isinstance(error, _AdmissionRefusedError):
        return [asdict(result) for result in error.ran], list(error.not_run)
    return checks, []


def _admitted_gates(
    root: Path, policy: ResolvedGatePolicy, runner: LocalGateRunner
) -> tuple[dict[str, object] | None, tuple[ActionRunResult, ...]]:
    """Run the readiness tier first, then the rest under one host ticket.

    Readiness gates are static checks of a committed tree, so they run without waiting; the test
    and package gates that follow hold the host ticket, with its token and worker cap exported,
    exactly as a caller gets today by wrapping the proof in `ethos host run`. A plan of readiness
    gates alone never waits, and a live admission is joined rather than taken again. A refused
    admission raises with the readiness results, so the result keeps them and names the rest.
    """
    nodes = policy.nodes
    tier = set(readiness_tier(nodes, policy.registry))
    capacity = max(1, os.cpu_count() or 1)

    def graph(
        run: tuple[PlanNode, ...], settled: dict[str, ActionRunResult] | None = None
    ) -> tuple[ActionRunResult, ...]:
        return run_gate_graph(
            runner,
            run,
            policy.registry,
            root=root,
            capacity=capacity,
            parallel=True,
            settled=settled,
        )

    readiness = graph(tuple(node for node in nodes if node.id in tier))
    if all(node.id in tier for node in nodes):
        return None, readiness
    with ExitStack() as held:
        try:
            work = held.enter_context(
                admitted_host_work(
                    root,
                    "ethos prove",
                    operation="proof.host",
                    owner=process_actor(),
                )
            )
        except ValueError as refused:
            not_run = tuple(node.id for node in nodes if node.id not in tier)
            raise _AdmissionRefusedError(refused, readiness, not_run) from refused
        settled = {result.action_id: result for result in readiness}
        with exported(work.environment):
            results = graph(nodes, settled)
    return {"waited_seconds": work.waited_seconds, "joined": work.joined}, results


def host_gate_observation(
    *, repo: Path, gate_ids: tuple[str, ...], expect_head: str | None, full: bool = False
) -> EthosResult:
    """Execute focused gates without repository lifecycle or Attestation authority."""
    observed = observe_gate_execution(repo, gate_ids=gate_ids, full=full, expect_head=expect_head)
    checks, required_gaps = observed["checks"], tuple(observed["required_gaps"])
    current_head, verdict = observed["head"], observed["verdict"]
    return EthosResult(
        command="prove",
        verdict=verdict,
        state="observed" if verdict == "pass" else "gapped",
        summary={
            "boundary": "host",
            "gate_count": len(checks),
            "proof_attestation_issued": False,
        },
        diagnostics=tuple(observed["diagnostics"]),
        required_gaps=required_gaps,
        next_action="repair the selected host gate" if required_gaps else "",
        data={
            "executed": bool(checks),
            "execution_source": observed["execution_source"],
            "policy_digest": observed["policy_digest"],
            "boundary": "host",
            "host_probe": host_probe_boundary(host=True, probe=False),
            "checks": checks,
            **({"admission": observed["admission"]} if "admission" in observed else {}),
            **({"not_run": observed["not_run"]} if observed["not_run"] else {}),
            "attestation": {},
            "expected_head": {
                "expected": expect_head or "",
                "current": current_head,
                "matches": expect_head is None or expect_head == current_head,
            },
        },
    )


def readiness_observation(*, repo: Path, expect_head: str | None) -> EthosResult:
    """Run the full plan's readiness tier alone; the gates after it are named, never passed."""
    head = current_tracked_head(repo)
    tree = current_tree(repo, head) if head else ""
    gaps = ["proof_head_missing"] if not head else []
    if expect_head is not None and expect_head != head:
        gaps.append("expected_head_mismatch")
    checks: list[dict[str, object]] = []
    not_run: list[str] = []
    source: dict[str, str] = {}
    digest = ""
    failure = Outcome()
    try:
        if not gaps:
            policy = resolve_gate_policy(repo, tree_ref=head, full=True)
            digest = policy.digest
            gaps.extend(policy.gaps)
            tier = set(readiness_tier(policy.nodes, policy.registry))
            not_run = [node.id for node in policy.nodes if node.id not in tier]
            source = observe_execution_source(repo, head, tree)
            gaps.extend(
                execution_source_gaps({"tree": tree, "values": {"execution_source": source}})
            )
            if not gaps:
                results = run_gate_graph(
                    LocalGateRunner(),
                    tuple(node for node in policy.nodes if node.id in tier),
                    policy.registry,
                    root=repo,
                    capacity=max(1, os.cpu_count() or 1),
                    parallel=True,
                )
                checks = [asdict(result) for result in results]
                if (
                    current_tracked_head(repo) != head
                    or observe_execution_source(repo, head, tree) != source
                ):
                    gaps.append("proof_execution_source_changed")
    except ValueError as error:
        failure = outcome_of(error)
    observed = Outcome.of("pass", *gaps).combine(gate_outcome(checks), failure)
    verdict = observed.verdict
    return EthosResult(
        command="prove",
        verdict=verdict,
        state="observed" if verdict == "pass" else "gapped",
        summary={
            "boundary": "readiness",
            "gate_count": len(checks),
            "not_run": not_run,
            "proof_attestation_issued": False,
        },
        diagnostics=tuple(observed.causes),
        required_gaps=tuple(observed.gaps),
        next_action="repair the failed readiness gate"
        if observed.gaps
        else "ethos prove --full --execute",
        data={
            "executed": bool(checks),
            "execution_source": source,
            "policy_digest": digest,
            "boundary": "readiness",
            "checks": checks,
            "not_run": not_run,
            "attestation": {},
        },
    )
