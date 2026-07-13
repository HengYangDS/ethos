from __future__ import annotations

import hashlib
import re
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.evidence.core import semantic_tree_digest
from ethos.repository.profile import profile_root
from ethos_core.contracts.package.ontology import RETIRED_PRODUCT_FAMILY_TOKENS
from ethos_core.models import EvidenceClaim
from ethos_core.models import canonical_assurance_class
from ethos_core.normalization.core import string_list

if TYPE_CHECKING:
    from pathlib import Path

REPOSITORY_OVERCLAIM_PHRASES = (
    "adopter-domain storage",
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
_MAC_HOME_PREFIX = "/" + "Users" + "/"
_HOME_PROJECT_PREFIX = "~" + "/" + "projects"
ACTIVE_PRODUCT_CLAIM_PRIVATE_PATTERNS = (
    (
        "private_adopter_literal",
        re.compile(
            r"\bprivate\s+(?:adopter|profile|repository|project|domain)\s+`?"
            r"(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)"
            r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b"
            r"`?"
            r"|\b(?:adopter|profile)\s*=\s*`?"
            r"(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)"
            r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b"
            r"`?"
            r"|\b--adopter\s+"
            r"(?!generic\b|reference-adopter\b|sample-adopter\b|example-adopter\b)"
            r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b"
            r"|\bevidence/parity/(?!generic-shadow\.json|<adopter-id>-shadow\.json)"
            r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+-shadow\.json\b"
            r"|\badopters/(?!<adopter-id>\b|reference-adopter\b|sample-adopter\b|example-adopter\b)"
            r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+\b",
            re.IGNORECASE,
        ),
    ),
    (
        "local_workstation_path",
        re.compile(
            rf"(?:{re.escape(_MAC_HOME_PREFIX)}|{re.escape(_HOME_PROJECT_PREFIX)}/)"
            r"[^\s\"']+"
        ),
    ),
)
_FRESHNESS_MODES = {"historical", "head_bound", "semantic_scope"}
_HISTORICAL_CARRIER_PREFIXES = (
    "evidence/chronicle/",
    "openspec/changes/archive/",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_payload(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _promotion_kind(path: str) -> str:
    if path.startswith("evidence/"):
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


def _semantic_scope_paths(
    *,
    claim_path: str,
    dated_evidence_path: str,
    promotion_targets: list[dict[str, str]],
) -> tuple[str, ...]:
    """Return current semantic targets, excluding self-describing history carriers."""
    paths = {
        target["path"]
        for target in promotion_targets
        if target["path"] not in {claim_path, dated_evidence_path}
        and not target["path"].startswith(_HISTORICAL_CARRIER_PREFIXES)
    }
    return tuple(sorted(paths))


def _freshness_record(
    root: Path,
    claim_path: str,
    evidence: dict[str, Any],
    promotion_targets: list[dict[str, str]],
    current_head: str,
) -> tuple[dict[str, object], list[str]]:
    """Evaluate the declared relationship between a claim and its evidence freshness."""
    raw_freshness = evidence.get("freshness")
    if not isinstance(raw_freshness, dict):
        declared_head = str(evidence.get("head") or "")
        record_gaps = ["freshness_missing"]
        if current_head and declared_head and declared_head != current_head:
            record_gaps.append(f"head_stale:{declared_head}!={current_head}")
        return {
            "mode": "",
            "state": "invalid",
            "recorded_head": declared_head,
            "current_head": current_head,
            "recorded_semantic_sha256": "",
            "current_semantic_sha256": "",
            "paths": [],
            "required_gaps": record_gaps,
        }, record_gaps

    mode = str(raw_freshness.get("mode") or "")
    head = str(raw_freshness.get("head") or "")
    recorded_digest = str(raw_freshness.get("semantic_sha256") or "").removeprefix("sha256:")
    paths = _semantic_scope_paths(
        claim_path=claim_path,
        dated_evidence_path=str(evidence.get("dated") or ""),
        promotion_targets=promotion_targets,
    )
    current_digest = ""
    match mode:
        case "historical":
            state, record_gaps = (
                ("invalid", ["historical_freshness_overbound"])
                if head or recorded_digest
                else ("durably_bound", [])
            )
        case "head_bound" if not head:
            state, record_gaps = "invalid", ["head_missing"]
        case "head_bound" if recorded_digest:
            state, record_gaps = "invalid", ["head_bound_semantic_digest_forbidden"]
        case "head_bound" if current_head and head != current_head:
            state, record_gaps = "invalid", [f"head_stale:{head}!={current_head}"]
        case "head_bound":
            state, record_gaps = ("current" if current_head else "uncompared"), []
        case "semantic_scope":
            record_gaps = [
                gap
                for gap, present in (
                    ("head_missing", bool(head)),
                    ("semantic_sha256_missing", bool(recorded_digest)),
                    ("semantic_scope_empty", bool(paths)),
                )
                if not present
            ]
            if record_gaps or not current_head:
                state = "invalid" if record_gaps else "uncompared"
            else:
                current_digest = semantic_tree_digest(root, head=current_head, relevant_paths=paths)
                state, record_gaps = (
                    ("invalid", ["semantic_scope_unavailable"])
                    if not current_digest
                    else ("invalid", ["semantic_scope_stale"])
                    if current_digest != recorded_digest
                    else ("current", [])
                )
        case _:
            state, record_gaps = "invalid", ["freshness_mode_invalid"]
    return {
        "mode": mode,
        "state": state,
        "recorded_head": head,
        "current_head": current_head,
        "recorded_semantic_sha256": recorded_digest,
        "current_semantic_sha256": current_digest,
        "paths": list(paths) if mode == "semantic_scope" else [],
        "required_gaps": record_gaps,
    }, record_gaps


def _active_product_claim_private_gaps(claim_id: str, payload: dict[str, Any]) -> list[str]:
    """Return active-claim gaps for private adopter, workstation, or project literals.

    Historical chronicles and archived OpenSpec records may retain factual names.
    Active product claims are different: they are live trust envelopes. They must
    not require a named private adopter, local workstation path, or private
    project token to understand product authority, evidence, fallback, or
    promotion scope.
    """
    text = _payload_text(payload)
    gaps: list[str] = []
    for kind, pattern in ACTIVE_PRODUCT_CLAIM_PRIVATE_PATTERNS:
        if pattern.search(text):
            gaps.append(f"{claim_id}:active_claim_private_coupling:{kind}")
    return gaps


def _has_repository_overclaim(text: str, verifier: str) -> bool:
    """Return whether a non-formal verifier overclaims repository assurance."""
    return canonical_assurance_class(verifier) != "formally_proven" and any(
        phrase in text.lower() for phrase in REPOSITORY_OVERCLAIM_PHRASES
    )


def _active_claim_gaps(
    claim_id: str, path: Path, payload: dict[str, Any], evidence: dict[str, Any]
) -> list[str]:
    """Return required trust-envelope gaps intrinsic to one active product claim."""
    claim = payload.get("claim", {})
    summary = str(claim.get("summary", ""))
    active_identity = "\n".join(
        [path.stem, str(claim.get("id", "")), str(claim.get("subject", ""))]
    )
    gaps = _active_product_claim_private_gaps(claim_id, payload)
    gaps.extend(
        f"{claim_id}:retired_product_family:{retired}"
        for retired in RETIRED_PRODUCT_FAMILY_TOKENS
        if retired in active_identity
    )
    evidence_ids = evidence.get("evidence_ids")
    binding = evidence.get("binding")
    verifier = evidence.get("verifier")
    gaps.extend(
        gap
        for gap, valid in (
            (
                f"{claim_id}:evidence_ids_missing",
                isinstance(evidence_ids, list) and bool(evidence_ids),
            ),
            (f"{claim_id}:binding_missing", isinstance(binding, str) and bool(binding)),
            (
                f"{claim_id}:verifier_missing",
                isinstance(verifier, str) and bool(verifier),
            ),
        )
        if not valid
    )
    if not isinstance(evidence_ids, list) or not binding or not verifier:
        return gaps
    claim_text = "\n".join((summary, str(binding)))
    try:
        EvidenceClaim(
            id=claim_id,
            change_id=str(claim.get("change_id") or claim_id),
            evidence_ids=tuple(str(item) for item in evidence_ids),
            binding=claim_text,
            verifier=str(verifier),
        )
    except ValueError:
        gaps.append(f"{claim_id}:claim_assurance_invalid")
    if _has_repository_overclaim(claim_text, str(verifier)):
        gaps.append(f"{claim_id}:claim_assurance_invalid")
    return gaps


def _payload_text(value: object) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{key}={_payload_text(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return "\n".join(_payload_text(item) for item in value)
    return str(value)


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

    boundary_owner = str(boundary.get("owner") or "")
    boundary_scope = str(boundary.get("scope") or "")
    openspec_carrier = str(carriers.get("openspec") or "")
    fallback = str(payload.get("fallback") or carriers.get("fallback") or "")
    kill_signal = str(payload.get("kill_signal") or carriers.get("kill_signal") or "")
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

    tests = payload.get("evidence", {}).get("tests", [])
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
            "commands": [str(item) for item in tests if str(item)]
            if isinstance(tests, list)
            else [],
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


def claims_report(
    root: Path, *, current_head: str = "", adopter_mode: bool = False
) -> dict[str, object]:
    """Report claim trust envelopes; an adopter with zero claims yet is not a gap.

    `adopter_mode` reclassifies `claims_missing` from required to advisory: a freshly
    scaffolded adopter has authored no claims yet, and there is no onboarding path that
    fixes that except writing one, so it must not read as blocking.
    """
    claims_dir = profile_root(root, "claims")
    gaps: list[str] = []
    advisory_gaps: list[str] = []
    claims: dict[str, dict[str, object]] = {}
    claim_paths = sorted(claims_dir.rglob("*.toml")) if claims_dir.exists() else []
    if not claim_paths:
        (advisory_gaps if adopter_mode else gaps).append("claims_missing")
    for path in claim_paths:
        payload = _claim_payload(path)
        if not isinstance(payload.get("claim"), dict):
            gaps.append(f"{path.stem}:claim_envelope_missing")
            continue
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
            gaps.extend(_active_claim_gaps(claim_id, path, payload, evidence))
        promotion_targets = _promotion_targets(payload.get("promotion", {}))
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
        freshness = (
            _freshness_record(
                root,
                path.relative_to(root).as_posix(),
                evidence,
                promotion_targets,
                current_head,
            )
            if is_active
            else ({}, [])
        )
        freshness_record, freshness_gaps = freshness
        gaps.extend(f"{claim_id}:evidence.{gap}" for gap in freshness_gaps)
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
        gaps.extend(f"{claim_id}:{gap}" for gap in string_list(trust_envelope.get("required_gaps")))
        claims[claim_id] = {
            "path": path.relative_to(root).as_posix(),
            "evidence": str(dated),
            "sha256": expected_digest,
            "actual_sha256": actual_digest,
            "state": claim.get("state", ""),
            "trust_envelope": trust_envelope,
            "freshness": freshness_record,
        }
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "advisory_gaps": advisory_gaps,
        "claims_root": claims_dir.relative_to(root.resolve()).as_posix()
        if claims_dir.is_relative_to(root.resolve())
        else str(claims_dir),
        "claims": claims,
    }
