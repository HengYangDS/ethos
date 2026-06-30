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
    pending_packages = [
        _pending_package(record)
        for record in records
        if record["disposition"] in {"migrate-to-product", "split"}
    ]
    if adopter:
        pending_packages.append(_shadow_pending_package(adopter))
    required_gaps = [str(package["gap"]) for package in pending_packages]
    return {
        "ok": not required_gaps,
        "adopter": adopter or "generic",
        "required_gaps": required_gaps,
        "pending_packages": pending_packages,
        "records": records,
    }


def _pending_package(record: dict[str, object]) -> dict[str, object]:
    return {
        "gap": f"parity_pending:{record['capability']}",
        "capability": record["capability"],
        "source_location": record["source_location"],
        "target_home": record["target_home"],
        "disposition": record["disposition"],
        "required_tests": list(record["required_tests"]),
        "parity_criterion": record["parity_criterion"],
        "rollback_impact": record["rollback_impact"],
    }


def _shadow_pending_package(adopter: str) -> dict[str, object]:
    return {
        "gap": f"shadow_parity_pending:{adopter}",
        "capability": f"shadow-parity:{adopter}",
        "source_location": f"{adopter} adopter repository",
        "target_home": "ethos-adapters + ethos-test",
        "disposition": "shadow-parity",
        "required_tests": [
            "status/plan/prove/report command comparison",
            "land and publish readiness comparison",
            "blocking versus advisory gap classification",
        ],
        "parity_criterion": (
            "external adopter command outputs preserve ETHOS branch-role, mutation, "
            "evidence, and publication-readiness semantics"
        ),
        "rollback_impact": (
            "adopter continues using local embedded fallback until shadow parity passes"
        ),
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
