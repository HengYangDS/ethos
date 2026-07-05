"""HEAD-keyed executed-proof records — tamper-evident.

R3 pinned proof to a HEAD-keyed record, but the record was forgeable: any file with
`state=="proven"` and a matching head was accepted, and the stored evidence_digest was
never re-checked — so `echo '{"head":H,"state":"proven"}' > .ethos/state/proof/H.json`
minted a proof `land` would consume.

This module makes the record SELF-AUTHENTICATING. The record stores the full evidence
body (the executed proof-runs: command, exit code, verdict per gate). `executed_proof_
record` REDERIVES the evidence digest from that stored body and rejects the record
unless (a) the recomputed digest equals the sealed digest, (b) the head matches, and
(c) every trust-bearing run actually passed. A hand-written record cannot satisfy (a)
without reproducing the real gate outputs, and cannot satisfy (c) without the gates
having actually passed — so forgery by file-authoring fails.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_PROOF_DIR = Path(".ethos") / "state" / "proof"


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _evidence_digest(body: dict[str, Any]) -> str:
    """Recompute the EvidenceSet digest over the sealed body — must match
    ethos.repository.evidence.core.EvidenceSet.from_runs exactly."""
    canonical = {
        "id": body.get("id", ""),
        "head": body.get("head", ""),
        "durability": body.get("durability", "local"),
        "runs": body.get("runs", []),
    }
    return hashlib.sha256(_stable_json(canonical).encode("utf-8")).hexdigest()


def record_executed_proof(root: Path, evidence: dict[str, Any]) -> Path:
    """Persist the executed EvidenceSet body under .ethos/state/proof/<head>.json.

    Stores the FULL evidence body (not just a summary) so the record is later
    self-authenticating: its digest is recomputable from its own contents.
    """
    head = str(evidence.get("head", ""))
    proof_dir = root / _PROOF_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{head}.json"
    record = {
        "schema_version": 2,
        "head": head,
        "state": "proven",
        "evidence": evidence,
        "evidence_digest": evidence.get("digest", ""),
    }
    path.write_text(_stable_json(record), encoding="utf-8")
    return path


def executed_proof_record(root: Path, head: str) -> dict[str, Any] | None:
    """Return the verified executed-proof record for head, or None if none is VALID.

    Validity is re-derived, never trusted: recompute the evidence digest from the
    stored body and require it to equal the sealed digest, the head to match, and every
    trust-bearing run to have passed. A forged/edited record fails these checks and is
    treated as absent (so the caller falls back to executed_proof_missing).
    """
    path = root / _PROOF_DIR / f"{head}.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(record, dict) or record.get("state") != "proven":
        return None
    if record.get("head") != head:
        return None
    evidence = record.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("head") != head:
        return None
    # (a) the digest must be reproducible from the sealed body — a forger cannot
    # fabricate it without the real gate outputs.
    sealed = str(evidence.get("digest", ""))
    if not sealed or _evidence_digest(evidence) != sealed:
        return None
    # (c) There is at least one run; every run passed; and trust-bearing runs are
    # proven. Non-trust diagnostic gates may be merely executed, but they cannot fail.
    # This mirrors `ethos prove`: verdicts gate correctness, trust-bearing proven runs
    # gate promotion authority.
    runs = evidence.get("runs")
    if not isinstance(runs, list) or not runs:
        return None
    trust_bearing_count = 0
    for run in runs:
        if not isinstance(run, dict):
            return None
        if run.get("verdict") != "passed":
            return None
        if run.get("trust_bearing") is True:
            trust_bearing_count += 1
            if run.get("state") != "proven":
                return None
    if trust_bearing_count == 0:
        return None
    return record
