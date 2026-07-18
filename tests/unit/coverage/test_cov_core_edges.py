# ruff: noqa: TC003
"""Coverage-closure edge tests for the core cluster (100% no-exemption campaign)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import ethos_core.contracts.system.contracts as system_contracts
from ethos_core import models
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.context.projection import redact_secret_like
from ethos_core.quality.models import QualityFinding
from ethos_core.quality.models import ToolAdapterProfile

# fmt: off


def test_quality_finding_to_dict_serializes_all_fields() -> None:
    # Explicit path: asdict emits every dataclass field as a flat str->str map.
    finding = QualityFinding(
        id="F1",
        severity="error",
        asset_class="python-code",
        dimension="lint",
        message="unused import",
        path="pkg/mod.py",
    )
    assert finding.to_dict() == {
        "id": "F1",
        "severity": "error",
        "asset_class": "python-code",
        "dimension": "lint",
        "message": "unused import",
        "path": "pkg/mod.py",
    }

    # Default path: the optional field falls back to the empty string.
    without_path = QualityFinding(
        id="F2",
        severity="warning",
        asset_class="markdown-docs",
        dimension="links",
        message="dead link",
    )
    serialized = without_path.to_dict()
    assert serialized["path"] == ""
    assert set(serialized) == {
        "id",
        "severity",
        "asset_class",
        "dimension",
        "message",
        "path",
    }
    adapter = ToolAdapterProfile("ruff", "ruff", ("python-code",), ("lint",), "format boundary")
    assert adapter.to_dict()["asset_classes"] == ["python-code"]


def test_redact_secret_like_masks_secret_and_preserves_plain_text() -> None:
    # Matching input: exercises SECRET_LIKE_RE.sub on line 70, replacing the secret.
    redacted = redact_secret_like("here is api_key: abcdef1234567890 end")
    assert redacted == "here is <redacted-secret> end"
    assert "abcdef1234567890" not in redacted

    # AWS-style access key id also triggers the substitution branch.
    assert redact_secret_like("cred AKIAIOSFODNN7EXAMPLE tail") == "cred <redacted-secret> tail"

    # Non-matching input: sub finds nothing and returns the original string unchanged.
    assert redact_secret_like("nothing secret here") == "nothing secret here"


def test_load_branch_role_policy_returns_default_on_malformed_toml(tmp_path: Path) -> None:
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    # Unparseable TOML: unterminated table header triggers tomllib.TOMLDecodeError.
    (ethos_dir / "workspace.toml").write_text("[branch_roles\n", encoding="utf-8")

    result = load_branch_role_policy(tmp_path)

    assert result == BranchRolePolicy()


def test_load_branch_role_policy_falls_back_on_non_string_value(tmp_path: Path) -> None:
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    # Valid TOML, but release_branch is an integer (non-string) so _string_value
    # must return the fallback default rather than the parsed value.
    (ethos_dir / "workspace.toml").write_text(
        "[branch_roles]\nrelease_branch = 123\n", encoding="utf-8"
    )

    result = load_branch_role_policy(tmp_path)

    assert result.release_branch == BranchRolePolicy().release_branch == "main"


def test_require_text_rejects_empty_and_whitespace_only_fields() -> None:
    with pytest.raises(ValueError, match="id must be non-empty"):
        models.Authority(id="", order_ref="anthropic")
    with pytest.raises(ValueError, match="order_ref must be non-empty"):
        models.Authority(id="authority:1", order_ref="   ")


def test_evidence_claim_to_dict_serializes_all_fields() -> None:
    claim = models.EvidenceClaim(
        id="claim:serialize",
        change_id="change:serialize",
        evidence_ids=("evidence:one", "evidence:two"),
        binding="digest binding recorded",
        verifier="digest_only",
    )
    assert claim.to_dict() == {
        "id": "claim:serialize",
        "change_id": "change:serialize",
        "evidence_ids": ["evidence:one", "evidence:two"],
        "binding": "digest binding recorded",
        "verifier": "digest_only",
    }


def test_schema_validation_gaps_returns_empty_when_jsonschema_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the soft `import jsonschema` to raise ImportError even though the
    # package is installed: a None entry in sys.modules makes `import` raise,
    # exercising the pure-leaf zero-hard-dependency fallback (return []).
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"type": "object"}', encoding="utf-8")

    gaps = system_contracts._schema_validation_gaps("authority", {"k": "v"}, schema_path)

    assert gaps == []


def test_schema_validation_gaps_reports_unreadable_schema(tmp_path: Path) -> None:
    # Malformed JSON makes json.loads raise JSONDecodeError (a ValueError
    # subclass), hitting the (ValueError, OSError) unreadable-schema fallback.
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{not json", encoding="utf-8")

    gaps = system_contracts._schema_validation_gaps("authority", {"k": "v"}, schema_path)

    assert len(gaps) == 1
    assert gaps[0].startswith("system_schema_unreadable:authority:")

# fmt: on
