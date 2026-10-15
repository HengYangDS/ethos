"""Bind captured native audit evidence to exact sources before fresh acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tomllib
from collections.abc import Callable
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.gate_policy import resolve_committed_gate_declaration
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import AuditPolicy
from ethos.repository.policy.quality.dependency_acceptance import audit_workspace_manifests
from ethos.repository.policy.quality.dependency_acceptance import compose_audit_policies
from ethos.repository.policy.quality.dependency_acceptance import evaluate_dependency_acceptance
from ethos.repository.policy.quality.dependency_acceptance import native_dependency_audit_scope
from ethos.repository.policy.quality.dependency_acceptance import product_audit_projection
from ethos.repository.release.resources import canonical_resource
from ethos.repository.release.resources import packaged_resource

if TYPE_CHECKING:
    from ethos.contracts.proof.plan import AcceptancePurpose
    from ethos.repository.policy.quality.dependency_acceptance import AuditScope
    from ethos.repository.release.identity import BuildIdentity


def product_audit_snapshot(*, build: BuildIdentity) -> tuple[AuditPolicy, dict]:
    """Bind the selected product's portable policy, independently of subject Git inputs."""
    resource = canonical_resource(AUDIT_POLICY_PATH)
    raw = resource.read_bytes()
    projected = product_audit_projection(raw)
    if resource == packaged_resource(AUDIT_POLICY_PATH) and raw != projected:
        message = "dependency_audit_product_policy_noncanonical"
        raise ValueError(message)
    return AuditPolicy.model_validate(tomllib.loads(projected.decode("utf-8"))), {
        "path": AUDIT_POLICY_PATH,
        "sha256": hashlib.sha256(projected).hexdigest(),
        "build": build.projection(),
    }


def _captured_audit_materials(
    stdout: str, head: str, source: Callable[[str], bytes]
) -> tuple[dict, dict, AuditPolicy]:
    """Resolve every observed source to its exact captured hash before interpretation."""
    payload = json.loads(stdout)
    if not isinstance(payload, dict) or payload.get("command") != "dependency-audit":
        message = "dependency_audit_payload_invalid"
        raise ValueError(message)
    if payload.get("head") != head:
        message = "dependency_audit_head_mismatch"
        raise ValueError(message)
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or not set(AUDIT_INPUTS) <= inputs.keys():
        message = "dependency_audit_inputs_missing"
        raise ValueError(message)
    materials = {}
    for name, digest in inputs.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            message = "dependency_audit_input_path_invalid"
            raise ValueError(message)
        value = source(name)
        if not value or hashlib.sha256(value).hexdigest() != digest:
            message = "dependency_audit_inputs_changed"
            raise ValueError(message)
        materials[name] = value
    workspace = {
        manifest
        for lock in ("uv.lock", "package-lock.json")
        for manifest in audit_workspace_manifests(lock, materials[lock])
    }
    if not workspace <= materials.keys():
        message = "dependency_audit_workspace_inputs_missing"
        raise ValueError(message)
    product, binding = product_audit_snapshot(build=invoking_build_identity())
    captured = payload.get("product_policy")
    if not isinstance(captured, dict) or _policy_identity(captured) != _policy_identity(binding):
        message = (
            "dependency_audit_product_policy_changed"
            if "product_policy" in payload
            else "dependency_audit_product_policy_missing"
        )
        raise ValueError(message)
    return payload, materials, product


def _policy_identity(binding: Mapping[str, object]) -> tuple[object, object]:
    """Bind the exact projected product policy; the build that read it is provenance only."""
    return binding.get("path"), binding.get("sha256")


def captured_dependency_acceptance(
    stdout: str,
    *,
    head: str,
    source: Callable[[str], bytes],
    scope: AuditScope,
) -> dict:
    """Read same-attempt native facts, never a build receipt or saved permission."""
    try:
        payload, materials, product = _captured_audit_materials(stdout, head, source)
        policy = AuditPolicy.model_validate(tomllib.loads(materials[AUDIT_POLICY_PATH].decode()))
        return evaluate_dependency_acceptance(
            compose_audit_policies(policy, product),
            payload,
            lock_source=materials["package-lock.json"],
            scope=scope,
            host=platform.node(),
            now=datetime.now(UTC),
            ci=bool(os.environ.get("CI")),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {"scope": scope, "verdict": "unknown", "reason": str(error)}


def dependency_acceptance_gaps(
    root: Path,
    head: str,
    policy: Mapping[str, object],
    checks: tuple[dict, ...],
    *,
    acceptance_purpose: AcceptancePurpose,
) -> list[str]:
    """Reevaluate source permission from already verified content-addressed checks."""
    scope = "local-development" if acceptance_purpose == "local-source" else "production-release"
    gates = policy.get("gates", ())
    if not isinstance(gates, tuple | list):
        return ["proof_dependency_acceptance_audit_missing"]
    audit_ids = {
        str(gate["id"])
        for gate in gates
        if isinstance(gate, Mapping) and native_dependency_audit_scope(gate) == scope
    }
    if not audit_ids:
        if scope != "local-development":
            return []
        try:
            declared = resolve_committed_gate_declaration(root, head)
        except (OSError, ValueError):
            return ["proof_dependency_acceptance_audit_missing"]
        return (
            ["proof_dependency_acceptance_audit_missing"]
            if any(
                native_dependency_audit_scope(gate.model_dump(mode="python")) is not None
                for gate in declared.proof_gates(full=True)
            )
            else []
        )
    selected = tuple(check for check in checks if check.get("action_id") in audit_ids)
    if len(selected) != len(audit_ids):
        return ["proof_dependency_acceptance_audit_missing"]
    gaps = []
    for check in selected:
        decision = captured_dependency_acceptance(
            check["stdout"],
            head=head,
            source=lambda name: committed_file_bytes(root, head, name),
            scope=scope,
        )
        if decision["verdict"] != "pass":
            gaps.append(f"proof_dependency_acceptance:{decision['reason']}")
    return gaps
