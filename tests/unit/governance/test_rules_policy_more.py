from __future__ import annotations

from ethos.repository.policy.rules import check as check_mod
from ethos.repository.policy.rules import evaluation as evaluation_mod
from ethos.repository.policy.rules import explain as explain_mod
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.evaluation import REQUIRED_CORE_FACTS
from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.explain import explain_rules_target
from ethos_core.contracts.rules import PolicyException
from ethos_core.contracts.rules import RuleFactSnapshot


def _fact(owner="test", value=None, *, fresh=True, available=True):
    return {
        "owner": owner,
        "fresh": fresh,
        "available": available,
        "value": {} if value is None else value,
    }


def test_rules_compile_normalizes_legacy_rules_profiles_and_gates(tmp_path):
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    (ethos_dir / "rules.toml").write_text(
        """
[profiles]
active = ["python-package", "strict", "python-package"]

[gates.custom]
command = "echo ok"
blocking = false

[[rule]]
id = "legacy.python"
risk = "python_change"
paths = ["src/**"]
requires = ["custom"]
evidence = ["unit"]
""".strip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)
    legacy = next(rule for rule in compiled["rules"] if rule["id"] == "legacy.python")

    assert compiled["profile_stack"] == ["generic", "python", "strict"]
    assert compiled["coverage_tier"] == "strict"
    assert compiled["gate_definitions"]["custom"] == {
        "id": "custom",
        "command": "echo ok",
        "blocking": False,
    }
    assert legacy["owner"] == "repo-local"
    assert legacy["subject"] == "python_change"
    assert legacy["required_gates"] == ["custom"]
    assert legacy["evidence_requirements"] == ["unit"]


def test_rules_check_reports_parse_duplicate_unknown_gate_and_missing_owner(tmp_path, monkeypatch):
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text("invalid = [\n", encoding="utf-8")
    monkeypatch.setattr(
        check_mod,
        "compile_rules",
        lambda _root: {
            "compile_gaps": ["compiled_gap"],
            "gate_definitions": {},
            "profile_stack": ["generic"],
            "coverage_tier": "starter",
            "rule_set_digest": "rules",
            "compiled_policy_digest": "policy",
            "source_refs": ["test"],
            "rules": [
                {"id": "dup", "owner": "", "required_gates": ["missing"]},
                {"id": "dup", "owner": "owner", "required_gates": []},
            ],
        },
    )

    report = rules_check_report(tmp_path)

    assert report["ok"] is False
    assert any(gap.startswith("rules_config_parse_error:") for gap in report["required_gaps"])
    assert "compiled_gap" in report["required_gaps"]
    assert "duplicate_rule_id:dup" in report["required_gaps"]
    assert "rule_missing_owner:dup" in report["required_gaps"]
    assert "unknown_rule_gate:dup:missing" in report["required_gaps"]


