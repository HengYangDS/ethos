from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from ethos.quality.proof.policy import run_state_for_adapter_state

if TYPE_CHECKING:
    from pathlib import Path

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


def semantic_tree_digest(root: Path, *, head: str, relevant_paths: tuple[str, ...]) -> str:
    """Digest tracked tree entries for a declared semantic scope at one revision."""
    if not head or not relevant_paths:
        return ""
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", head, "--", *relevant_paths],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()


def trim_output(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    trimmed = len(text) - limit
    return f"{text[:limit]}\n[trimmed {trimmed} bytes]"


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
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
            message = f"invalid proof run state: {self.state}"
            raise ValueError(message)
        if self.state == "proven" and not self.trust_bearing:
            msg = "proven proof run must be trust_bearing"
            raise ValueError(msg)
        if self.trust_bearing and self.state != "proven":
            msg = "trust_bearing proof run must be proven"
            raise ValueError(msg)
        if self.state in {"accepted-risk", "waived_nonblocking"} and not self.governance_ref:
            message = f"{self.state} proof run requires governance_ref"
            raise ValueError(message)

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


@dataclass(frozen=True, slots=True)
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
        evidence_id: str,
        head: str,
        runs: tuple[ProofRun, ...],
        durability: str = "local",
    ) -> EvidenceSet:
        body = {
            "id": evidence_id,
            "head": head,
            "durability": durability,
            "runs": [run.to_dict() for run in runs],
        }
        digest = hashlib.sha256(_stable_json(body).encode("utf-8")).hexdigest()
        return cls(id=evidence_id, head=head, runs=runs, durability=durability, digest=digest)

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
