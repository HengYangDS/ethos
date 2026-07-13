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
    if not isinstance(config, dict):
        return _unattested()
    receipt_id = str(config.get("receipt_id") or "")
    receipt_dir = os.environ.get("ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR", "")
    if (
        not receipt_id
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", receipt_id)
        or not receipt_dir
    ):
        return _unattested()
    path, gap = _external_receipt_path(binding[0], receipt_dir, receipt_id)
    if gap:
        return {
            "state": "unattested" if gap.endswith("required") else "invalid",
            "required_gaps": [gap],
        }
    try:
        raw = path.read_bytes() if path else b""
        receipt = SemanticAttestationReceipt.model_validate(json.loads(raw))
    except (OSError, TypeError, ValueError):
        return {
            "state": "invalid",
            "required_gaps": ["semantic_attestation_receipt_invalid"],
        }
    gaps = _receipt_binding_gaps(receipt, raw, config, binding)
    return {
        "state": "attested" if not gaps else "invalid",
        "receipt_id": receipt_id,
        "reviewer_role": receipt.reviewer_role,
        "reviewer_ref": receipt.reviewer_ref,
        "mints_authority": False,
        "required_gaps": gaps,
    }


def _unattested() -> dict[str, object]:
    return {
        "state": "unattested",
        "required_gaps": ["semantic_attestation_receipt_required"],
    }


def _external_receipt_path(
    root: Path, receipt_dir_value: str, receipt_id: str
) -> tuple[Path | None, str]:
    """Resolve exactly one receipt and reject repository-local evidence."""
    receipt_dir = Path(receipt_dir_value).expanduser()
    if not receipt_dir.is_absolute():
        return None, "semantic_attestation_receipt_invalid"
    receipt_dir, root = receipt_dir.resolve(), root.resolve()
    receipt_path = (receipt_dir / f"{receipt_id}.json").resolve()
    if receipt_dir.is_relative_to(root) or receipt_path.is_relative_to(root):
        return None, "semantic_attestation_receipt_inside_repository"
    return (
        (receipt_path, "")
        if receipt_path.is_file()
        else (None, "semantic_attestation_receipt_required")
    )


def _receipt_binding_gaps(
    receipt: SemanticAttestationReceipt,
    raw: bytes,
    config: dict[str, Any],
    binding: AttestationBinding,
) -> list[str]:
    """Return candidate receipt facts that differ from the exact claim binding."""
    _, claim_id, evidence_sha256, scope_sha256, current_head = binding
    declared = (str(config.get(key) or "") for key in ("receipt_sha256", "scope_sha256", "head"))
    receipt_digest, declared_scope, declared_head = declared
    checks = (
        (
            claim_id,
            claim_id,
            receipt.claim_id,
            "semantic_attestation_claim_id_mismatch",
        ),
        (
            evidence_sha256,
            evidence_sha256,
            receipt.evidence_sha256,
            "semantic_attestation_evidence_digest_mismatch",
        ),
        (
            scope_sha256,
            declared_scope,
            receipt.scope_sha256,
            "semantic_attestation_scope_digest_mismatch",
        ),
        (
            current_head,
            declared_head,
            receipt.head,
            "semantic_attestation_head_mismatch",
        ),
    )
    gaps = [
        gap
        for actual, declared, value, gap in checks
        if not actual or actual != declared or value != actual
    ]
    if hashlib.sha256(raw).hexdigest() != receipt_digest:
        gaps.append("semantic_attestation_receipt_digest_mismatch")
    now = datetime.now(UTC)
    if (
        receipt.issued_at > now
        or receipt.valid_until <= now
        or receipt.valid_until <= receipt.issued_at
    ):
        gaps.append("semantic_attestation_receipt_stale")
    return gaps
