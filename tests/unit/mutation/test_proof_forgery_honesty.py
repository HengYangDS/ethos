"""Adversarial forgery pin — the local executed-proof record is tamper-EVIDENT, not
tamper-PROOF, and the code must say so honestly.

ETHOS governs autonomous agents that run as the SAME UID as the human. That agent is the
primary governed principal, and it can write `.ethos/state/proof/<H>.json`. This test
hand-authors a WELL-FORMED "proven" record for a head whose gates never actually ran —
computing the unkeyed sha256 over its own body, exactly as a same-UID forger would — and
pins the honest truth:

  (a) the forged record IS accepted by executed_proof_record (local layer is forgeable by
      design — this documents current, correct-for-its-scope behavior, not a bug to hide);
  (b) the module docstring no longer claims "forgery by file-authoring fails";
  (c) the genuine anti-forgery guarantee is deferred to independent-identity re-execution
      (IndependentVerificationReceipt), never to this local digest.

If a future change makes the local record claim to be a prevention/enforcement guarantee
(e.g. an on-host MAC marketed as tamper-proof), (a) will change shape and this test should
be revisited deliberately — it is the tripwire for over-claiming the local trust layer.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from ethos.adapters.mutation import proof as proof_mod
from ethos.adapters.mutation.proof import _evidence_digest
from ethos.adapters.mutation.proof import _proof_path
from ethos.adapters.mutation.proof import executed_proof_record

if TYPE_CHECKING:
    from pathlib import Path


def _forge_proven_record(root: Path, head: str) -> Path:
    """Author a well-formed 'proven' record from scratch — NO gate is executed.

    Mirrors exactly what a same-UID adversary writes: every run verdict=passed, one
    trust-bearing run marked proven, and the evidence digest computed by the forger over
    their own body (the check the code performs is self-referential).
    """
    evidence: dict[str, object] = {
        "id": "forged",
        "head": head,
        "durability": "local",
        "runs": [
            {
                "action_id": "unit-architecture",
                "command": ["tools/ci/scripts/run-python-tests.sh"],
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
            },
            {
                "action_id": "ruff",
                "command": ["tools/ci/scripts/run-python-lint.sh"],
                "verdict": "passed",
                "state": "executed",
                "trust_bearing": False,
            },
        ],
    }
    evidence["digest"] = _evidence_digest(evidence)
    record = {
        "schema_version": 3,
        "head": head,
        "state": "proven",
        "evidence": evidence,
        "evidence_digest": evidence["digest"],
        "gate_policy_digest": "",  # forger leaves it blank; not checked by executed_proof_record
    }
    path = _proof_path(root, head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_hand_authored_proof_is_accepted_local_layer_is_forgeable_by_design(
    tmp_path: Path,
) -> None:
    head = "a" * 40
    # No gate ever ran; a well-formed record is authored directly.
    _forge_proven_record(tmp_path, head)

    accepted = executed_proof_record(tmp_path, head)

    # (a) HONEST TRUTH: the local layer accepts the forgery. This is tamper-evidence, not
    # tamper-proof. If this ever flips to None, the local layer has gained a genuine
    # anti-same-UID-forgery property — a deliberate change that must be reviewed, not a
    # silent regression.
    assert accepted is not None
    assert accepted["state"] == "proven"


def test_forged_digest_is_unkeyed_sha256_reproducible_by_the_forger(tmp_path: Path) -> None:
    head = "b" * 40
    path = _forge_proven_record(tmp_path, head)
    record = json.loads(path.read_text(encoding="utf-8"))
    evidence = record["evidence"]

    # The digest is a plain unkeyed sha256 over the canonical body — anyone who can write
    # the body can compute it. This is the crux of why the local layer is not a trust root.
    canonical = {
        "id": evidence["id"],
        "head": evidence["head"],
        "durability": evidence["durability"],
        "runs": evidence["runs"],
    }
    recomputed = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert recomputed == evidence["digest"]


def test_tamper_evidence_still_holds_partial_edit_is_rejected(tmp_path: Path) -> None:
    # The property the local layer DOES provide: a record edited after the fact (without
    # recomputing the digest) fails validation. Defends fat-finger / bit-rot / wrong-HEAD.
    head = "c" * 40
    path = _forge_proven_record(tmp_path, head)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["evidence"]["runs"][0]["verdict"] = "failed"  # partial edit, digest not updated
    path.write_text(json.dumps(record), encoding="utf-8")

    assert executed_proof_record(tmp_path, head) is None


def test_module_docstring_states_the_honest_trust_boundary() -> None:
    # The docstring must not resurrect the old false claim, and must name the honest scope.
    doc = proof_mod.__doc__ or ""
    assert "forgery by file-authoring fails" not in doc
    assert "tamper-PROOF" in doc  # explicitly states what it is NOT
    assert "local_readiness" in doc.lower() or "local readiness" in doc.lower()
