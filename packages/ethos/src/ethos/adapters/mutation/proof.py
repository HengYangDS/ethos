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
import os
import shutil
from pathlib import Path
from typing import Any

_DEFAULT_PROOF_DIR = Path(".ethos") / "state" / "proof"
_TEST_PROOF_STATE_DIR_ENV = "ETHOS_TEST_PROOF_STATE_DIR"


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _pytest_state_active() -> bool:
    """Return whether the current process is running under pytest."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_XDIST_WORKER"))


def proof_state_dir(root: Path) -> Path:
    """Return the local executed-proof state directory for ``root``.

    Production proof state stays at ``.ethos/state/proof``. Test workers may
    override the physical directory through ``ETHOS_TEST_PROOF_STATE_DIR`` so
    xdist workers do not race over one shared mutable local-state projection.
    The override is ignored outside pytest.
    """
    override = os.environ.get(_TEST_PROOF_STATE_DIR_ENV, "").strip()
    if override and _pytest_state_active():
        path = Path(override).expanduser()
        return path if path.is_absolute() else root / path
    return root / _DEFAULT_PROOF_DIR


def _proof_path(root: Path, head: str) -> Path:
    return proof_state_dir(root) / f"{head}.json"


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


def _runs_prove_head(runs: object) -> bool:
    if not isinstance(runs, list) or not runs:
        return False
    trust_bearing_count = 0
    for run in runs:
        if not isinstance(run, dict):
            return False
        if run.get("verdict") != "passed":
            return False
        if run.get("trust_bearing") is True:
            trust_bearing_count += 1
            if run.get("state") != "proven":
                return False
    return trust_bearing_count > 0


def record_executed_proof(root: Path, evidence: dict[str, Any]) -> Path:
    """Persist the executed EvidenceSet body under .ethos/state/proof/<head>.json.

    Stores the FULL evidence body (not just a summary) so the record is later
    self-authenticating: its digest is recomputable from its own contents.
    """
    head = str(evidence.get("head", ""))
    proof_dir = proof_state_dir(root)
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
    path = _proof_path(root, head)
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
    # (c) Mirror `ethos prove`: every run must pass, and at least one trust-bearing
    # run must be proven. Non-trust diagnostic gates may be merely executed, but they
    # cannot fail or stand alone as promotion evidence.
    if not _runs_prove_head(evidence.get("runs")):
        return None
    return record


def _proof_carry_package(
    *, source_root: Path, target_root: Path, head: str, source_verified: bool
) -> dict[str, Any]:
    """Common proof-carry boundary fields."""
    return {
        "head": head,
        "source_root": source_root.resolve().as_posix(),
        "target_root": target_root.resolve().as_posix(),
        "truth_boundary": "local-proof-state-projection",
        "mints_proof": False,
        "same_head_only": True,
        "source_verified": source_verified,
        "target_verified": False,
    }


def carry_executed_proof_record(
    *, source_root: Path, target_root: Path, head: str
) -> dict[str, Any]:
    """Carry a verified HEAD-bound proof record between local roots.

    This is a projection of an already self-authenticating proof record, not a new
    proof minting path: the source record must verify first, and the target copy is
    re-read through the same verifier after writing.
    """
    source_record = executed_proof_record(source_root, head)
    source_path = _proof_path(source_root, head)
    target_path = _proof_path(target_root, head)
    base = _proof_carry_package(
        source_root=source_root,
        target_root=target_root,
        head=head,
        source_verified=source_record is not None,
    )
    if source_record is None:
        return {
            "ok": False,
            "state": "skipped",
            "reason": "source-proof-missing-or-invalid",
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
    except OSError as exc:
        return {
            "ok": False,
            "state": "failed",
            "reason": exc.__class__.__name__,
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    if executed_proof_record(target_root, head) is None:
        return {
            "ok": False,
            "state": "failed",
            "reason": "target-proof-invalid-after-copy",
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    return {
        "ok": True,
        "state": "carried",
        **base,
        "target_verified": True,
        "source_path": source_path.as_posix(),
        "target_path": target_path.as_posix(),
        "required_gaps": [],
    }
