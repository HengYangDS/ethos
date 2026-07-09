from __future__ import annotations

import hashlib
import re
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.profile import profile_root
from ethos_core.contracts.package.ontology import RETIRED_PRODUCT_FAMILY_TOKENS
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


def _has_repository_overclaim(text: str, verifier: str) -> bool:
    if verifier == "semantic":
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in REPOSITORY_OVERCLAIM_PHRASES)


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


def _payload_text(value: object) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{key}={_payload_text(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return "\n".join(_payload_text(item) for item in value)
    return str(value)


def _normalized_digest(value: object) -> str:
    digest = str(value or "")
    return digest.removeprefix("sha256:")


def _change_claim_record(
    *,
    root: Path,
    path: Path,
    payload: dict[str, Any],
    gaps: list[str],
) -> tuple[str, dict[str, object]]:
    claim_id = str(payload.get("id") or path.stem)
    lifecycle = str(payload.get("lifecycle") or "")
    refs = payload.get("evidence_refs")
    requires_evidence = lifecycle in {"evidence_closed", "promoted", "closed", "accepted"}
    if not isinstance(refs, list) or not refs:
        if requires_evidence:
            gaps.append(f"{claim_id}:evidence_refs_missing")
        refs = []
    artifacts: list[dict[str, object]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            gaps.append(f"{claim_id}:evidence_ref_invalid:{index}")
            continue
        artifact = str(ref.get("artifact") or "")
        expected_digest = _normalized_digest(ref.get("digest"))
        if not artifact:
            gaps.append(f"{claim_id}:evidence_ref_artifact_missing:{index}")
            continue
        evidence_path = root / artifact
        actual_digest = ""
        if not evidence_path.exists():
            gaps.append(f"{claim_id}:evidence_file_missing:{artifact}")
        else:
            actual_digest = _sha256(evidence_path)
            if expected_digest and expected_digest != actual_digest:
                gaps.append(f"{claim_id}:evidence.sha256_mismatch:{artifact}")
            elif not expected_digest:
                gaps.append(f"{claim_id}:evidence.sha256_missing:{artifact}")
        artifacts.append(
            {
                "artifact": artifact,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "gate": str(ref.get("gate") or ""),
                "head": str(ref.get("head") or ""),
                "verdict": str(ref.get("verdict") or ""),
            }
        )
    for retired in RETIRED_PRODUCT_FAMILY_TOKENS:
        if lifecycle == "active" and retired in claim_id:
            gaps.append(f"{claim_id}:retired_product_family:{retired}")
    return claim_id, {
        "path": path.relative_to(root).as_posix(),
        "evidence": artifacts[0]["artifact"] if artifacts else "",
        "sha256": artifacts[0]["sha256"] if artifacts else "",
        "actual_sha256": artifacts[0]["actual_sha256"] if artifacts else "",
        "state": lifecycle,
        "kind": str(payload.get("kind") or ""),
        "evidence_refs": artifacts,
        "trust_envelope": {},
    }


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
    claims_dir = profile_root(root, "claims")
    gaps: list[str] = []
    advisory_gaps: list[str] = []
    claims: dict[str, dict[str, object]] = {}
    claim_paths = sorted(claims_dir.rglob("*.toml")) if claims_dir.exists() else []
    if not claim_paths:
        gaps.append("claims_missing")
    for path in claim_paths:
        payload = _claim_payload(path)
        if "claim" not in payload and ("id" in payload or "evidence_refs" in payload):
            claim_id, record = _change_claim_record(
                root=root,
                path=path,
                payload=payload,
                gaps=gaps,
            )
            claims[claim_id] = record
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
            gaps.extend(_active_product_claim_private_gaps(claim_id, payload))
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
        "claims_root": claims_dir.relative_to(root.resolve()).as_posix()
        if claims_dir.is_relative_to(root.resolve())
        else str(claims_dir),
        "claims": claims,
    }
