from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
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
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
) -> dict[str, object]:
    records = capability_parity_records()
    adopter_name = adopter or "generic"
    evidence_root = root or Path.cwd()
    evidence = _parity_evidence(
        evidence_root,
        adopter_name,
        target=target,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
    )
    evidence_valid = not evidence.get("required_gaps")
    evidence_gaps = [str(gap) for gap in evidence.get("required_gaps", [])]
    if not evidence:
        evidence = {
            "refresh_package": parity_evidence_refresh_package(
                root=evidence_root,
                adopter=adopter_name,
                target=target,
                required_gaps=[f"parity_evidence_missing:{adopter_name}"],
            )
        }
    elif evidence_gaps:
        evidence = {
            **evidence,
            "refresh_package": parity_evidence_refresh_package(
                root=evidence_root,
                adopter=adopter_name,
                target=target,
                required_gaps=evidence_gaps,
            ),
        }
    verified = set(evidence.get("verified_capabilities", []))
    pending_packages = [
        _pending_package(record)
        for record in records
        if record["disposition"] in {"migrate-to-product", "split"}
        and (not evidence_valid or record["capability"] not in verified)
    ]
    shadow = evidence.get("shadow") if isinstance(evidence.get("shadow"), dict) else {}
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


def build_tracked_parity_evidence(
    *,
    adopter: str,
    target: Path,
    shadow: dict[str, object],
    current_product_head: str,
    current_target_head: str,
    timeout_seconds: int,
) -> dict[str, object]:
    target = target.resolve()
    command = _shadow_evidence_command(
        adopter=adopter,
        target=target,
        timeout_seconds=timeout_seconds,
    )
    return {
        "schema_version": 1,
        "adopter": adopter,
        "target": target.as_posix(),
        "generated_on": datetime.now(tz=UTC).date().isoformat(),
        "command": command,
        "freshness": {
            "product_head": current_product_head,
            "target_head": current_target_head,
            "command_sha256": _sha256_text(command),
        },
        "shadow": {
            "ok": bool(shadow.get("ok")),
            "state": str(shadow.get("state") or "matched"),
            "required_gaps": list(shadow.get("required_gaps", []))
            if isinstance(shadow.get("required_gaps"), list)
            else [],
            "comparison_count": len(SHADOW_PARITY_COMMANDS),
            "commands": list(SHADOW_PARITY_COMMANDS),
        },
        "verified_capabilities": _migratable_capability_list(),
        "semantic_dimensions": _string_list(shadow.get("semantic_dimensions"))
        or list(SHADOW_PARITY_DIMENSIONS),
        "capability_basis": {
            capability: [f"{capability} shadow parity matched"]
            for capability in _migratable_capability_list()
        },
    }


def write_tracked_parity_evidence(
    *,
    root: Path,
    adopter: str,
    evidence: dict[str, object],
) -> Path:
    path = root / "docs" / "evidence" / "parity" / f"{adopter}-shadow.json"
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
    target_text = target.resolve().as_posix() if target is not None else "<repo>"
    return {
        "kind": "parity_evidence_refresh",
        "adopter": adopter,
        "root": root.resolve().as_posix(),
        "target": target_text,
        "blocking": True,
        "required_gaps": [str(gap) for gap in required_gaps],
        "command": _shadow_refresh_command(adopter=adopter, target=target_text),
        "next_action": "refresh tracked shadow parity evidence",
    }


def _shadow_refresh_command(*, adopter: str, target: str) -> str:
    return (
        f"ethos parity shadow --adopter {adopter} --target {target} "
        "--execute --write-evidence --json"
    )


def _shadow_evidence_command(*, adopter: str, target: Path, timeout_seconds: int) -> str:
    return (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target {target.as_posix()} --execute --timeout-seconds {timeout_seconds} --json"
    )


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


