from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any

from ethos_contracts.package_ontology import RETIRED_PRODUCT_FAMILY_TOKENS
from ethos_core.models import EvidenceClaim


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_payload(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def claims_report(root: Path) -> dict[str, object]:
    claims_dir = root / "claims"
    gaps: list[str] = []
    claims: dict[str, dict[str, object]] = {}
    claim_paths = sorted(claims_dir.glob("*.toml")) if claims_dir.exists() else []
    if not claim_paths:
        gaps.append("claims_missing")
    for path in claim_paths:
        payload = _claim_payload(path)
        claim = payload.get("claim", {})
        evidence = payload.get("evidence", {})
        claim_id = str(claim.get("id", path.stem))
        dated = evidence.get("dated")
        expected_digest = str(evidence.get("sha256", ""))
        if not dated:
            gaps.append(f"{claim_id}:evidence.dated_missing")
            continue
        if claim.get("state") == "active":
            active_identity = "\n".join(
                [
                    path.stem,
                    str(claim.get("id", "")),
                    str(claim.get("subject", "")),
                ]
            )
            for retired in RETIRED_PRODUCT_FAMILY_TOKENS:
                if retired in active_identity:
                    gaps.append(f"{claim_id}:retired_product_family:{retired}")
            evidence_ids = evidence.get("evidence_ids")
            binding = evidence.get("binding")
            verifier = evidence.get("verifier")
            summary = str(claim.get("summary", ""))
            if not isinstance(evidence_ids, list) or not evidence_ids:
                gaps.append(f"{claim_id}:evidence_ids_missing")
            if not isinstance(binding, str) or not binding:
                gaps.append(f"{claim_id}:binding_missing")
            if not isinstance(verifier, str) or not verifier:
                gaps.append(f"{claim_id}:verifier_missing")
            if isinstance(evidence_ids, list) and binding and verifier:
                try:
                    EvidenceClaim(
                        id=claim_id,
                        change_id=str(claim.get("subject", claim_id)),
                        evidence_ids=tuple(str(item) for item in evidence_ids),
                        binding="\n".join((summary, str(binding))),
                        verifier=str(verifier),
                    )
                except ValueError:
                    gaps.append(f"{claim_id}:semantic_overclaim_requires_semantic_verifier")
        evidence_path = root / str(dated)
        if not evidence_path.exists():
            gaps.append(f"{claim_id}:evidence_file_missing:{dated}")
            continue
        actual_digest = _sha256(evidence_path)
        if not expected_digest:
            gaps.append(f"{claim_id}:evidence.sha256_missing")
        elif expected_digest != actual_digest:
            gaps.append(f"{claim_id}:evidence.sha256_mismatch")
        claims[claim_id] = {
            "path": path.relative_to(root).as_posix(),
            "evidence": str(dated),
            "sha256": expected_digest,
            "actual_sha256": actual_digest,
            "state": claim.get("state", ""),
        }
    return {"ok": not gaps, "required_gaps": gaps, "claims": claims}
