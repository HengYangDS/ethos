from __future__ import annotations

import json
from pathlib import Path

from ethos_contracts.capability_parity import capability_parity_records


def parity_ledger_report() -> dict[str, object]:
    records = capability_parity_records()
    return {
        "ok": True,
        "records": records,
        "summary": {
            "capability_count": len(records),
            "unclassified_count": 0,
        },
    }


def parity_gaps_report(
    *,
    adopter: str | None = None,
    root: Path | None = None,
) -> dict[str, object]:
    records = capability_parity_records()
    evidence = _parity_evidence(root or Path.cwd(), adopter) if adopter else {}
    verified = set(evidence.get("verified_capabilities", []))
    required_gaps = [
        f"parity_pending:{record['capability']}"
        for record in records
        if record["disposition"] in {"migrate-to-product", "split"}
        and record["capability"] not in verified
    ]
    shadow = evidence.get("shadow") if isinstance(evidence.get("shadow"), dict) else {}
    if adopter and not (shadow.get("ok") is True and not shadow.get("required_gaps")):
        required_gaps.append(f"shadow_parity_pending:{adopter}")
    return {
        "ok": not required_gaps,
        "adopter": adopter or "generic",
        "required_gaps": required_gaps,
        "records": records,
        "evidence": evidence,
    }


def shadow_parity_report(*, target: Path) -> dict[str, object]:
    target = target.resolve()
    expected = (
        "ethos status --json",
        "ethos plan --changed --json",
        "ethos prove --json",
        "ethos report --json",
        "ethos quality command-surface --json",
        "ethos assistants doctor --json",
        "ethos playbooks route --changed --json",
        "ethos land --json",
        "ethos publish --json",
    )
    return {
        "ok": False,
        "state": "planned",
        "target": target.as_posix(),
        "required_gaps": [f"shadow_parity_not_executed:{target.as_posix()}"],
        "comparisons": list(expected),
        "semantic_dimensions": [
            "branch_role",
            "mutation_allowed",
            "changed_path_classification",
            "required_gates",
            "required_gaps",
            "assistant_boundary",
            "evidence_freshness",
            "land_readiness",
            "publish_readiness",
            "blocking_vs_advisory",
        ],
    }


def _parity_evidence(root: Path, adopter: str | None) -> dict[str, object]:
    if not adopter:
        return {}
    path = root / "docs" / "evidence" / "parity" / f"{adopter}-shadow.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "path": path.relative_to(root).as_posix(),
            "required_gaps": [f"parity_evidence_invalid_json:{exc.__class__.__name__}"],
            "verified_capabilities": [],
        }
    if not isinstance(payload, dict):
        return {
            "path": path.relative_to(root).as_posix(),
            "required_gaps": ["parity_evidence_not_object"],
            "verified_capabilities": [],
        }
    return {"path": path.relative_to(root).as_posix(), **payload}
