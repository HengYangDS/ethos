"""Build control-plane replacement fixtures and their trusted verification receipts."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import ethos.adapters.admission.control.replacement as replacement
import ethos.adapters.admission.evidence.external as evidence
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path


def control_change(
    tmp_path: Path, path: str = "system/gates.toml", mode: str = "required"
) -> tuple[Path, str, str]:
    repo, candidate = start_adopted_candidate(tmp_path, docs_only=True)
    (repo / "system/gates.toml").rename(repo / ".ethos/fixture-proof.toml")
    profile = repo / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text().replace(
            'gate_registry = "system/gates.toml"',
            'gate_registry = ".ethos/fixture-proof.toml"',
        )
        + f'\n[independent_verification]\nmode = "{mode}"\n',
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    accepted = commit_fixture(repo, "configure independent verification")
    git(candidate, "reset", "--hard", accepted)
    return (
        candidate,
        accepted,
        commit_fixture_file(candidate, path, "candidate control\n", "control"),
    )


def control_report(candidate: Path, accepted: str, head: str, receipt: Path | None = None):
    return replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
        independent_verification_receipt=receipt,
    )


def trusted_receipt(request: dict[str, object], **updates: object) -> Path:
    provider, gaps = evidence.load_independent_verification_provider(
        evidence.default_provider_config_path()
    )
    assert provider is not None
    assert not gaps
    now = datetime.now(UTC)
    receipt = IndependentVerificationReceipt.model_validate(
        {
            **request,
            "implementation_digest": provider.implementation_digest,
            "result": "pass",
            "issuer": "provider:example",
            "key_id": "provider:example",
            "signature_algorithm": "ssh-ed25519",
            "signature": "signed",
            "issued_at": now,
            "valid_until": now + timedelta(minutes=5),
            "payload_digest": "",
            **updates,
        }
    )
    receipt = receipt.model_copy(update={"payload_digest": receipt.canonical_payload_digest()})
    path = provider.receipt_store / "receipt.json"
    path.write_text(json.dumps(receipt.model_dump(mode="json")))
    return path