SHADOW_PARITY_COMMANDS = (
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

SHADOW_PARITY_DIMENSIONS = [
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
]


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
        evidence = _parity_evidence(
            root or Path.cwd(),
            adopter,
            target=target,
            current_target_head=current_target_head,
            current_product_head=current_product_head,
            acceptable_product_heads=acceptable_product_heads,
            acceptable_target_heads=acceptable_target_heads,
        )
        if evidence:
            evidence_gaps = list(evidence.get("required_gaps", []))
            if evidence.get("target") != target.as_posix():
                evidence_gaps.append(f"shadow_parity_evidence_target_mismatch:{adopter}")
            shadow = evidence.get("shadow") if isinstance(evidence.get("shadow"), dict) else {}
            provenance = _tracked_evidence_provenance(
                evidence,
                required_gaps=evidence_gaps,
                current_target_head=current_target_head,
                current_product_head=current_product_head,
            )
            if not evidence_gaps and shadow.get("ok") is True:
                commands = _string_list(shadow.get("commands")) or list(SHADOW_PARITY_COMMANDS)
                dimensions = _string_list(evidence.get("semantic_dimensions")) or list(
                    SHADOW_PARITY_DIMENSIONS
                )
                package = {
                    "kind": "shadow_parity_evidence",
                    "state": str(shadow.get("state") or "matched"),
                    "target": target.as_posix(),
                    "evidence_path": str(evidence.get("path")),
                    "comparison_count": int(shadow.get("comparison_count") or len(commands)),
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
                root=root or Path.cwd(),
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


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _tracked_evidence_provenance(
    evidence: dict[str, object],
    *,
    required_gaps: list[str],
    current_target_head: str,
    current_product_head: str = "",
) -> dict[str, object]:
    freshness = evidence.get("freshness") if isinstance(evidence.get("freshness"), dict) else {}
    return {
        "mode": "tracked_evidence",
        "evidence_path": str(evidence.get("path") or ""),
        "freshness": {
            "ok": not required_gaps,
            "required_gaps": list(required_gaps),
            "product_head": str(freshness.get("product_head") or ""),
            "current_product_head": current_product_head,
            "target_head": str(freshness.get("target_head") or ""),
            "current_target_head": current_target_head,
            "command_sha256": str(freshness.get("command_sha256") or ""),
        },
    }


def _parity_evidence(
    root: Path,
    adopter: str | None,
    *,
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
) -> dict[str, object]:
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
    required_gaps = _validate_parity_evidence(
        payload,
        adopter,
        target=target,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
    )
    return {
        "path": path.relative_to(root).as_posix(),
        **payload,
        "required_gaps": required_gaps,
    }


def _validate_parity_evidence(
    payload: dict[str, object],
    adopter: str,
    *,
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
) -> list[str]:
    required_gaps: list[str] = []
    if payload.get("schema_version") != 1:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:schema_version")
    if payload.get("adopter") != adopter:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:adopter")
    if not isinstance(payload.get("target"), str) or not payload.get("target"):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:target")
    if not isinstance(payload.get("generated_on"), str) or not payload.get("generated_on"):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:generated_on")
    command = payload.get("command")
    if not isinstance(command, str) or not command:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:command")
    elif not _command_matches_identity(command, adopter=adopter, target=payload.get("target")):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:command_identity")
    _validate_freshness(
        payload.get("freshness"),
        adopter=adopter,
        command=command if isinstance(command, str) else "",
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
        required_gaps=required_gaps,
    )
    shadow = payload.get("shadow")
    if not isinstance(shadow, dict):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow")
    else:
        if shadow.get("ok") is not True:
            required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow_ok")
        if shadow.get("required_gaps") != []:
            required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow_required_gaps")
        if shadow.get("comparison_count") != len(SHADOW_PARITY_COMMANDS):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:comparison_count")
        if shadow.get("commands") != list(SHADOW_PARITY_COMMANDS):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:commands")
    verified = payload.get("verified_capabilities")
    if not isinstance(verified, list) or not all(isinstance(item, str) for item in verified):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:verified_capabilities")
    else:
        migratable = _migratable_capabilities()
        unknown = sorted(set(verified) - migratable)
        if unknown:
            required_gaps.append(f"parity_evidence_invalid:{adopter}:unknown_capability")
        capability_basis = payload.get("capability_basis")
        if not isinstance(capability_basis, dict):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:capability_basis")
        else:
            for capability in verified:
                basis = capability_basis.get(capability)
                if not isinstance(basis, list) or not basis or not all(
                    isinstance(item, str) and item for item in basis
                ):
                    required_gaps.append(
                        f"parity_evidence_invalid:{adopter}:capability_basis:{capability}"
                    )
    if required_gaps:
        return [f"parity_evidence_invalid:{adopter}", *required_gaps]
    return []


def _command_matches_identity(command: str, *, adopter: str, target: object) -> bool:
    if "ethos parity shadow" not in command:
        return False
    if f"--adopter {adopter}" not in command:
        return False
    if isinstance(target, str) and target and f"--target {target}" not in command:
        return False
    return "--execute" in command and "--json" in command


def _validate_freshness(
    freshness: object,
    *,
    adopter: str,
    command: str,
    current_target_head: str,
    current_product_head: str,
    acceptable_product_heads: Iterable[str],
    acceptable_target_heads: Iterable[str],
    required_gaps: list[str],
) -> None:
    if not isinstance(freshness, dict):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:freshness")
        return
    for field in ("product_head", "target_head", "command_sha256"):
        if not isinstance(freshness.get(field), str) or not freshness.get(field):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:{field}")
    expected_digest = _sha256_text(command)
    if command and freshness.get("command_sha256") != expected_digest:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:command_sha256")
    product_head = str(freshness.get("product_head") or "")
    if (
        current_product_head
        and product_head != current_product_head
        and product_head not in set(acceptable_product_heads)
    ):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:product_head")
    target_head = str(freshness.get("target_head") or "")
    if (
        current_target_head
        and target_head != current_target_head
        and target_head not in set(acceptable_target_heads)
    ):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:target_head")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _migratable_capabilities() -> set[str]:
    return {
        str(record["capability"])
        for record in capability_parity_records()
        if record["disposition"] in {"migrate-to-product", "split"}
    }


def _migratable_capability_list() -> list[str]:
    return [
        str(record["capability"])
        for record in capability_parity_records()
        if record["disposition"] in {"migrate-to-product", "split"}
    ]
