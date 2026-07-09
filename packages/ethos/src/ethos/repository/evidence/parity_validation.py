from __future__ import annotations

import hashlib
import json
import re
import subprocess
from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.evidence.shadow.routing import parity_evidence_path
from ethos_core.contracts.capability.parity import capability_parity_records

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
# The shadow-parity command set — the single source of truth for BOTH the executed
# read-only commands (adapters/shadow/core.py imports SHADOW_COMMAND_ARGS to run them) and
# the display-string identities recorded in parity evidence (SHADOW_PARITY_COMMANDS,
# derived below). Add or remove a command in ONE place; the two forms cannot drift.
# Lives in the repository layer so adapters may import it (adapters -> repository is the
# permitted direction; the reverse is not).
SHADOW_COMMAND_ARGS: tuple[tuple[str, ...], ...] = (
    ("status",),
    ("plan", "--changed"),
    ("prove",),
    ("report",),
    ("quality", "command-surface"),
    ("assistants", "doctor"),
    ("playbooks", "route", "--changed"),
    ("land",),
    ("publish",),
)
SHADOW_PARITY_COMMANDS: tuple[str, ...] = tuple(
    "ethos " + " ".join(args) + " --json" for args in SHADOW_COMMAND_ARGS
)
_MAC_HOME_PREFIX = "/" + "Users" + "/"
_HOME_PROJECT_PREFIX = "~" + "/" + "projects"
_RELEASE_VISIBLE_LOCAL_PATH_PATTERN = re.compile(
    rf"(?:{re.escape(_MAC_HOME_PREFIX)}|{re.escape(_HOME_PROJECT_PREFIX)}/)[^\s\"']+"
)


def string_list(value: object) -> list[str]:
    """Return a string-normalized list when the payload field is list-shaped."""
    return [str(item) for item in value] if isinstance(value, list) else []


def semantic_tree_digest(root: Path, *, head: str, relevant_paths: tuple[str, ...]) -> str:
    """Digest the Git tree entries that can change generic parity semantics."""
    if not head:
        return ""
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", head, "--", *relevant_paths],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return sha256_text(completed.stdout)


