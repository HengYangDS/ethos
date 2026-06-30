from __future__ import annotations

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


def parity_gaps_report(*, adopter: str | None = None) -> dict[str, object]:
    records = capability_parity_records()
    required_gaps = [
        f"parity_pending:{record['capability']}"
        for record in records
        if record["disposition"] in {"migrate-to-product", "split"}
    ]
    if adopter:
        required_gaps.append(f"shadow_parity_pending:{adopter}")
    return {
        "ok": not required_gaps,
        "adopter": adopter or "generic",
        "required_gaps": required_gaps,
        "records": records,
    }


def shadow_parity_report(*, target: Path) -> dict[str, object]:
    target = target.resolve()
    expected = (
        "ethos status --json",
        "ethos plan --changed --json",
        "ethos prove --json",
        "ethos report --json",
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
