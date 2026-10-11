"""Bind complete subject inputs and a separate installed product for audit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.repo.dependency_acceptance as acceptance
import ethos.repository.release.resources as resource_owner
import tests
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import product_audit_projection
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_bytes
from ethos.repository.release.identity import packaged_build_identity
from tools.ci import dependency_audit as audit


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bind the real declaration and every required native input in isolation."""
    monkeypatch.delenv("CI", raising=False)
    root = Path(tests.__file__).resolve().parent.parent
    for name in AUDIT_INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    (tmp_path / "package-lock.json").write_text('{"packages":{"":{}}}\n')
    policy = tmp_path / audit.POLICY
    policy.write_text(
        policy.read_text()
        .split("\n[[dispositions]]", 1)[0]
        .replace('finding_action = "report"\n', "")
    )
    package = tmp_path / "product/ethos"
    product = package / "resources" / AUDIT_POLICY_PATH
    product.parent.mkdir(parents=True)
    product.write_bytes(product_audit_projection(policy.read_bytes()))
    identity = package / "resources" / resource_owner.BUILD_IDENTITY_RESOURCE
    identity.parent.mkdir(parents=True)
    identity.write_bytes(
        build_identity_bytes(
            build_identity(product="0.0.0", source_commit="a" * 40, source_tree="b" * 40)
        )
    )
    monkeypatch.setattr(resource_owner, "files", lambda _name: package)
    monkeypatch.setattr(audit, "invoking_build_identity", packaged_build_identity)
    monkeypatch.setattr(acceptance, "invoking_build_identity", packaged_build_identity)
    return tmp_path
