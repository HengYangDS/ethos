"""File-based adapters for optional external identity and enforcement receipts."""

from __future__ import annotations

import json
import os
import shutil
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
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.profile import IndependentVerificationPolicy
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

_SYSTEM_PROVIDER_CONFIGS = (
    Path("/Library/Application Support/ETHOS/independent-verification.toml"),
    Path("/etc/ethos/independent-verification.toml"),
)
_SHA256_LENGTH = 64


def _read_mapping(path: Path, gap: str) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, gap
    if not isinstance(payload, dict):
        return {}, gap
    return cast("dict[str, Any]", payload), ""


@dataclass(frozen=True, slots=True)
class IndependentVerificationProvider:
    """Protected host-local facts used to verify an optional provider receipt."""

    receipt_store: Path
    allowed_signers: Path
    namespace: str
    implementation_digest: str
    issuer: str
    key_id: str


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
    issuer = signature_table.get("issuer")
    key_id = signature_table.get("key_id")
    if (
        receipt_store is None
        or allowed_signers is None
        or not isinstance(namespace, str)
        or not namespace
        or not isinstance(issuer, str)
        or not issuer
        or not isinstance(key_id, str)
        or not key_id
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
            issuer=issuer,
            key_id=key_id,
        ),
        [],
    )


def default_provider_config_path() -> Path:
    return next(
        (path for path in _SYSTEM_PROVIDER_CONFIGS if path.exists()),
        _SYSTEM_PROVIDER_CONFIGS[0],
    )


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def verify_independent_receipt_signature(
    receipt: IndependentVerificationReceipt,
    provider: IndependentVerificationProvider,
) -> bool:
    """Verify the receipt's SSH signature against the protected provider anchor."""
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        return False
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as signature_file:
            signature_file.write(receipt.signature)
            signature_file.flush()
            completed = subprocess.run(
                [
                    ssh_keygen,
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
                input=receipt.canonical_payload_bytes(),
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
    profile = load_repository_profile(root)
    if gaps := profile_required_gaps(profile):
        raise ValueError(gaps[0])
    declaration = profile.declaration
    policy = declaration.independent_verification if declaration else None
    selected = policy.mode if policy else "disabled"
    action_policy = getattr(policy.actions, action, None) if policy else None
    return IndependentVerificationPolicy(mode=action_policy.mode if action_policy else selected)


def independent_verification_request(*, root: Path, action: str) -> dict[str, object]:
    """Bind an external re-execution receipt to the current Git proof subject.

    The request contains repository facts only.  In particular, it intentionally
    leaves ``implementation_digest`` blank: the independent provider supplies its
    expected out-of-tree implementation digest from protected provider-local
    configuration, never from an adopter profile or repository environment.
    """
    commit = git.current_head(root)
    tree = git.git_stdout(root, "rev-parse", f"{commit}^{{tree}}") if commit else ""
    policy = resolve_gate_policy(root, tree_ref=commit) if commit else None
    floor = policy.gate_ids if policy else ()
    return {
        "remote": git.git_stdout(root, "remote", "get-url", "origin"),
        "commit": commit,
        "tree": tree,
        "action": action,
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": canonical_json_digest({"gate_ids": sorted(floor)}),
        "policy_digest": policy.digest if policy else "",
        "implementation_digest": "",
    }


def _local_verification_report(
    *, root: Path, policy: IndependentVerificationPolicy
) -> dict[str, object]:
    """Describe receipt evaluation before independently verified evidence exists."""
    return {
        "root": root.resolve().as_posix(),
        "mode": policy.mode,
        "receipt": {},
        "evidence_class": "local_readiness",
        "mints_authority": False,
        "required_gaps": [],
    }


def _absent_receipt_report(
    *, base: dict[str, object], policy: IndependentVerificationPolicy
) -> dict[str, object]:
    """Return the action-policy outcome when no provider receipt was supplied."""
    if policy.mode == "optional":
        return {**base, "verdict": "pass", "state": "local_readiness"}
    return {
        **base,
        "verdict": "unknown",
        "state": "blocked",
        "required_gaps": ["independent_verification_receipt_required"],
    }


def _receipt_validation_gaps(
    *,
    receipt: IndependentVerificationReceipt,
    request: dict[str, object],
    signature_verifier: Any | None,
) -> list[str]:
    """Return deterministic failures for one supplied independent-verification receipt."""
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
        "issuer",
        "key_id",
    ):
        expected = str(request.get(field) or "")
        if expected and getattr(receipt, field) != expected:
            gaps.append("independent_verification_receipt_binding_mismatch")
            break
    if signature_verifier is None or not bool(signature_verifier(receipt)):
        gaps.append("independent_verification_signature_invalid")
    return gaps


def independent_verification_report(
    *,
    root: Path,
    policy: IndependentVerificationPolicy,
    request: dict[str, object],
    receipt_path: Path | None,
    signature_verifier: Any | None = None,
) -> dict[str, object]:
    """Validate one receipt without upgrading it beyond exact re-execution."""
    base = _local_verification_report(root=root, policy=policy)
    if policy.mode == "disabled":
        return {**base, "verdict": "pass", "state": "disabled"}
    if receipt_path is None:
        return _absent_receipt_report(base=base, policy=policy)
    payload, gap = _read_mapping(receipt_path, "independent_verification_receipt_invalid")
    if gap:
        return {**base, "verdict": "block", "state": "invalid", "required_gaps": [gap]}
    try:
        receipt = IndependentVerificationReceipt.model_validate_json(json.dumps(payload))
    except ValidationError:
        return {
            **base,
            "verdict": "block",
            "state": "invalid",
            "required_gaps": ["independent_verification_receipt_invalid"],
        }
    gaps = _receipt_validation_gaps(
        receipt=receipt,
        request=request,
        signature_verifier=signature_verifier,
    )
    return {
        **base,
        "verdict": "block" if gaps else "pass",
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
        provider_config_path or default_provider_config_path()
    )
    if provider is None:
        return {
            "root": root.resolve().as_posix(),
            "mode": policy.mode,
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "verdict": "block",
            "state": "blocked" if policy.mode == "required" else "invalid",
            "required_gaps": provider_gaps,
        }
    if not path_is_within(path, provider.receipt_store):
        return {
            "root": root.resolve().as_posix(),
            "mode": policy.mode,
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "verdict": "block",
            "state": "invalid",
            "required_gaps": ["independent_verification_receipt_outside_store"],
        }
    return independent_verification_report(
        root=root,
        policy=policy,
        request={**request, "implementation_digest": provider.implementation_digest},
        receipt_path=path,
        signature_verifier=lambda receipt: verify_independent_receipt_signature(receipt, provider),
    )
