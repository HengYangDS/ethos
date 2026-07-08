from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ethos_core.quality.proof.policy import run_state_for_adapter_state

PROOF_RUN_STATES = {
    "planned",
    "readiness",
    "executed",
    "proven",
    "blocked",
    "accepted-risk",
    "waived_nonblocking",
}


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def trim_output(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    trimmed = len(text) - limit
    return f"{text[:limit]}\n[trimmed {trimmed} bytes]"


@dataclass(frozen=True)
class AdapterProofResult:
    action_id: str
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    adapter_state: str
    evidence_class: str = "proof"
    trust_bearing: bool = False
    diagnostics: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ProofRun:
    action_id: str
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    state: str
    evidence_class: str = "proof"
    verdict: str = "not_run"
    trust_bearing: bool = False
    diagnostics: tuple[dict[str, Any], ...] = ()
    governance_ref: str = ""

    def __post_init__(self) -> None:
        if self.state not in PROOF_RUN_STATES:
            raise ValueError(f"invalid proof run state: {self.state}")
        if self.state == "proven" and not self.trust_bearing:
            raise ValueError("proven proof run must be trust_bearing")
        if self.trust_bearing and self.state != "proven":
            raise ValueError("trust_bearing proof run must be proven")
        if self.state in {"accepted-risk", "waived_nonblocking"} and not self.governance_ref:
            raise ValueError(f"{self.state} proof run requires governance_ref")

    @classmethod
    def from_adapter_result(cls, result: AdapterProofResult) -> ProofRun:
        classification = run_state_for_adapter_state(
            result.adapter_state,
            trust_bearing_capable=result.trust_bearing,
        )
        return cls(
            action_id=result.action_id,
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            state=str(classification["state"]),
            evidence_class=result.evidence_class,
            verdict=str(classification["verdict"]),
            trust_bearing=bool(classification["trust_bearing"]),
            diagnostics=result.diagnostics,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "state": self.state,
            "evidence_class": self.evidence_class,
            "verdict": self.verdict,
            "trust_bearing": self.trust_bearing,
            "diagnostics": list(self.diagnostics),
            "governance_ref": self.governance_ref,
        }


@dataclass(frozen=True)
class EvidenceSet:
    id: str
    head: str
    runs: tuple[ProofRun, ...]
    durability: str = "local"
    digest: str = ""

    @classmethod
    def from_runs(
        cls,
        *,
        id: str,
        head: str,
        runs: tuple[ProofRun, ...],
        durability: str = "local",
    ) -> EvidenceSet:
        body = {
            "id": id,
            "head": head,
            "durability": durability,
            "runs": [run.to_dict() for run in runs],
        }
        digest = hashlib.sha256(_stable_json(body).encode("utf-8")).hexdigest()
        return cls(id=id, head=head, runs=runs, durability=durability, digest=digest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "head": self.head,
            "durability": self.durability,
            "digest": self.digest,
            "runs": [run.to_dict() for run in self.runs],
        }


def provenance_envelope(evidence: EvidenceSet) -> dict[str, Any]:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "predicateType": "https://ethos.local/provenance/ethos-provenance/v1",
        "subject": [
            {
                "name": evidence.id,
                "digest": {"sha256": evidence.digest},
            }
        ],
        "predicate": {
            "builder": {"id": "ethos"},
            "head": evidence.head,
            "durability": evidence.durability,
            "runs": [run.to_dict() for run in evidence.runs],
        },
    }
