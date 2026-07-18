"""File-based adapters for optional external identity and enforcement receipts."""

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
_SHA256_LENGTH = 64
_INDEPENDENT_VERIFICATION_MODE_ERROR = "independent verification mode is invalid"


def external_evidence_report(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
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
    """Verify only the exact evidence dimensions required by current policy."""
    identity, identity_gaps = _identity_report(identity_path, required=require_identity)
    enforcement, enforcement_gaps = _enforcement_report(
        enforcement_path,
        required=require_hosted_enforcement,
        expected_action=expected_action,
        expected_resource=expected_resource,
        expected_old=expected_old,
        expected_new=expected_new,
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


def _identity_report(path: Path | None, *, required: bool) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["identity_assertion_required"] if required else []
    payload, gap = _read_mapping(path, "identity_assertion_invalid")
    if gap:
        return {}, [gap]
    try:
        assertion = IdentityAssertion.model_validate(payload)
    except ValidationError:
        return {}, ["identity_assertion_invalid"]
    now = datetime.now(UTC)
    if now < assertion.valid_from:
        return {}, ["identity_assertion_not_yet_valid"]
    if now > assertion.valid_until:
        return {}, ["identity_assertion_expired"]
    return assertion.to_payload(), []


def _enforcement_report(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    path: Path | None,
    *,
    required: bool,
    expected_action: str,
    expected_resource: str,
    expected_old: str,
    expected_new: str,
) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["hosted_enforcement_receipt_required"] if required else []
    payload, gap = _read_mapping(path, "hosted_enforcement_receipt_invalid")
    if gap:
        return {}, [gap]
    try:
        receipt = EnforcementReceipt.model_validate(payload)
    except ValidationError:
        return {}, ["hosted_enforcement_receipt_invalid"]
    expected = (expected_action, expected_resource, expected_old, expected_new)
    actual = (receipt.action, receipt.resource, receipt.old_value, receipt.new_value)
    if actual != expected:
        return {}, ["hosted_enforcement_receipt_binding_mismatch"]
    return receipt.to_payload(), []


def _read_mapping(path: Path, gap: str) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, gap
    if not isinstance(payload, dict):
        return {}, gap
    return cast("dict[str, Any]", payload), ""


@dataclass(frozen=True, slots=True)
class IndependentVerificationPolicy:
    """Policy depth for one named action; provider details never appear here."""

    mode: str = "disabled"

    def __post_init__(self) -> None:
        if self.mode not in {"disabled", "optional", "required"}:
            raise ValueError(_INDEPENDENT_VERIFICATION_MODE_ERROR)


@dataclass(frozen=True, slots=True)
class IndependentVerificationProvider:
    """Protected host-local facts used to verify an optional provider receipt."""

    receipt_store: Path
    allowed_signers: Path
    namespace: str
    implementation_digest: str


def _is_protected_from_current_identity(path: Path) -> bool:
    """Return whether `path` and its parent cannot be changed by this process identity."""
    try:
        target = path.resolve(strict=True)
        target_stat = target.stat()
        parent_stat = target.parent.stat()
    except OSError:
        return False
    return (
        target_stat.st_uid != os.geteuid()
        and parent_stat.st_uid != os.geteuid()
        and not target_stat.st_mode & 0o022
        and not parent_stat.st_mode & 0o022
    )


def _absolute_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else None


def _sha256(value: object) -> str:
    return (
        value
        if isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(char in "0123456789abcdef" for char in value)
        else ""
    )


def load_independent_verification_provider(
    config_path: Path,
) -> tuple[IndependentVerificationProvider | None, list[str]]:
    """Load a host-controlled provider configuration without using repository state."""
    if not config_path.exists():
        return None, ["independent_verification_provider_config_missing"]
    if not _is_protected_from_current_identity(config_path):
        return None, ["independent_verification_provider_config_untrusted"]
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None, ["independent_verification_provider_config_invalid"]
    store_table = payload.get("receipt_store")
    signature_table = payload.get("signature")
    if not isinstance(store_table, dict) or not isinstance(signature_table, dict):
        return None, ["independent_verification_provider_config_invalid"]
    receipt_store = _absolute_path(store_table.get("root"))
    allowed_signers = _absolute_path(signature_table.get("allowed_signers"))
    namespace = signature_table.get("namespace")
    implementation_digest = _sha256(signature_table.get("implementation_digest"))
    if (
        receipt_store is None
        or allowed_signers is None
        or not isinstance(namespace, str)
        or not namespace
        or not implementation_digest
        or not receipt_store.is_dir()
        or not allowed_signers.is_file()
        or not _is_protected_from_current_identity(receipt_store)
        or not _is_protected_from_current_identity(allowed_signers)
    ):
        return None, ["independent_verification_provider_config_invalid"]
    return (
        IndependentVerificationProvider(
            receipt_store=receipt_store.resolve(),
            allowed_signers=allowed_signers.resolve(),
            namespace=namespace,
            implementation_digest=implementation_digest,
        ),
        [],
    )


def _default_provider_config_path() -> Path:
    return next(
        (path for path in _SYSTEM_PROVIDER_CONFIGS if path.exists()),
        _SYSTEM_PROVIDER_CONFIGS[0],
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _verify_independent_receipt_signature(
    receipt: IndependentVerificationReceipt,
    provider: IndependentVerificationProvider,
) -> bool:
    """Verify the receipt's SSH signature against the protected provider anchor."""
    if not _SSH_KEYGEN.is_file() or not os.access(_SSH_KEYGEN, os.X_OK):
        return False
    payload = receipt.model_dump(mode="json", exclude={"signature", "payload_digest"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as signature_file:
            signature_file.write(receipt.signature)
            signature_file.flush()
            completed = subprocess.run(
                [
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
                    signature_file.name,
                ],
                input=canonical,
                text=False,
                capture_output=True,
                check=False,
                timeout=5,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def independent_verification_policy(root: Path, action: str) -> IndependentVerificationPolicy:
    """Load the action-scoped policy with a default-disabled adopter posture."""
    return IndependentVerificationPolicy(**independent_verification_policy_table(root, action))


def independent_verification_request(*, root: Path, action: str) -> dict[str, object]:
    """Bind an external re-execution receipt to the current Git proof subject.

    The request contains repository facts only.  In particular, it intentionally
    leaves ``implementation_digest`` blank: the independent provider supplies its
    expected out-of-tree implementation digest from protected provider-local
    configuration, never from an adopter profile or repository environment.
    """
    commit = git.current_head(root)
    tree = git.git_stdout(root, "rev-parse", f"{commit}^{{tree}}") if commit else ""
    floor = promotion_required_gate_ids(root)
    return {
        "remote": git.git_stdout(root, "remote", "get-url", "origin"),
        "commit": commit,
        "tree": tree,
        "action": action,
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": stable_digest({"gate_ids": sorted(floor)}),
        "policy_digest": gate_policy_digest(root, tree_ref=commit) if commit else "",
        "implementation_digest": "",
    }


def independent_verification_report(  # noqa: C901
    *,
    root: Path,
    policy: IndependentVerificationPolicy,
    request: dict[str, object],
    receipt_path: Path | None,
    signature_verifier: Any | None = None,
) -> dict[str, object]:
    """Validate one receipt without upgrading it beyond exact re-execution."""
    base = {
        "root": root.resolve().as_posix(),
        "mode": policy.mode,
        "receipt": {},
        "evidence_class": "local_readiness",
        "mints_authority": False,
        "required_gaps": [],
    }
    if policy.mode == "disabled":
        return {**base, "ok": True, "state": "disabled"}
    if receipt_path is None:
        if policy.mode == "optional":
            return {**base, "ok": True, "state": "local_readiness"}
        return {
            **base,
            "ok": False,
            "state": "blocked",
            "required_gaps": ["independent_verification_receipt_required"],
        }
    payload, gap = _read_mapping(receipt_path, "independent_verification_receipt_invalid")
    if gap:
        return {**base, "ok": False, "state": "invalid", "required_gaps": [gap]}
    try:
        receipt = IndependentVerificationReceipt.model_validate(payload)
    except ValidationError:
        return {
            **base,
            "ok": False,
            "state": "invalid",
            "required_gaps": ["independent_verification_receipt_invalid"],
        }
    now = datetime.now(UTC)
    gaps: list[str] = []
    if receipt.result != "pass":
        gaps.append("independent_verification_receipt_failed")
    if now < receipt.issued_at or now > receipt.valid_until:
        gaps.append("independent_verification_receipt_stale")
    for field in (
        "remote",
        "commit",
        "tree",
        "action",
        "proof_floor_id",
        "proof_floor_digest",
        "policy_digest",
        "implementation_digest",
    ):
        expected = str(request.get(field) or "")
        if expected and getattr(receipt, field) != expected:
            gaps.append("independent_verification_receipt_binding_mismatch")
            break
    if signature_verifier is None or not bool(signature_verifier(receipt)):
        gaps.append("independent_verification_signature_invalid")
    return {
        **base,
        "ok": not gaps,
        "state": "independently_verified" if not gaps else "invalid",
        "receipt": receipt.to_payload(),
        "evidence_class": "independently_reexecuted" if not gaps else "local_readiness",
        "required_gaps": gaps,
    }


def independent_verification_admission_report(
    *,
    root: Path,
    action: str,
    request: dict[str, object],
    provider_config_path: Path | None = None,
) -> dict[str, object]:
    """Evaluate the action-scoped receipt policy using host-local receipt input.

    Receipt location and signature trust are provider configuration, not profile
    truth.  The profile may require the evidence depth, but it cannot smuggle a
    key, account name, or provider path into a governed checkout.
    """
    policy = independent_verification_policy(root, action)
    configured = os.environ.get("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", "").strip()
    path = Path(configured).expanduser() if configured else None
    if policy.mode == "disabled" or (policy.mode == "optional" and path is None):
        return independent_verification_report(
            root=root,
            policy=policy,
            request=request,
            receipt_path=path,
        )
    if path is None:
        return independent_verification_report(
            root=root,
            policy=policy,
            request=request,
            receipt_path=None,
        )
    provider, provider_gaps = load_independent_verification_provider(
        provider_config_path or _default_provider_config_path()
    )
    if provider is None:
        return {
            "root": root.resolve().as_posix(),
            "mode": policy.mode,
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "ok": False,
            "state": "blocked" if policy.mode == "required" else "invalid",
            "required_gaps": provider_gaps,
        }
    if not _is_within(path, provider.receipt_store):
        return {
            "root": root.resolve().as_posix(),
            "mode": policy.mode,
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "ok": False,
            "state": "invalid",
            "required_gaps": ["independent_verification_receipt_outside_store"],
        }
    return independent_verification_report(
        root=root,
        policy=policy,
        request={**request, "implementation_digest": provider.implementation_digest},
        receipt_path=path,
        signature_verifier=lambda receipt: _verify_independent_receipt_signature(receipt, provider),
    )
