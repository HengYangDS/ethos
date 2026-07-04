from __future__ import annotations

import hashlib
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos_core.contracts.package_ontology import RETIRED_PRODUCT_FAMILY_TOKENS
from ethos_core.models import EvidenceClaim

if TYPE_CHECKING:
    from pathlib import Path

REPOSITORY_OVERCLAIM_PHRASES = (
    "raw/cache",
    "parity passed",
    "hosted ci",
    "remote publication",
    "published",
    "verified",
    "validates",
    "enforces",
    "guarantees",
    "guaranteed",
    " are retired",
    " is retired",
    " are closed",
    " is closed",
    "retirement is safe",
    "backend retirement",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_payload(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _string_value(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return str(value) if value else ""


def _list_value(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _promotion_kind(path: str) -> str:
    if path.startswith("docs/evidence/"):
        return "evidence"
    if path.startswith("docs/"):
        return "docs"
    if path.startswith("schemas/"):
        return "schema"
    if path.startswith("openspec/"):
        return "openspec"
    if path.startswith("tests/"):
        return "tests"
    return "source"


def _promotion_targets(payload: dict[str, Any]) -> list[dict[str, str]]:
    value = payload.get("targets")
    if not isinstance(value, list):
        return []
    targets: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            path = str(item.get("path") or "")
            kind = str(item.get("kind") or _promotion_kind(path))
        else:
            path = str(item)
            kind = _promotion_kind(path)
        if path:
            targets.append({"kind": kind, "path": path})
    return targets


def _has_repository_overclaim(text: str, verifier: str) -> bool:
    if verifier == "semantic":
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in REPOSITORY_OVERCLAIM_PHRASES)


def _trust_envelope(
    *,
    root: Path,
    claim_id: str,
    payload: dict[str, Any],
    dated: str,
    evidence_digest_gap: bool,
) -> dict[str, object]:
    claim = payload.get("claim", {})
    boundary = payload.get("boundary", {})
    carriers = payload.get("carriers", {})
    promotion = payload.get("promotion", {})
    envelope_gaps: list[str] = []

    boundary_owner = _string_value(boundary, "owner")
    boundary_scope = _string_value(boundary, "scope")
    openspec_carrier = _string_value(carriers, "openspec")
    fallback = _string_value(payload, "fallback") or _string_value(carriers, "fallback")
    kill_signal = _string_value(payload, "kill_signal") or _string_value(carriers, "kill_signal")
    promotion_targets = _promotion_targets(promotion)

    if not boundary_owner:
        envelope_gaps.append("boundary.owner_missing")
    if not boundary_scope:
        envelope_gaps.append("boundary.scope_missing")
    if not openspec_carrier:
        envelope_gaps.append("carriers.openspec_missing")
    elif not (root / openspec_carrier).exists():
        envelope_gaps.append(f"carriers.openspec_missing_path:{openspec_carrier}")
    if not fallback:
        envelope_gaps.append("fallback_missing")
    if not kill_signal:
        envelope_gaps.append("kill_signal_missing")
    if not promotion_targets:
        envelope_gaps.append("promotion.targets_missing")
    for target in promotion_targets:
        if not (root / target["path"]).exists():
            envelope_gaps.append(f"promotion_target_missing:{target['path']}")
    if evidence_digest_gap:
        envelope_gaps.append("evidence.digest_untrusted")

    return {
        "claim_id": claim_id,
        "state": claim.get("state", ""),
        "boundary": {
            "owner": boundary_owner,
            "scope": boundary_scope,
        },
        "evidence": {
            "dated": dated,
            "digest_trusted": not evidence_digest_gap,
            "commands": _list_value(payload.get("evidence", {}), "tests"),
        },
        "carriers": {
            "openspec": openspec_carrier,
        },
        "fallback": fallback,
        "kill_signal": kill_signal,
        "promotion": {
            "targets": promotion_targets,
            "ready": bool(promotion_targets)
            and not any(gap.startswith("promotion_target_missing:") for gap in envelope_gaps),
        },
        "required_gaps": envelope_gaps,
    }


def claims_report(root: Path, *, current_head: str = "") -> dict[str, object]:
    claims_dir = root / "claims"
    gaps: list[str] = []
    advisory_gaps: list[str] = []
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
        is_active = claim.get("state") == "active"
        if is_active:
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
                claim_text = "\n".join((summary, str(binding)))
                # change_id must reference the Change this claim binds evidence to —
                # NOT the Subject. Piping subject into change_id collapsed the
                # Subject->Change->Claim boundary (kernel double-representation). Use
                # an explicit change_id, falling back to the claim's own id.
                try:
                    EvidenceClaim(
                        id=claim_id,
                        change_id=str(claim.get("change_id") or claim_id),
                        evidence_ids=tuple(str(item) for item in evidence_ids),
                        binding=claim_text,
                        verifier=str(verifier),
                    )
                except ValueError:
                    gaps.append(f"{claim_id}:semantic_overclaim_requires_semantic_verifier")
                if _has_repository_overclaim(claim_text, str(verifier)):
                    gaps.append(f"{claim_id}:semantic_overclaim_requires_semantic_verifier")
        evidence_path = root / str(dated)
        if not evidence_path.exists():
            gaps.append(f"{claim_id}:evidence_file_missing:{dated}")
            continue
        actual_digest = _sha256(evidence_path)
        evidence_digest_gap = False
        if not expected_digest:
            gaps.append(f"{claim_id}:evidence.sha256_missing")
            evidence_digest_gap = True
        elif expected_digest != actual_digest:
            gaps.append(f"{claim_id}:evidence.sha256_mismatch")
            evidence_digest_gap = True
        # HEAD-binding: a digest proves the narrative file is unchanged, NOT that the
        # claim is current for the product state it asserts about. An active claim
        # should record the product HEAD it was proven at. A DECLARED-but-mismatched
        # head is a stale claim (blocking); an unbound legacy claim is surfaced as
        # advisory so the fleet can be migrated without a hard break.
        claim_head = str(evidence.get("head", ""))
        if is_active and current_head:
            if claim_head and claim_head != current_head:
                gaps.append(f"{claim_id}:evidence.head_stale:{claim_head}!={current_head}")
            elif not claim_head:
                advisory_gaps.append(f"{claim_id}:evidence.head_unbound")
        trust_envelope = (
            _trust_envelope(
                root=root,
                claim_id=claim_id,
                payload=payload,
                dated=str(dated),
                evidence_digest_gap=evidence_digest_gap,
            )
            if is_active
            else {}
        )
        for gap in trust_envelope.get("required_gaps", []):
            gaps.append(f"{claim_id}:{gap}")
        claims[claim_id] = {
            "path": path.relative_to(root).as_posix(),
            "evidence": str(dated),
            "sha256": expected_digest,
            "actual_sha256": actual_digest,
            "state": claim.get("state", ""),
            "trust_envelope": trust_envelope,
        }
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "advisory_gaps": advisory_gaps,
        "claims": claims,
    }