def test_rules_evaluation_blocks_fact_gaps_authorization_and_nonwaivable_obligations(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        evaluation_mod,
        "compile_rules",
        lambda _root: {
            "rule_set_digest": "rules",
            "compiled_policy_digest": "policy",
            "source_refs": ["test"],
            "rules": [{"id": "blocking.rule"}],
        },
    )
    monkeypatch.setattr(evaluation_mod, "rules_check_report", lambda _root: {"required_gaps": []})

    def fake_coverage_report(_root, *, changed_paths):
        return {
            "required_gaps": [],
            "matched_rules": [
                {
                    "rule_id": "blocking.rule",
                    "path": "src/app.py",
                    "blocking": True,
                    "required_gates": ["tests"],
                    "required_gates_detail": [{"id": "tests", "command": "pytest"}],
                    "evidence_requirements": ["proof"],
                    "non_waivable": True,
                }
            ],
        }

    monkeypatch.setattr(evaluation_mod, "coverage_report", fake_coverage_report)
    monkeypatch.setattr(
        evaluation_mod,
        "policy_exceptions_report",
        lambda _root, today=None: {"required_gaps": [], "exceptions": []},  # noqa: ARG005
    )
    facts = {name: _fact(value={"ok": True, "required_gaps": []}) for name in REQUIRED_CORE_FACTS}
    facts["changed_paths"] = _fact(value=["src/app.py"])
    facts["mutation"] = _fact(value=True)
    facts["authorization"] = _fact(value=False)
    facts["actor"] = _fact(value="agent")
    facts["scope"] = _fact(value="repository")
    facts["claim_state"] = _fact(
        value={"ok": False, "required_gaps": ["claim_gap"], "stale": ["claim"]}
    )
    facts["worktree"] = _fact(
        value={"ok": True, "timeout": True, "deterministic": False, "unresolved_conflicts": ["x"]}
    )
    snapshot = RuleFactSnapshot(phase="land", head="abc", facts=facts, source_refs=("test",))

    report = rules_evaluation_report(tmp_path, phase="land", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "authorization_required" in report["required_gaps"]
    assert "fact_not_ok:claim_state" in report["required_gaps"]
    assert "fact_required_gap:claim_state:claim_gap" in report["required_gaps"]
    assert "fact_stale_ref:claim_state:claim" in report["required_gaps"]
    assert "fact_timeout:worktree" in report["required_gaps"]
    assert "gate_required:blocking.rule:tests" in report["required_gaps"]
    assert "evidence_required:blocking.rule:proof" in report["required_gaps"]
    assert {item["kind"] for item in report["obligations"]} >= {
        "require_authorization",
        "require_gate",
        "require_evidence",
    }


def test_rules_evaluation_applies_active_waiver_for_waivable_blocking_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(
        evaluation_mod,
        "compile_rules",
        lambda _root: {
            "rule_set_digest": "r",
            "compiled_policy_digest": "p",
            "source_refs": [],
            "rules": [],
        },
    )
    monkeypatch.setattr(evaluation_mod, "rules_check_report", lambda _root: {"required_gaps": []})

    def fake_coverage_report(_root, *, changed_paths):
        return {
            "required_gaps": [],
            "matched_rules": [
                {
                    "rule_id": "waived.rule",
                    "path": "src/app.py",
                    "blocking": True,
                    "required_gates": ["tests"],
                    "required_gates_detail": [],
                    "evidence_requirements": [],
                    "non_waivable": False,
                }
            ],
        }

    monkeypatch.setattr(evaluation_mod, "coverage_report", fake_coverage_report)
    monkeypatch.setattr(
        evaluation_mod,
        "policy_exceptions_report",
        lambda _root, today=None: {  # noqa: ARG005
            "required_gaps": [],
            "exceptions": [
                {"id": "ex1", "rule_id": "waived.rule", "scope": "path:src", "status": "active"}
            ],
        },
    )
    snapshot = RuleFactSnapshot(
        phase="plan",
        head="abc",
        facts={name: _fact(value={"ok": True, "required_gaps": []}) for name in REQUIRED_CORE_FACTS}
        | {
            "changed_paths": _fact(value=["src/app.py"]),
            "mutation": _fact(value=False),
            "authorization": _fact(value=False),
            "actor": _fact(value="agent"),
            "scope": _fact(value="path:src"),
        },
    )

    report = rules_evaluation_report(tmp_path, phase="plan", fact_snapshot=snapshot)

    assert report["state"] == "advisory"
    assert report["required_gaps"] == []
    assert report["waivers_applied"] == [
        {
            "id": "ex1",
            "rule_id": "waived.rule",
            "scope": "path:src",
            "waived_gaps": ["gate_required:waived.rule:tests"],
        }
    ]


def test_policy_exceptions_report_validates_digest_ttl_scope_and_evidence(tmp_path):
    (tmp_path / "rules" / "ethos").mkdir(parents=True)
    good = PolicyException(
        id="good",
        rule_id="starter.docs",
        scope="path:docs",
        owner="owner",
        approver="approver",
        reason="temporary",
        evidence_ref="evidence/good.md",
        created_at="2026-01-01",
        expires_at="2026-01-10",
        status="active",
        max_ttl="30d",
    ).to_dict()
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "good.md").write_text("ok", encoding="utf-8")
    (tmp_path / "rules" / "ethos" / "policy-exceptions.toml").write_text(
        """
[[exception]]
id = "good"
rule_id = "starter.docs"
scope = "path:docs"
owner = "owner"
approver = "approver"
reason = "temporary"
evidence_ref = "evidence/good.md"
created_at = "2026-01-01"
expires_at = "2026-01-10"
status = "active"
max_ttl = "30d"
digest = "{good_digest}"

[[exception]]
id = "bad"
rule_id = "missing.rule"
scope = "bad-scope"
owner = "owner"
approver = "approver"
reason = "temporary"
evidence_ref = "evidence/missing.md"
created_at = "not-a-date"
expires_at = "2026-03-01"
status = "active"
max_ttl = "xd"
digest = "wrong"
""".format(good_digest=good["digest"]),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-02-01")

    assert report["ok"] is False
    assert "policy_exception_digest_mismatch:bad" in report["required_gaps"]
    assert "policy_exception_unknown_rule:bad:missing.rule" in report["required_gaps"]
    assert "policy_exception_scope_invalid:bad" in report["required_gaps"]
    assert "policy_exception_evidence_missing:bad:evidence/missing.md" in report["required_gaps"]
    assert "policy_exception_date_invalid:bad:created_at" in report["required_gaps"]
    assert "policy_exception_ttl_invalid:bad" in report["required_gaps"]
    assert "policy_exception_expired:good" in report["required_gaps"]


def test_explain_rules_target_for_gap_rule_path_and_skeleton(tmp_path, monkeypatch):
    monkeypatch.setattr(
        explain_mod,
        "compile_rules",
        lambda _root: {"rules": [{"id": "known", "path_globs": ["docs/**"]}]},
    )

    def fake_coverage_report(_root, *, changed_paths):
        return {
            "matched_rules": [],
            "next_action_contract": [],
            "required_gaps": ["rules_uncovered_path:x"],
        }

    monkeypatch.setattr(explain_mod, "coverage_report", fake_coverage_report)

    assert explain_rules_target(tmp_path, "gap:docs/x.md")["kind"] == "gap"
    assert explain_rules_target(tmp_path, "known")["kind"] == "rule"
    path_report = explain_rules_target(tmp_path, "src/new.py")
    assert path_report["kind"] == "path"
    assert path_report["minimal_rule_skeleton"]["path_globs"] == ["src/new.py"]
