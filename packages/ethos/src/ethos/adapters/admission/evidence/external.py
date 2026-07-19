"""Provider-neutral admission for optional independent verification receipts."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import ValidationError

import ethos.adapters.repo.git as git
from ethos.repository.policy.gates import gate_policy_digest
from ethos.repository.policy.gates import promotion_required_gate_ids
from ethos.repository.profile import independent_verification_policy_table
from ethos_core.contracts.evidence.external import EnforcementReceipt
from ethos_core.contracts.evidence.external import IdentityAssertion
from ethos_core.contracts.evidence.external import IndependentVerificationReceipt
from ethos_core.contracts.rules import stable_digest

_SYSTEM_PROVIDER_CONFIGS = (
    Path("/Library/Application Support/ETHOS/independent-verification.toml"),
    Path("/etc/ethos/independent-verification.toml"),
)
_SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
_BINDING_FIELDS = (
    "remote",
    "commit",
    "tree",
    "action",
    "proof_floor_id",
    "proof_floor_digest",
    "policy_digest",
    "implementation_digest",
)
_MODE_ERROR = "independent verification mode is invalid"
_SHA256_HEX_LENGTH = 64


def external_evidence_report(  # noqa: PLR0913, RUF100 - exact receipt binding dimensions
    *,
    root: Path,
    identity_path: Path | None,
    enforcement_path: Path | None,
    expected_action: str,
    expected_resource: str,
    expected_old: str,
    expected_new: str,
    require_identity: bool,
    require_hosted_enforcement: bool,
) -> dict[str, object]:
    """Verify the optional external identity and hosted-enforcement axes."""
    identity, identity_gaps = _identity_report(identity_path, required=require_identity)
    enforcement, enforcement_gaps = _enforcement_report(
        enforcement_path,
        required=require_hosted_enforcement,
        expected=(expected_action, expected_resource, expected_old, expected_new),
    )
    gaps = [*identity_gaps, *enforcement_gaps]
    return {
        "ok": not gaps,
        "root": root.resolve().as_posix(),
        "identity": identity,
        "enforcement": enforcement,
        "identity_basis": "verified_external_assertion" if identity else "not_evaluated",
        "enforcement_boundary": str(
            enforcement.get("enforcement_boundary") or "local_process_guard"
        ),
        "hosted_prevention_claimed": bool(enforcement.get("hosted_enforcement_proven")),
        "mints_authority": False,
        "required_gaps": gaps,
    }


def _read_mapping(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return cast("dict[str, Any]", payload) if isinstance(payload, dict) else None


def _identity_report(path: Path | None, *, required: bool) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["identity_assertion_required"] if required else []
    try:
        assertion = IdentityAssertion.model_validate(_read_mapping(path))
    except ValidationError:
        return {}, ["identity_assertion_invalid"]
    now = datetime.now(UTC)
    if now < assertion.valid_from:
        return {}, ["identity_assertion_not_yet_valid"]
    if now > assertion.valid_until:
        return {}, ["identity_assertion_expired"]
    return assertion.to_payload(), []


def _enforcement_report(
    path: Path | None,
    *,
    required: bool,
    expected: tuple[str, str, str, str],
) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["hosted_enforcement_receipt_required"] if required else []
    try:
        receipt = EnforcementReceipt.model_validate(_read_mapping(path))
    except ValidationError:
        return {}, ["hosted_enforcement_receipt_invalid"]
    actual = (receipt.action, receipt.resource, receipt.old_value, receipt.new_value)
    if actual != expected:
        return {}, ["hosted_enforcement_receipt_binding_mismatch"]
    return receipt.to_payload(), []


@dataclass(frozen=True, slots=True)
class IndependentVerificationPolicy:
    """Required independent evidence depth for one action."""

    mode: str = "disabled"

    def __post_init__(self) -> None:
        if self.mode not in {"disabled", "optional", "required"}:
            raise ValueError(_MODE_ERROR)


@dataclass(frozen=True, slots=True)
class IndependentVerificationProvider:
    """Host-controlled receipt store and signature anchor."""

    receipt_store: Path
    allowed_signers: Path
    namespace: str
    implementation_digest: str


def _protected(path: Path) -> bool:
    try:
        target = path.resolve(strict=True)
        stats = target.stat(), target.parent.stat()
    except OSError:
        return False
    return all(stat.st_uid != os.geteuid() and not stat.st_mode & 0o022 for stat in stats)


def _provider_failure(kind: str) -> tuple[None, list[str]]:
    return None, [f"independent_verification_provider_config_{kind}"]


def load_independent_verification_provider(
    config_path: Path,
) -> tuple[IndependentVerificationProvider | None, list[str]]:
    """Load protected host configuration without trusting repository state."""
    if not config_path.exists():
        return _provider_failure("missing")
    if not _protected(config_path):
        return _provider_failure("untrusted")
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        store, signature = payload["receipt_store"], payload["signature"]
        receipt_store = Path(store["root"]).expanduser()
        allowed_signers = Path(signature["allowed_signers"]).expanduser()
        namespace = signature["namespace"]
        digest = signature["implementation_digest"]
    except (KeyError, OSError, TypeError, tomllib.TOMLDecodeError):
        return _provider_failure("invalid")
    valid = (
        receipt_store.is_absolute()
        and allowed_signers.is_absolute()
        and isinstance(namespace, str)
        and bool(namespace)
        and isinstance(digest, str)
        and len(digest) == _SHA256_HEX_LENGTH
        and all(char in "0123456789abcdef" for char in digest)
        and receipt_store.is_dir()
        and allowed_signers.is_file()
        and _protected(receipt_store)
        and _protected(allowed_signers)
    )
    if not valid:
        return _provider_failure("invalid")
    return IndependentVerificationProvider(
        receipt_store.resolve(), allowed_signers.resolve(), namespace, digest
    ), []


def _default_provider_config_path() -> Path:
    return next(
        (path for path in _SYSTEM_PROVIDER_CONFIGS if path.exists()), _SYSTEM_PROVIDER_CONFIGS[0]
    )


def _verify_signature(
    receipt: IndependentVerificationReceipt, provider: IndependentVerificationProvider
) -> bool:
    if not _SSH_KEYGEN.is_file() or not os.access(_SSH_KEYGEN, os.X_OK):
        return False
    payload = receipt.model_dump(mode="json", exclude={"signature", "payload_digest"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as signature:
            signature.write(receipt.signature)
            signature.flush()
            result = subprocess.run(
                (
                    _SSH_KEYGEN.as_posix(),
                    "-Y",
                    "verify",
                    "-f",
                    provider.allowed_signers.as_posix(),
                    "-I",
                    receipt.key_id,
                    "-n",
                    provider.namespace,
                    "-s",
                    signature.name,
                ),
                input=canonical,
                capture_output=True,
                check=False,
                timeout=5,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def independent_verification_policy(root: Path, action: str) -> IndependentVerificationPolicy:
    """Load action-scoped policy with a default-disabled posture."""
    return IndependentVerificationPolicy(**independent_verification_policy_table(root, action))


def independent_verification_request(*, root: Path, action: str) -> dict[str, object]:
    """Bind an independent receipt request to current Git and gate facts."""
    commit = git.current_head(root)
    floor = promotion_required_gate_ids(root)
    return {
        "remote": git.git_stdout(root, "remote", "get-url", "origin"),
        "commit": commit,
        "tree": git.git_stdout(root, "rev-parse", f"{commit}^{{tree}}") if commit else "",
        "action": action,
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": stable_digest({"gate_ids": sorted(floor)}),
        "policy_digest": gate_policy_digest(root, tree_ref=commit) if commit else "",
        "implementation_digest": "",
    }


def _report(  # noqa: PLR0913, RUF100 - exact external evidence result dimensions
    root: Path,
    mode: str,
    *,
    ok: bool,
    state: str,
    gaps: list[str] | None = None,
    receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "root": root.resolve().as_posix(),
        "mode": mode,
        "receipt": receipt or {},
        "evidence_class": "independently_reexecuted" if ok and receipt else "local_readiness",
        "mints_authority": False,
        "required_gaps": gaps or [],
        "ok": ok,
        "state": state,
    }


def _read_receipt(path: Path) -> IndependentVerificationReceipt | None:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
        return IndependentVerificationReceipt.model_validate(cast("dict[str, Any]", payload))
    except (OSError, json.JSONDecodeError, ValidationError, TypeError):
        return None


def independent_verification_report(
    *,
    root: Path,
    policy: IndependentVerificationPolicy,
    request: dict[str, object],
    receipt_path: Path | None,
    signature_verifier: Any | None = None,
) -> dict[str, object]:
    """Validate one receipt without upgrading it beyond exact re-execution."""
    mode = policy.mode
    if mode == "disabled":
        return _report(root, mode, ok=True, state="disabled")
    if receipt_path is None:
        return _report(
            root,
            mode,
            ok=mode == "optional",
            state="local_readiness" if mode == "optional" else "blocked",
            gaps=[] if mode == "optional" else ["independent_verification_receipt_required"],
        )
    receipt = _read_receipt(receipt_path)
    if receipt is None:
        return _report(
            root,
            mode,
            ok=False,
            state="invalid",
            gaps=["independent_verification_receipt_invalid"],
        )
    now, gaps = datetime.now(UTC), []
    if receipt.result != "pass":
        gaps.append("independent_verification_receipt_failed")
    if not receipt.issued_at <= now <= receipt.valid_until:
        gaps.append("independent_verification_receipt_stale")
    if any(
        (expected := str(request.get(field) or "")) and getattr(receipt, field) != expected
        for field in _BINDING_FIELDS
    ):
        gaps.append("independent_verification_receipt_binding_mismatch")
    if signature_verifier is None or not bool(signature_verifier(receipt)):
        gaps.append("independent_verification_signature_invalid")
    return _report(
        root,
        mode,
        ok=not gaps,
        state="independently_verified" if not gaps else "invalid",
        gaps=gaps,
        receipt=receipt.to_payload(),
    )


def independent_verification_admission_report(
    *,
    root: Path,
    action: str,
    request: dict[str, object],
    provider_config_path: Path | None = None,
) -> dict[str, object]:
    """Evaluate action policy using only host-local receipt and trust input."""
    policy = independent_verification_policy(root, action)
    configured = os.environ.get("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", "").strip()
    path = Path(configured).expanduser() if configured else None
    if policy.mode == "disabled" or (policy.mode == "optional" and path is None) or path is None:
        return independent_verification_report(
            root=root, policy=policy, request=request, receipt_path=path
        )
    provider, gaps = load_independent_verification_provider(
        provider_config_path or _default_provider_config_path()
    )
    if provider is None:
        return _report(
            root,
            policy.mode,
            ok=False,
            state="blocked" if policy.mode == "required" else "invalid",
            gaps=gaps,
        )
    try:
        path.resolve().relative_to(provider.receipt_store.resolve())
    except ValueError:
        return _report(
            root,
            policy.mode,
            ok=False,
            state="invalid",
            gaps=["independent_verification_receipt_outside_store"],
        )
    return independent_verification_report(
        root=root,
        policy=policy,
        request={**request, "implementation_digest": provider.implementation_digest},
        receipt_path=path,
        signature_verifier=lambda receipt: _verify_signature(receipt, provider),
    )
