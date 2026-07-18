from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.rules import PolicyException
from tests.unit.kernel.rules.snapshots import complete_snapshot


def test_policy_exceptions_validate_required_owner_scope_ttl_and_digest(tmp_path: Path) -> None:
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        """
[[exception]]
id = "expired"
rule_id = "starter.docs"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-01-01"
expires_at = "2026-01-03"
status = "active"
max_ttl = "1d"
digest = "0"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_expired:expired" in report["required_gaps"]
    assert "policy_exception_digest_mismatch:expired" in report["required_gaps"]
    assert "policy_exception_ttl_exceeded:expired" in report["required_gaps"]
    assert (
        "policy_exception_evidence_missing:expired:evidence/example.md" in report["required_gaps"]
    )


def test_policy_exceptions_block_invalid_dates_and_non_waivable_rules(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence" / "example.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence\n", encoding="utf-8")
    invalid_date = PolicyException(
        id="invalid-date",
        rule_id="starter.docs",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="never",
    ).to_dict()
    non_waivable = PolicyException(
        id="non-waivable",
        rule_id="starter.governance",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "invalid-date"
rule_id = "starter.docs"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "never"
status = "active"
digest = "{invalid_date["digest"]}"

[[exception]]
id = "non-waivable"
rule_id = "starter.governance"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "2026-07-02"
status = "active"
digest = "{non_waivable["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_date_invalid:invalid-date:expires_at" in report["required_gaps"]
    assert (
        "policy_exception_non_waivable_rule:non-waivable:starter.governance"
        in report["required_gaps"]
    )


def test_policy_exceptions_block_empty_path_scope(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence" / "example.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence\n", encoding="utf-8")
    invalid_scope = PolicyException(
        id="empty-path",
        rule_id="starter.docs",
        scope="path:",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "empty-path"
rule_id = "starter.docs"
scope = "path:"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "2026-07-02"
status = "active"
digest = "{invalid_scope["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_scope_invalid:empty-path" in report["required_gaps"]


def test_valid_policy_exception_waives_scoped_blocking_rule(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence" / "exception.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("temporary waiver\n", encoding="utf-8")
    waiver = PolicyException(
        id="docs-waiver",
        rule_id="custom.docs",
        scope="path:notes/",
        owner="docs-team",
        approver="maintainer",
        reason="temporary docs gate migration",
        evidence_ref="evidence/exception.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "docs-waiver"
rule_id = "custom.docs"
scope = "path:notes/"
owner = "docs-team"
approver = "maintainer"
reason = "temporary docs gate migration"
evidence_ref = "evidence/exception.md"
created_at = "2026-07-01"
expires_at = "2026-07-31"
status = "active"
digest = "{waiver["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert report["state"] == "advisory"
    assert "gate_required:custom.docs:docs-registry" not in report["required_gaps"]
    assert report["waivers_applied"] == [
        {
            "id": "docs-waiver",
            "rule_id": "custom.docs",
            "scope": "path:notes/",
            "waived_gaps": ["gate_required:custom.docs:docs-registry"],
        }
    ]
    assert validate_schema_instance("rule-evaluation.schema.json", report)["ok"]


def test_policy_exception_path_scope_respects_path_boundaries(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["docs2/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence" / "exception.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("temporary waiver\n", encoding="utf-8")
    waiver = PolicyException(
        id="docs-waiver",
        rule_id="custom.docs",
        scope="path:docs",
        owner="docs-team",
        approver="maintainer",
        reason="temporary docs gate migration",
        evidence_ref="evidence/exception.md",
        created_at="2026-07-01",
        expires_at="2026-07-02",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "docs-waiver"
rule_id = "custom.docs"
scope = "path:docs"
owner = "docs-team"
approver = "maintainer"
reason = "temporary docs gate migration"
evidence_ref = "evidence/exception.md"
created_at = "2026-07-01"
expires_at = "2026-07-31"
status = "active"
digest = "{waiver["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("docs2/a.md",),
        fact_snapshot=complete_snapshot(changed_paths=("docs2/a.md",)),
    )

    assert report["state"] == "block"
    assert report["waivers_applied"] == []
    assert "gate_required:custom.docs:docs-registry" in report["required_gaps"]
