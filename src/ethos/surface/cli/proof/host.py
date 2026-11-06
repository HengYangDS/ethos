"""Host-only gate observation without repository proof authority."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import observe_gate_execution
from ethos.adapters.gates.runner import readiness_tier
from ethos.adapters.gates.runner import run_gate_graph
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from ethos.contracts.outcome import Outcome
from ethos.contracts.outcome import gate_outcome
from ethos.contracts.outcome import outcome_of
from ethos.contracts.proof.plan import execution_source_gaps
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


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
