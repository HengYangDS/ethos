from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos_core.contracts.evidence.semantic import SemanticAttestationReceipt

type AttestationBinding = tuple[Path, str, str, str, str]


def semantic_attestation(
    evidence: dict[str, Any], binding: AttestationBinding
) -> dict[str, object]:
    """Validate an optional external receipt without minting any authority."""
    if evidence.get("verifier") != "semantic_attested":
        return {}
    config = evidence.get("semantic_attestation")
    receipt_id = str(config.get("receipt_id") or "") if isinstance(config, dict) else ""
    receipt_dir = os.environ.get("ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR", "")
    if (
        not receipt_id
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", receipt_id)
        or not receipt_dir
    ):
        return _result("unattested", "semantic_attestation_receipt_required")
    receipt_root = Path(receipt_dir).expanduser()
    if not receipt_root.is_absolute():
        return _result("invalid", "semantic_attestation_receipt_invalid")
    receipt_root, root = receipt_root.resolve(), binding[0].resolve()
    path = (receipt_root / f"{receipt_id}.json").resolve()
    if receipt_root.is_relative_to(root) or path.is_relative_to(root):
        return _result("invalid", "semantic_attestation_receipt_inside_repository")
    if not path.is_file():
        return _result("unattested", "semantic_attestation_receipt_required")
    try:
        raw = path.read_bytes()
        receipt = SemanticAttestationReceipt.model_validate(json.loads(raw))
    except (OSError, TypeError, ValueError):
        return _result("invalid", "semantic_attestation_receipt_invalid")
    gaps = _receipt_binding_gaps(receipt, raw, config or {}, binding)
    return {
        "state": "attested" if not gaps else "invalid",
        "receipt_id": receipt_id,
        "reviewer_role": receipt.reviewer_role,
        "reviewer_ref": receipt.reviewer_ref,
        "mints_authority": False,
        "required_gaps": gaps,
    }


def _result(state: str, gap: str) -> dict[str, object]:
    return {"state": state, "required_gaps": [gap]}


def _receipt_binding_gaps(
    receipt: SemanticAttestationReceipt,
    raw: bytes,
    config: dict[str, Any],
    binding: AttestationBinding,
) -> list[str]:
    _, claim_id, evidence_sha256, scope_sha256, current_head = binding
    declared = (str(config.get(key) or "") for key in ("receipt_sha256", "scope_sha256", "head"))
    receipt_digest, declared_scope, declared_head = declared
    actuals = (claim_id, evidence_sha256, scope_sha256, current_head)
    declared_values = (claim_id, evidence_sha256, declared_scope, declared_head)
    received = (receipt.claim_id, receipt.evidence_sha256, receipt.scope_sha256, receipt.head)
    gaps = [
        gap
        for actual, declared, value, gap in zip(
            actuals,
            declared_values,
            received,
            (
                "semantic_attestation_claim_id_mismatch",
                "semantic_attestation_evidence_digest_mismatch",
                "semantic_attestation_scope_digest_mismatch",
                "semantic_attestation_head_mismatch",
            ),
            strict=True,
        )
        if not actual or actual != declared or value != actual
    ]
    if hashlib.sha256(raw).hexdigest() != receipt_digest:
        gaps.append("semantic_attestation_receipt_digest_mismatch")
    now = datetime.now(UTC)
    if receipt.issued_at > now or receipt.valid_until <= max(now, receipt.issued_at):
        gaps.append("semantic_attestation_receipt_stale")
    return gaps
