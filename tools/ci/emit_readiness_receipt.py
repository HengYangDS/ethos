"""Emit one compact hosted-CI receipt from retained ETHOS readiness JSON."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def load(path: Path) -> dict[str, object]:
    """Read one owner-command JSON result or fail with its exact path."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"invalid readiness receipt {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"invalid readiness receipt {path}: expected object")
    return value


def state(payload: dict[str, object], key: str) -> object:
    """Read a compact result field without constructing a second result model."""
    value = payload.get(key)
    return value if value is not None else ""


def main() -> None:
    """Print the bounded verdict and SHA-256 identities for retained reports."""
    audit_path, report_path, proof_path = (Path(value) for value in sys.argv[1:4])
    audit, report, proof = load(audit_path), load(report_path), load(proof_path)
    summary = proof.get("summary") if isinstance(proof.get("summary"), dict) else {}
    expected = proof.get("data") if isinstance(proof.get("data"), dict) else {}
    head = expected.get("expected_head") if isinstance(expected.get("expected_head"), dict) else {}
    ok = audit.get("ok") is True and report.get("ok") is True and proof.get("ok") is True
    print(
        json.dumps(
            {
                "kind": "ethos_hosted_readiness_receipt",
                "ok": ok,
                "audit_state": state(audit, "state"),
                "report_state": state(report, "state"),
                "proof_state": state(proof, "state"),
                "head": state(head, "current"),
                "head_matches_expected": state(head, "ok"),
                "proof_gate_count": state(summary, "gate_count"),
                "proof_evidence_digest": state(summary, "evidence_digest"),
                "reports": {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (audit_path, report_path, proof_path)
                },
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
