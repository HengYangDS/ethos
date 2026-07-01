from __future__ import annotations

PROOF_STATES = (
    {
        "state": "planned",
        "meaning": "gate graph is declared but not evaluated",
        "trust_bearing": False,
        "allowed_consumers": ["plan", "readiness"],
    },
    {
        "state": "readiness",
        "meaning": "static readiness is available without executed gate evidence",
        "trust_bearing": False,
        "allowed_consumers": ["plan", "doctor"],
    },
    {
        "state": "executed",
        "meaning": "a gate command ran, but the proof verdict is not yet sufficient",
        "trust_bearing": False,
        "allowed_consumers": ["diagnostics"],
    },
    {
        "state": "proven",
        "meaning": "required executed evidence passed for the current proof scope",
        "trust_bearing": True,
        "allowed_consumers": ["claim", "land", "publish", "release", "repository-governance"],
    },
    {
        "state": "blocked",
        "meaning": "a required gate or adapter prevented proof",
        "trust_bearing": False,
        "allowed_consumers": ["diagnostics"],
    },
    {
        "state": "accepted-risk",
        "meaning": "a risk was accepted through an explicit governance record",
        "trust_bearing": False,
        "allowed_consumers": ["report"],
    },
    {
        "state": "waived_nonblocking",
        "meaning": "a nonblocking gate was waived with an explicit waiver record",
        "trust_bearing": False,
        "allowed_consumers": ["report"],
    },
)


def proof_lattice() -> dict[str, object]:
    return {
        "schema_version": 1,
        "states": list(PROOF_STATES),
        "trust_consumers": [
            "claim",
            "land",
            "publish",
            "release",
            "repository-governance",
        ],
        "rules": [
            "planned and readiness states never satisfy trust-bearing consumers",
            "executed evidence must still be classified before promotion",
            "only proven evidence may satisfy claim, land, publish, release, "
            "or repository-governance",
            "waived_nonblocking and accepted-risk require explicit governance records",
        ],
    }


def run_state_for_adapter_state(
    adapter_state: str,
    *,
    trust_bearing_capable: bool = False,
) -> dict[str, object]:
    if adapter_state == "passed":
        if trust_bearing_capable:
            return {"state": "proven", "verdict": "passed", "trust_bearing": True}
        return {"state": "executed", "verdict": "passed", "trust_bearing": False}
    if adapter_state == "failed":
        return {"state": "blocked", "verdict": "failed", "trust_bearing": False}
    if adapter_state == "planned":
        return {"state": "planned", "verdict": "not_run", "trust_bearing": False}
    return {"state": "executed", "verdict": adapter_state, "trust_bearing": False}