def tracked_evidence_provenance(
    evidence: dict[str, object],
    *,
    required_gaps: list[str],
    current_target_head: str,
    current_product_head: str = "",
    semantic_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Describe how tracked parity evidence binds to current heads and digests."""
    freshness_value = evidence.get("freshness")
    freshness = freshness_value if isinstance(freshness_value, dict) else {}
    product_head = str(freshness.get("product_head") or "")
    target_head = str(freshness.get("target_head") or "")
    product_current = bool(current_product_head) and product_head == current_product_head
    target_current = bool(current_target_head) and target_head == current_target_head
    product_head_gap = any(str(gap).endswith(":product_head") for gap in required_gaps)
    target_head_gap = any(str(gap).endswith(":target_head") for gap in required_gaps)
    recorded_product_digest = str(freshness.get("product_semantic_sha256") or "")
    recorded_target_digest = str(freshness.get("target_semantic_sha256") or "")
    semantic = semantic_context or {}
    product_root = cast("Path | None", semantic.get("product_root"))
    target_root = cast("Path | None", semantic.get("target_root"))
    relevant_paths = cast("tuple[str, ...]", semantic.get("relevant_paths") or ())
    current_product_digest = (
        semantic_tree_digest(product_root, head=current_product_head, relevant_paths=relevant_paths)
        if product_root is not None and relevant_paths and current_product_head
        else ""
    )
    current_target_digest = (
        semantic_tree_digest(target_root, head=current_target_head, relevant_paths=relevant_paths)
        if target_root is not None and relevant_paths and current_target_head
        else ""
    )
    return {
        "mode": "tracked_evidence",
        "evidence_path": str(evidence.get("path") or ""),
        "freshness": {
            "ok": not required_gaps,
            "required_gaps": list(required_gaps),
            "product_head": product_head,
            "current_product_head": current_product_head,
            "product_head_current": product_current,
            "product_head_accepted_by_relevant_tree": bool(
                current_product_head
                and product_head
                and product_head != current_product_head
                and not product_head_gap
            ),
            "product_semantic_sha256": recorded_product_digest,
            "current_product_semantic_sha256": current_product_digest,
            "product_semantic_current": bool(
                recorded_product_digest
                and current_product_digest
                and recorded_product_digest == current_product_digest
            ),
            "target_head": target_head,
            "current_target_head": current_target_head,
            "target_head_current": target_current,
            "target_head_accepted_by_relevant_tree": bool(
                current_target_head
                and target_head
                and target_head != current_target_head
                and not target_head_gap
            ),
            "target_semantic_sha256": recorded_target_digest,
            "current_target_semantic_sha256": current_target_digest,
            "target_semantic_current": bool(
                recorded_target_digest
                and current_target_digest
                and recorded_target_digest == current_target_digest
            ),
            "command_sha256": str(freshness.get("command_sha256") or ""),
        },
    }


def parity_evidence(
    root: Path,
    adopter: str | None,
    *,
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
    relevant_paths: tuple[str, ...] = (),
    product_root: Path | None = None,
) -> dict[str, object]:
    """Load and validate tracked shadow-parity evidence for one adopter."""
    if not adopter:
        return {}
    path = parity_evidence_path(root=root, adopter=adopter)
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
    required_gaps = validate_parity_evidence(
        payload,
        adopter,
        target=target,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
        product_root=product_root or root,
        target_root=target,
        relevant_paths=relevant_paths,
    )
    evidence_with_path = {"path": path.relative_to(root).as_posix(), **payload}
    return {
        **evidence_with_path,
        "required_gaps": required_gaps,
        "provenance": tracked_evidence_provenance(
            evidence_with_path,
            required_gaps=required_gaps,
            current_target_head=current_target_head,
            current_product_head=current_product_head,
            semantic_context={
                "product_root": product_root or root,
                "target_root": target,
                "relevant_paths": relevant_paths,
            },
        ),
    }


def validate_parity_evidence(
    payload: dict[str, object],
    adopter: str,
    *,
    target: Path | None = None,
    current_target_head: str = "",
    current_product_head: str = "",
    acceptable_product_heads: Iterable[str] = (),
    acceptable_target_heads: Iterable[str] = (),
    product_root: Path | None = None,
    target_root: Path | None = None,
    relevant_paths: tuple[str, ...] = (),
) -> list[str]:
    """Return required gaps for malformed, stale, or overclaiming parity evidence."""
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
    elif not command_matches_identity(command, adopter=adopter, target=payload.get("target")):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:command_identity")
    _validate_freshness(
        {
            "freshness": payload.get("freshness"),
            "adopter": adopter,
            "command": command if isinstance(command, str) else "",
            "current_target_head": current_target_head,
            "current_product_head": current_product_head,
            "acceptable_product_heads": acceptable_product_heads,
            "acceptable_target_heads": acceptable_target_heads,
            "product_root": product_root,
            "target_root": target_root,
            "relevant_paths": relevant_paths,
            "required_gaps": required_gaps,
        }
    )
    _validate_shadow(payload.get("shadow"), adopter=adopter, required_gaps=required_gaps)
    _validate_semantic_dimensions(
        payload.get("semantic_dimensions"),
        adopter=adopter,
        required_gaps=required_gaps,
    )
    _validate_verified_capabilities(
        payload.get("verified_capabilities"),
        capability_basis=payload.get("capability_basis"),
        adopter=adopter,
        required_gaps=required_gaps,
    )
    _validate_release_visible_payload(payload, adopter=adopter, required_gaps=required_gaps)
    if required_gaps:
        return [f"parity_evidence_invalid:{adopter}", *required_gaps]
    return []


def _validate_shadow(
    shadow: object,
    *,
    adopter: str,
    required_gaps: list[str],
) -> None:
    if not isinstance(shadow, dict):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow")
        return
    if shadow.get("ok") is not True:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow_ok")
    if shadow.get("required_gaps") != []:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:shadow_required_gaps")
    if shadow.get("comparison_count") != len(SHADOW_PARITY_COMMANDS):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:comparison_count")
    if shadow.get("commands") != list(SHADOW_PARITY_COMMANDS):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:commands")
    if shadow.get("false_negative_count") != 0:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:false_negative_count")


def _validate_semantic_dimensions(
    dimensions: object,
    *,
    adopter: str,
    required_gaps: list[str],
) -> None:
    if not isinstance(dimensions, list) or not all(isinstance(item, str) for item in dimensions):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:semantic_dimensions")
        return
    required = {"blocking_vs_advisory", "external_false_negative"}
    missing = sorted(required - set(dimensions))
    required_gaps.extend(
        f"parity_evidence_invalid:{adopter}:semantic_dimension:{dimension}" for dimension in missing
    )


def _validate_verified_capabilities(
    verified: object,
    *,
    capability_basis: object,
    adopter: str,
    required_gaps: list[str],
) -> None:
    if not isinstance(verified, list) or not all(isinstance(item, str) for item in verified):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:verified_capabilities")
        return
    unknown = sorted(set(verified) - _migratable_capabilities())
    if unknown:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:unknown_capability")
    if not isinstance(capability_basis, dict):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:capability_basis")
        return
    for capability in verified:
        basis = capability_basis.get(capability)
        if not _valid_capability_basis(basis):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:capability_basis:{capability}")


def _validate_release_visible_payload(
    payload: dict[str, object],
    *,
    adopter: str,
    required_gaps: list[str],
) -> None:
    """Block host-local workstation roots from tracked parity evidence."""
    if _RELEASE_VISIBLE_LOCAL_PATH_PATTERN.search(json.dumps(payload, sort_keys=True)):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:release_visible_local_path")


def _valid_capability_basis(basis: object) -> bool:
    return (
        isinstance(basis, list)
        and bool(basis)
        and all(isinstance(item, str) and item for item in basis)
    )


def command_matches_identity(command: str, *, adopter: str, target: object) -> bool:
    """Check whether a recorded shadow command names the adopter and target."""
    if "ethos parity shadow" not in command:
        return False
    if f"--adopter {adopter}" not in command:
        return False
    if isinstance(target, str) and target:
        target_matches = f"--target {target}" in command or (
            target == "<repo>" and "--target ." in command
        )
        if not target_matches:
            return False
    elif "--target " not in command:
        return False
    return "--execute" in command and "--json" in command


def _validate_freshness(context: dict[str, object]) -> None:
    freshness = context["freshness"]
    adopter = str(context["adopter"])
    command = str(context["command"])
    current_target_head = str(context["current_target_head"])
    current_product_head = str(context["current_product_head"])
    acceptable_product_heads = set(cast("Iterable[str]", context["acceptable_product_heads"]))
    acceptable_target_heads = set(cast("Iterable[str]", context["acceptable_target_heads"]))
    product_root = cast("Path | None", context.get("product_root"))
    target_root = cast("Path | None", context.get("target_root"))
    relevant_paths = cast("tuple[str, ...]", context.get("relevant_paths") or ())
    required_gaps = cast("list[str]", context["required_gaps"])
    if not isinstance(freshness, dict):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:freshness")
        return
    for field in ("product_head", "target_head", "command_sha256"):
        if not isinstance(freshness.get(field), str) or not freshness.get(field):
            required_gaps.append(f"parity_evidence_invalid:{adopter}:{field}")
    expected_digest = sha256_text(command)
    if command and freshness.get("command_sha256") != expected_digest:
        required_gaps.append(f"parity_evidence_invalid:{adopter}:command_sha256")
    product_head = str(freshness.get("product_head") or "")
    product_semantic = str(freshness.get("product_semantic_sha256") or "")
    current_product_semantic = (
        semantic_tree_digest(product_root, head=current_product_head, relevant_paths=relevant_paths)
        if product_root is not None and relevant_paths and current_product_head
        else ""
    )
    product_semantic_matches = bool(
        product_semantic
        and current_product_semantic
        and product_semantic == current_product_semantic
    )
    if (
        current_product_head
        and product_head != current_product_head
        and product_head not in acceptable_product_heads
        and not product_semantic_matches
    ):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:product_head")
    target_head = str(freshness.get("target_head") or "")
    target_semantic = str(freshness.get("target_semantic_sha256") or "")
    current_target_semantic = (
        semantic_tree_digest(target_root, head=current_target_head, relevant_paths=relevant_paths)
        if target_root is not None and relevant_paths and current_target_head
        else ""
    )
    target_semantic_matches = bool(
        target_semantic and current_target_semantic and target_semantic == current_target_semantic
    )
    if (
        current_target_head
        and target_head != current_target_head
        and target_head not in acceptable_target_heads
        and not target_semantic_matches
    ):
        required_gaps.append(f"parity_evidence_invalid:{adopter}:target_head")


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest for a UTF-8 text value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _migratable_capabilities() -> set[str]:
    return {
        str(record["capability"])
        for record in capability_parity_records()
        if record["disposition"] in {"migrate-to-product", "split"}
    }


def migratable_capability_list() -> list[str]:
    """List parity capabilities that product governance must verify or split."""
    return [
        str(record["capability"])
        for record in capability_parity_records()
        if record["disposition"] in {"migrate-to-product", "split"}
    ]
