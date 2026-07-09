from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.repository.evidence.parity_validation import SHADOW_PARITY_COMMANDS
from ethos.repository.evidence.parity_validation import migratable_capability_list
from ethos.repository.evidence.parity_validation import semantic_tree_digest
from ethos.repository.evidence.parity_validation import sha256_text
from ethos.repository.evidence.parity_validation import string_list
from ethos.repository.evidence.shadow.routing import requires_product_root_argument
from ethos.repository.evidence.shadow.routing import target_command_argument
from ethos.repository.evidence.shadow.routing import target_identity

if TYPE_CHECKING:
    from pathlib import Path

# The tree whose change can actually move a shadow-compared command output
# (status / plan --changed / prove / report / quality command-surface / assistants
# doctor / playbooks route / land / publish). Parity freshness is keyed on THIS
# semantic tree, not on a proxy touch of the evidence file.
PARITY_RELEVANT_PATHS: tuple[str, ...] = (
    "packages",
    "system",
    ".ethos",
    ".agents/skills",
    "openspec",
    "evidence/claims",
    "rules",
    "pyproject.toml",
    "uv.lock",
    "docs/governance",
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
    "external_false_negative",
]


def build_tracked_parity_evidence(
    *,
    adopter: str,
    target: Path,
    shadow: dict[str, object],
    current_product_head: str,
    current_target_head: str,
    timeout_seconds: int,
    root: Path | None = None,
) -> dict[str, object]:
    target = target.resolve()
    target_name = target_identity(root=root, adopter=adopter, target=target)
    accepted_summary = shadow.get("accepted_summary")
    shadow_required_gaps = shadow.get("required_gaps")
    command = shadow_evidence_command(
        adopter=adopter,
        target=target_command_argument(target_name),
        timeout_seconds=timeout_seconds,
        root=root,
        include_product_root=requires_product_root_argument(root=root, target=target),
    )
    return {
        "schema_version": 1,
        "adopter": adopter,
        "target": target_name,
        "generated_on": datetime.now(tz=UTC).date().isoformat(),
        "command": command,
        "freshness": {
            "product_head": current_product_head,
            "target_head": current_target_head,
            "product_semantic_sha256": semantic_tree_digest(
                root or target,
                head=current_product_head,
                relevant_paths=PARITY_RELEVANT_PATHS,
            ),
            "target_semantic_sha256": semantic_tree_digest(
                target,
                head=current_target_head,
                relevant_paths=PARITY_RELEVANT_PATHS,
            ),
            "command_sha256": sha256_text(command),
        },
        "shadow": {
            "ok": bool(shadow.get("ok")),
            "state": str(shadow.get("state") or "matched"),
            "required_gaps": list(shadow_required_gaps)
            if isinstance(shadow_required_gaps, list)
            else [],
            "comparison_count": len(SHADOW_PARITY_COMMANDS),
            "commands": list(SHADOW_PARITY_COMMANDS),
            "accepted_summary": accepted_summary
            if isinstance(accepted_summary, dict)
            else {"total_count": 0, "kind_counts": {}, "command_count": 0},
            "false_negative_count": int_value(shadow.get("false_negative_count")),
        },
        "identity": shadow_identity(
            shadow=shadow,
            target=target,
            current_target_head=current_target_head,
            current_product_head=current_product_head,
        ),
        "verified_capabilities": migratable_capability_list(),
        "semantic_dimensions": string_list(shadow.get("semantic_dimensions"))
        or list(SHADOW_PARITY_DIMENSIONS),
        "capability_basis": {
            capability: [f"{capability} shadow parity matched"]
            for capability in migratable_capability_list()
        },
    }


def int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def shadow_identity(
    *,
    shadow: dict[str, object],
    target: Path,
    current_target_head: str,
    current_product_head: str,
) -> dict[str, object]:
    value = shadow.get("identity")
    if isinstance(value, dict):
        return {
            "target_root": str(value.get("target_root") or target.resolve().as_posix()),
            "target_head": str(value.get("target_head") or current_target_head),
            "product_head": str(value.get("product_head") or current_product_head),
            "changed_paths": string_list(value.get("changed_paths")),
            "commands": string_list(value.get("commands")) or list(SHADOW_PARITY_COMMANDS),
            "external_commands": string_list(value.get("external_commands")),
            "embedded_commands": string_list(value.get("embedded_commands")),
            "evidence_inputs": identity_evidence_inputs(value.get("evidence_inputs")),
        }
    return {
        "target_root": target.resolve().as_posix(),
        "target_head": current_target_head,
        "product_head": current_product_head,
        "changed_paths": [],
        "commands": list(SHADOW_PARITY_COMMANDS),
        "external_commands": [],
        "embedded_commands": [],
        "evidence_inputs": [],
    }


def identity_evidence_inputs(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        kind = str(item.get("kind") or "")
        sha256 = str(item.get("sha256") or "")
        if path and kind and sha256:
            result.append({"path": path, "kind": kind, "sha256": sha256})
    return result


def shadow_evidence_command(
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
