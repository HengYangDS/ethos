from __future__ import annotations

from ethos_core.contracts.rules import RuleFactSnapshot


def complete_snapshot(
    *,
    phase: str = "plan",
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
) -> RuleFactSnapshot:
    return RuleFactSnapshot(
        phase=phase,
        head="untracked",
        facts={
            "changed_paths": {
                "owner": "ethos-adapters",
                "fresh": True,
                "available": True,
                "value": list(changed_paths),
            },
            "mutation": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": mutation,
            },
            "authorization": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": authorized,
            },
            "actor": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": "local",
            },
            "scope": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": "repository",
            },
            "worktree": {
                "owner": "ethos-adapters.status",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "prewrite": {
                "owner": "ethos-adapters.prewrite",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "openspec_state": {
                "owner": "ethos-repository.self-audit",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "claim_state": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "evidence_freshness": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "stale": []},
            },
            "host_readiness": {
                "owner": "ethos-repository.self-audit",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "command_registry": {
                "owner": "ethos-repository.command-registry",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "projection_drift": {
                "owner": "ethos-assistants.projections",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
        },
    )
