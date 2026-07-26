from __future__ import annotations

from ethos.contracts.rules import RuleFactSnapshot

READY_FACT_OWNERS = {
    "worktree": "ethos-adapters.status",
    "prewrite": "ethos-adapters.prewrite",
    "openspec_state": "ethos-repository.self-audit",
    "host_readiness": "ethos-repository.self-audit",
    "projection_drift": "ethos-assistants.projections",
}


def fact(
    value: object = None,
    *,
    owner: str = "test",
    fresh: bool = True,
    available: bool = True,
) -> dict[str, object]:
    return {
        "owner": owner,
        "fresh": fresh,
        "available": available,
        "value": {} if value is None else value,
    }


def passed() -> dict[str, object]:
    return {"ok": True, "required_gaps": []}


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
            "changed_paths": fact(list(changed_paths), owner="ethos-adapters"),
            "mutation": fact(mutation, owner="ethos-cli"),
            "authorization": fact(authorized, owner="ethos-cli"),
            "actor": fact("local", owner="ethos-cli"),
            "scope": fact("repository", owner="ethos-cli"),
            **{name: fact(passed(), owner=owner) for name, owner in READY_FACT_OWNERS.items()},
        },
    )
