# ruff: noqa: E501 - source-budget closeout keeps equivalent trust envelopes compact.
from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path  # noqa: TC003 - runtime audit paths remain part of this public boundary
from typing import Any

from ethos.repository.evidence.attestation import AttestationBinding
from ethos.repository.evidence.attestation import semantic_attestation
from ethos.repository.evidence.core import semantic_tree_digest
from ethos.repository.profile import profile_root
from ethos_core.contracts.package.ontology import RETIRED_PRODUCT_FAMILY_TOKENS
from ethos_core.models import EvidenceClaim
from ethos_core.normalization.core import string_list

# fmt: off
REPOSITORY_OVERCLAIM_PHRASES = ("adopter-domain storage", "parity passed", "hosted ci", "remote publication", "published", "verified", "validates", "enforces", "guarantees", "guaranteed", " are retired", " is retired", " are closed", " is closed", "retirement is safe", "backend retirement")
_MAC_HOME_PREFIX = "/" + "Users" + "/"
_HOME_PROJECT_PREFIX = "~" + "/" + "projects"
ACTIVE_PRODUCT_CLAIM_PRIVATE_PATTERNS = (
    ("private_adopter_literal", re.compile(r"\bprivate\s+(?:adopter|profile|repository|project|domain)\s+`?(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b`?|\b(?:adopter|profile)\s*=\s*`?(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b`?|\b--adopter\s+(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b|\bevidence/parity/(?!generic-shadow\.json|<adopter-id>-shadow\.json)[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+-shadow\.json\b|\badopters/(?!<adopter-id>\b|reference-adopter\b|sample-adopter\b|example-adopter\b)[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b", re.IGNORECASE)),
    ("local_workstation_path", re.compile(rf"(?:{re.escape(_MAC_HOME_PREFIX)}|{re.escape(_HOME_PROJECT_PREFIX)}/)[^\s\"']+")),
)
_HISTORICAL_CARRIER_PREFIXES = ("evidence/chronicle/", "openspec/changes/archive/")
_PROMOTION_KINDS = (("evidence/", "evidence"), ("docs/", "docs"), ("schemas/", "schema"), ("openspec/", "openspec"), ("tests/", "tests"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _promotion_kind(path: str) -> str:
    return next((kind for prefix, kind in _PROMOTION_KINDS if path.startswith(prefix)), "source")


def _promotion_targets(payload: dict[str, Any]) -> list[dict[str, str]]:
    value = payload.get("targets")
    if not isinstance(value, list):
        return []
    targets = []
    for item in value:
        path = str(item.get("path") or "") if isinstance(item, dict) else str(item)
        if path:
            targets.append({"kind": str(item.get("kind") or _promotion_kind(path)) if isinstance(item, dict) else _promotion_kind(path), "path": path})
    return targets


def _semantic_scope_paths(*, claim_path: str, dated_evidence_path: str, promotion_targets: list[dict[str, str]]) -> tuple[str, ...]:
    """Return current semantic targets, excluding self-describing history carriers."""
    excluded = {claim_path, dated_evidence_path}
    return tuple(sorted({target["path"] for target in promotion_targets if target["path"] not in excluded and not target["path"].startswith(_HISTORICAL_CARRIER_PREFIXES)}))


def _freshness_payload(mode: str, state: str, head: str, current_head: str, recorded_digest: str, current_digest: str, paths: tuple[str, ...], gaps: list[str]) -> tuple[dict[str, object], list[str]]:  # noqa: PLR0913, RUF100 - exact freshness evidence dimensions
    return ({"mode": mode, "state": state, "recorded_head": head, "current_head": current_head, "recorded_semantic_sha256": recorded_digest, "current_semantic_sha256": current_digest, "paths": list(paths) if mode == "semantic_scope" else [], "required_gaps": gaps}, gaps)


def _freshness_record(root: Path, claim_path: str, evidence: dict[str, Any], promotion_targets: list[dict[str, str]], current_head: str) -> tuple[dict[str, object], list[str]]:
    """Evaluate the declared relationship between a claim and its evidence freshness."""
    raw = evidence.get("freshness")
    if not isinstance(raw, dict):
        head = str(evidence.get("head") or "")
        gaps = ["freshness_missing"] + ([f"head_stale:{head}!={current_head}"] if current_head and head and head != current_head else [])
        return _freshness_payload("", "invalid", head, current_head, "", "", (), gaps)
    mode, head = str(raw.get("mode") or ""), str(raw.get("head") or "")
    recorded = str(raw.get("semantic_sha256") or "").removeprefix("sha256:")
    paths = _semantic_scope_paths(claim_path=claim_path, dated_evidence_path=str(evidence.get("dated") or ""), promotion_targets=promotion_targets)
    current, gaps = "", []
    if mode == "historical":
        state, gaps = (("invalid", ["historical_freshness_overbound"]) if head or recorded else ("durably_bound", []))
    elif mode == "head_bound":
        if not head:
            state, gaps = "invalid", ["head_missing"]
        elif recorded:
            state, gaps = "invalid", ["head_bound_semantic_digest_forbidden"]
        elif current_head and head != current_head:
            state, gaps = "invalid", [f"head_stale:{head}!={current_head}"]
        else:
            state = "current" if current_head else "uncompared"
    elif mode == "semantic_scope":
        gaps = [gap for gap, present in (("head_missing", head), ("semantic_sha256_missing", recorded), ("semantic_scope_empty", paths)) if not present]
        if gaps or not current_head:
            state = "invalid" if gaps else "uncompared"
        else:
            current = semantic_tree_digest(root, head=current_head, relevant_paths=paths)
            state, gaps = (("invalid", ["semantic_scope_unavailable"]) if not current else ("invalid", ["semantic_scope_stale"]) if current != recorded else ("current", []))
    else:
        state, gaps = "invalid", ["freshness_mode_invalid"]
    return _freshness_payload(mode, state, head, current_head, recorded, current, paths, gaps)


def _payload_text(value: object) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{key}={_payload_text(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return "\n".join(map(_payload_text, value))
    return str(value)


def _active_product_claim_private_gaps(claim_id: str, payload: dict[str, Any]) -> list[str]:
    """Return private adopter, workstation, or project coupling gaps."""
    text = _payload_text(payload)
    return [f"{claim_id}:active_claim_private_coupling:{kind}" for kind, pattern in ACTIVE_PRODUCT_CLAIM_PRIVATE_PATTERNS if pattern.search(text)]


def _has_repository_overclaim(claim_text: str, verifier: str) -> bool:
    """Return whether a non-formal verifier claims repository-wide authority."""
    return verifier != "formally_proven" and any(phrase in claim_text.lower() for phrase in REPOSITORY_OVERCLAIM_PHRASES)


def _active_claim_gaps(claim_id: str, path: Path, payload: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    """Return required trust-envelope gaps intrinsic to one active product claim."""
    claim = payload.get("claim", {})
    gaps = _active_product_claim_private_gaps(claim_id, payload)
    identity = "\n".join((path.stem, str(claim.get("id", "")), str(claim.get("subject", ""))))
    gaps += [f"{claim_id}:retired_product_family:{token}" for token in RETIRED_PRODUCT_FAMILY_TOKENS if token in identity]
    evidence_ids, binding, verifier = evidence.get("evidence_ids"), evidence.get("binding"), evidence.get("verifier")
    gaps += [gap for gap, valid in ((f"{claim_id}:evidence_ids_missing", isinstance(evidence_ids, list) and bool(evidence_ids)), (f"{claim_id}:binding_missing", isinstance(binding, str) and bool(binding)), (f"{claim_id}:verifier_missing", isinstance(verifier, str) and bool(verifier))) if not valid]
    if not isinstance(evidence_ids, list) or not binding or not verifier:
        return gaps
    claim_text = "\n".join((str(claim.get("summary", "")), str(binding)))
    try:
        EvidenceClaim(id=claim_id, change_id=str(claim.get("change_id") or claim_id), evidence_ids=tuple(map(str, evidence_ids)), binding=claim_text, verifier=str(verifier))
    except ValueError:
        gaps.append(f"{claim_id}:claim_assurance_invalid")
    if _has_repository_overclaim(claim_text, str(verifier)):
        gaps.append(f"{claim_id}:claim_assurance_invalid")
    return gaps


def _trust_envelope(*, payload: dict[str, Any], dated: str, evidence_digest_gap: bool, binding: AttestationBinding) -> dict[str, object]:
    claim, boundary, carriers, promotion = (payload.get(key, {}) for key in ("claim", "boundary", "carriers", "promotion"))
    owner, scope, openspec = str(boundary.get("owner") or ""), str(boundary.get("scope") or ""), str(carriers.get("openspec") or "")
    fallback = str(payload.get("fallback") or carriers.get("fallback") or "")
    kill_signal = str(payload.get("kill_signal") or carriers.get("kill_signal") or "")
    targets, attestation = _promotion_targets(promotion), semantic_attestation(payload.get("evidence", {}), binding)
    gaps = string_list(attestation.get("required_gaps"))
    gaps += [gap for gap, present in (("boundary.owner_missing", owner), ("boundary.scope_missing", scope)) if not present]
    if not openspec:
        gaps.append("carriers.openspec_missing")
    elif not (binding[0] / openspec).exists():
        gaps.append(f"carriers.openspec_missing_path:{openspec}")
    gaps += [gap for gap, present in (("fallback_missing", fallback), ("kill_signal_missing", kill_signal), ("promotion.targets_missing", targets)) if not present]
    gaps += [f"promotion_target_missing:{target['path']}" for target in targets if not (binding[0] / target["path"]).exists()]
    if evidence_digest_gap:
        gaps.append("evidence.digest_untrusted")
    tests = payload.get("evidence", {}).get("tests", [])
    return {"claim_id": binding[1], "state": claim.get("state", ""), "boundary": {"owner": owner, "scope": scope}, "evidence": {"dated": dated, "digest_trusted": not evidence_digest_gap, "commands": [str(item) for item in tests if str(item)] if isinstance(tests, list) else []}, "carriers": {"openspec": openspec}, "fallback": fallback, "kill_signal": kill_signal, "promotion": {"targets": targets, "ready": bool(targets) and not any(gap.startswith("promotion_target_missing:") for gap in gaps)}, "semantic_attestation": attestation, "required_gaps": gaps}


def claims_report(root: Path, *, current_head: str = "", adopter_mode: bool = False) -> dict[str, object]:
    """Report claim trust envelopes; an adopter with zero claims yet is not a gap."""
    claims_dir = profile_root(root, "claims")
    gaps, advisory_gaps, claims = [], [], {}
    paths = sorted(claims_dir.rglob("*.toml")) if claims_dir.exists() else []
    if not paths:
        (advisory_gaps if adopter_mode else gaps).append("claims_missing")
    for path in paths:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("claim"), dict):
            gaps.append(f"{path.stem}:claim_envelope_missing")
            continue
        claim, evidence = payload["claim"], payload.get("evidence", {})
        claim_id, dated = str(claim.get("id", path.stem)), evidence.get("dated")
        if not dated:
            gaps.append(f"{claim_id}:evidence.dated_missing")
            continue
        active = claim.get("state") == "active"
        if active:
            gaps += _active_claim_gaps(claim_id, path, payload, evidence)
        targets, evidence_path = _promotion_targets(payload.get("promotion", {})), root / str(dated)
        if not evidence_path.exists():
            gaps.append(f"{claim_id}:evidence_file_missing:{dated}")
            continue
        expected, actual = str(evidence.get("sha256", "")), _sha256(evidence_path)
        digest_gap = not expected or expected != actual
        if digest_gap:
            gaps.append(f"{claim_id}:evidence.sha256_{'missing' if not expected else 'mismatch'}")
        freshness, freshness_gaps = _freshness_record(root, path.relative_to(root).as_posix(), evidence, targets, current_head) if active else ({}, [])
        gaps += [f"{claim_id}:evidence.{gap}" for gap in freshness_gaps]
        envelope = _trust_envelope(payload=payload, dated=str(dated), evidence_digest_gap=digest_gap, binding=(root, claim_id, actual, str(freshness.get("current_semantic_sha256") or ""), current_head)) if active else {}
        gaps += [f"{claim_id}:{gap}" for gap in string_list(envelope.get("required_gaps"))]
        claims[claim_id] = {"path": path.relative_to(root).as_posix(), "evidence": str(dated), "sha256": expected, "actual_sha256": actual, "state": claim.get("state", ""), "trust_envelope": envelope, "freshness": freshness}
    resolved = root.resolve()
    return {"ok": not gaps, "required_gaps": gaps, "advisory_gaps": advisory_gaps, "claims_root": claims_dir.relative_to(resolved).as_posix() if claims_dir.is_relative_to(resolved) else str(claims_dir), "claims": claims}
