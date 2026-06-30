from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def trim_output(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    trimmed = len(text) - limit
    return f"{text[:limit]}\n[trimmed {trimmed} bytes]"


@dataclass(frozen=True)
class ProofRun:
    action_id: str
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "state": self.state,
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
