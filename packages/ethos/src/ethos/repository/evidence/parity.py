from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.evidence.parity_validation import SHADOW_PARITY_COMMANDS
from ethos.repository.evidence.parity_validation import parity_evidence
from ethos.repository.evidence.parity_validation import string_list
from ethos.repository.evidence.parity_validation import tracked_evidence_provenance
from ethos.repository.evidence.shadow.payload import PARITY_RELEVANT_PATHS
from ethos.repository.evidence.shadow.payload import SHADOW_PARITY_DIMENSIONS
from ethos.repository.evidence.shadow.payload import build_tracked_parity_evidence
from ethos.repository.evidence.shadow.routing import REPOSITORY_TARGET
from ethos.repository.evidence.shadow.routing import parity_evidence_path
from ethos.repository.evidence.shadow.routing import parity_evidence_repository_root
from ethos.repository.evidence.shadow.routing import requires_product_root_argument
from ethos.repository.evidence.shadow.routing import target_command_argument
from ethos.repository.evidence.shadow.routing import target_identity
from ethos_core.contracts.capability.parity import capability_parity_records

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["build_tracked_parity_evidence"]


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
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
) -> dict[str, object]:
    records = capability_parity_records()
    adopter_name = adopter or "generic"
    product_root = root or Path.cwd()
    evidence_root = parity_evidence_repository_root(root=product_root, target=target)
    evidence = parity_evidence(
        evidence_root,
        adopter_name,
        target=target,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
        relevant_paths=PARITY_RELEVANT_PATHS,
        product_root=product_root,
    )
    evidence_valid = not evidence.get("required_gaps")
    evidence_gaps = [
        str(gap) for gap in cast("Iterable[object]", evidence.get("required_gaps", []))
    ]
    if not evidence:
        evidence = {
            "refresh_package": parity_evidence_refresh_package(
                root=product_root,
                adopter=adopter_name,
                target=target,
                required_gaps=[f"parity_evidence_missing:{adopter_name}"],
            )
        }
    elif evidence_gaps:
        evidence = {
            **evidence,
            "refresh_package": parity_evidence_refresh_package(
                root=product_root,
                adopter=adopter_name,
                target=target,
                required_gaps=evidence_gaps,
            ),
        }
    verified = set(cast("Iterable[object]", evidence.get("verified_capabilities", [])))
    pending_packages = [
        _pending_package(record)
        for record in records
        if record["disposition"] in {"migrate-to-product", "split"}
        and (not evidence_valid or record["capability"] not in verified)
    ]
    shadow_value = evidence.get("shadow")
    shadow = shadow_value if isinstance(shadow_value, dict) else {}
    if adopter and not (shadow.get("ok") is True and not shadow.get("required_gaps")):
        pending_packages.append(_shadow_pending_package(adopter))
    required_gaps = [str(package["gap"]) for package in pending_packages]
    if evidence_gaps:
        required_gaps.extend(evidence_gaps)
    return {
        "ok": not required_gaps,
        "adopter": adopter_name,
        "required_gaps": required_gaps,
        "pending_packages": pending_packages,
        "records": records,
        "evidence": evidence,
    }


