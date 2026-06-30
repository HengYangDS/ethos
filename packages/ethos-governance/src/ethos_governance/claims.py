from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_payload(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def claims_report(root: Path) -> dict[str, object]:
    claims_dir = root / "claims"
    gaps: list[str] = []
    claims: dict[str, dict[str, object]] = {}
    for path in sorted(claims_dir.glob("*.toml")):
        payload = _claim_payload(path)
        claim = payload.get("claim", {})
        evidence = payload.get("evidence", {})
        claim_id = str(claim.get("id", path.stem))
        dated = evidence.get("dated")
        expected_digest = str(evidence.get("sha256", ""))
        if not dated:
            gaps.append(f"{claim_id}:evidence.dated_missing")
            continue
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