def write_tracked_parity_evidence(
    *,
    root: Path,
    adopter: str,
    evidence: dict[str, object],
) -> Path:
    path = parity_evidence_path(root=root, adopter=adopter)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(evidence, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def parity_evidence_refresh_package(
    *,
    root: Path,
    adopter: str,
    target: Path | None,
    required_gaps: Iterable[str] = (),
) -> dict[str, object]:
    target_name = (
        target_identity(root=root, adopter=adopter, target=target.resolve())
        if target is not None
        else REPOSITORY_TARGET
    )
    target_arg = target_command_argument(target_name)
    include_product_root = requires_product_root_argument(root=root, target=target)
    return {
        "kind": "parity_evidence_refresh",
        "adopter": adopter,
        "root": root.resolve().as_posix(),
        "target": target_name,
        "blocking": True,
        "required_gaps": [str(gap) for gap in required_gaps],
        "command": _shadow_refresh_command(
            adopter=adopter,
            root=root,
            target=target_arg,
            include_product_root=include_product_root,
        ),
        "next_action": "refresh tracked shadow parity evidence",
    }


def _shadow_refresh_command(
    *, adopter: str, root: Path, target: str, include_product_root: bool
) -> str:
    root_arg = f" --root {root.resolve().as_posix()}" if include_product_root else ""
    return (
        f"ethos parity shadow --adopter {adopter}{root_arg} --target {target} "
        "--execute --write-evidence --json"
    )


def _shadow_evidence_command(
    *,
    adopter: str,
    target: str,
    timeout_seconds: int,
    root: Path | None,
    include_product_root: bool,
) -> str:
    root_arg = f" --root {root.resolve().as_posix()}" if root and include_product_root else ""
    return (
        f"uv run --package ethos ethos parity shadow --adopter {adopter}{root_arg} "
        f"--target {target} --execute --timeout-seconds {timeout_seconds} --json"
    )


def _pending_package(record: dict[str, object]) -> dict[str, object]:
    return {
        "gap": f"parity_pending:{record['capability']}",
        "capability": record["capability"],
        "source_location": record["source_location"],
        "target_home": record["target_home"],
        "disposition": record["disposition"],
        "required_tests": list(cast("Iterable[object]", record["required_tests"])),
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


def shadow_parity_report(
    *,
    target: Path,
    root: Path | None = None,
    adopter: str | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
) -> dict[str, object]:
    target = target.resolve()
    if adopter:
        target_name = target_identity(root=root or Path.cwd(), adopter=adopter, target=target)
        product_root = root or Path.cwd()
        evidence_root = parity_evidence_repository_root(root=product_root, target=target)
        evidence = parity_evidence(
            evidence_root,
            adopter,
            target=target,
            current_target_head=current_target_head,
            current_product_head=current_product_head,
            acceptable_product_heads=acceptable_product_heads,
            acceptable_target_heads=acceptable_target_heads,
            relevant_paths=PARITY_RELEVANT_PATHS,
            product_root=product_root,
        )
        if evidence:
            evidence_gaps = list(cast("Iterable[str]", evidence.get("required_gaps", [])))
            if evidence.get("target") != target_name:
                evidence_gaps.append(f"shadow_parity_evidence_target_mismatch:{adopter}")
            shadow_value = evidence.get("shadow")
            shadow = shadow_value if isinstance(shadow_value, dict) else {}
            provenance = tracked_evidence_provenance(
                evidence,
                required_gaps=evidence_gaps,
                current_target_head=current_target_head,
                current_product_head=current_product_head,
                semantic_context={
                    "product_root": product_root,
                    "target_root": target,
                    "relevant_paths": PARITY_RELEVANT_PATHS,
                },
            )
            if not evidence_gaps and shadow.get("ok") is True:
                commands = string_list(shadow.get("commands")) or list(SHADOW_PARITY_COMMANDS)
                dimensions = string_list(evidence.get("semantic_dimensions")) or list(
                    SHADOW_PARITY_DIMENSIONS
                )
                package = {
                    "kind": "shadow_parity_evidence",
                    "state": str(shadow.get("state") or "matched"),
                    "target": target.as_posix(),
                    "evidence_path": str(evidence.get("path")),
                    "comparison_count": int(
                        cast("int", shadow.get("comparison_count")) or len(commands)
                    ),
                    "commands": commands,
                    "semantic_dimensions": dimensions,
                    "blocking": False,
                    "required_gaps": [],
                    "provenance": provenance,
                    "next_action": "use tracked shadow parity evidence for local closeout",
                }
                return {
                    "ok": True,
                    "state": package["state"],
                    "target": target.as_posix(),
                    "required_gaps": [],
                    "comparisons": commands,
                    "semantic_dimensions": dimensions,
                    "evidence_path": evidence.get("path"),
                    "provenance": provenance,
                    "execution_packages": [package],
                }
            gap = f"shadow_parity_evidence_invalid:{adopter}"
            refresh_package = parity_evidence_refresh_package(
                root=product_root,
                adopter=adopter,
                target=target,
                required_gaps=evidence_gaps,
            )
            return {
                "ok": False,
                "state": "invalid",
                "target": target.as_posix(),
                "required_gaps": [gap, *evidence_gaps],
                "comparisons": list(SHADOW_PARITY_COMMANDS),
                "semantic_dimensions": list(SHADOW_PARITY_DIMENSIONS),
                "evidence_path": evidence.get("path"),
                "provenance": provenance,
                "execution_packages": [
                    {
                        "gap": gap,
                        "state": "invalid",
                        "target": target.as_posix(),
                        "evidence_path": evidence.get("path"),
                        "commands": list(SHADOW_PARITY_COMMANDS),
                        "semantic_dimensions": list(SHADOW_PARITY_DIMENSIONS),
                        "blocking": True,
                        "required_gaps": evidence_gaps,
                        "provenance": provenance,
                        "refresh_package": refresh_package,
                        "next_action": refresh_package["command"],
                    }
                ],
            }
    gap = f"shadow_parity_not_executed:{target.as_posix()}"
    provenance = {
        "mode": "planned_shadow_run",
        "evidence_path": "",
        "freshness": {
            "ok": False,
            "required_gaps": [gap],
            "product_head": "",
            "current_product_head": current_product_head,
            "target_head": "",
            "current_target_head": current_target_head,
            "command_sha256": "",
        },
    }
    refresh_package = parity_evidence_refresh_package(
        root=root or Path.cwd(),
        adopter=adopter or "generic",
        target=target,
        required_gaps=[gap],
    )
    return {
        "ok": False,
        "state": "planned",
        "target": target.as_posix(),
        "required_gaps": [gap],
        "comparisons": list(SHADOW_PARITY_COMMANDS),
        "semantic_dimensions": list(SHADOW_PARITY_DIMENSIONS),
        "provenance": provenance,
        "execution_packages": [
            {
                "gap": gap,
                "state": "planned",
                "target": target.as_posix(),
                "commands": list(SHADOW_PARITY_COMMANDS),
                "semantic_dimensions": list(SHADOW_PARITY_DIMENSIONS),
                "blocking": True,
                "provenance": provenance,
                "refresh_package": refresh_package,
                "next_action": refresh_package["command"],
            }
        ],
    }
