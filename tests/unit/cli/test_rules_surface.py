from __future__ import annotations

from pathlib import Path  # noqa: TC003

from ethos.surface.cli import rules as rules_cli


def _capture_emit(monkeypatch):
    emitted = []

    def fake_emit(result, json_output=False, enforce=True):  # noqa: FBT002
        emitted.append(
            {
                "payload": result.to_dict(),
                "json_output": json_output,
                "enforce": enforce,
            }
        )

    monkeypatch.setattr(rules_cli, "emit", fake_emit)
    return emitted


def test_rules_check_surface_emits_kernel_readiness(monkeypatch, tmp_path: Path):
    emitted = _capture_emit(monkeypatch)
    monkeypatch.setattr(rules_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        rules_cli,
        "rules_check_report",
        lambda _repo: {
            "ok": False,
            "coverage_tier": "partial",
            "resolved_rules": [{"id": "mutation"}],
            "required_gaps": ["rule_gap"],
            "next_action_contract": ["fix rules"],
        },
    )

    rules_cli.rules_check(root=tmp_path, json_output=True)

    payload = emitted[0]["payload"]
    assert payload["command"] == "rules check"
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["summary"] == {"coverage_tier": "partial", "rule_count": 1}
    assert payload["required_gaps"] == ["rule_gap"]
    assert emitted[0]["enforce"] is False


def test_rules_eval_surface_binds_head_snapshot_and_attestation(monkeypatch, tmp_path: Path):
    emitted = _capture_emit(monkeypatch)
    monkeypatch.setattr(rules_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(rules_cli._gitio, "current_head", lambda _repo: "abc123")

    def fake_snapshot(repo, **kwargs):
        assert kwargs["head"] == "abc123"
        assert kwargs["changed_paths"] == ("src/app.py",)
        assert kwargs["mutation"] is True
        return {"snapshot": kwargs}

    def fake_report(repo, **kwargs):
        assert kwargs["fact_snapshot"]["snapshot"]["actor"] == "agent"
        return {
            "state": "block",
            "digest": "digest",
            "required_gaps": ["gap"],
            "required_gates": [{"id": "tests"}],
            "next_action_contract": ["run tests"],
        }

    monkeypatch.setattr(rules_cli._plan, "rule_fact_snapshot", fake_snapshot)
    monkeypatch.setattr(rules_cli, "rules_evaluation_report", fake_report)
    monkeypatch.setattr(
        rules_cli._plan,
        "rule_attestation_for_evaluation",
        lambda report, actor, scope: {"actor": actor, "scope": scope, "digest": report["digest"]},
    )

    rules_cli.rules_eval(
        root=tmp_path,
        phase="prewrite",
        changed_path=("src/app.py",),
        mutation=True,
        authorized=True,
        actor="agent",
        scope="repository",
        json_output=True,
    )

    payload = emitted[0]["payload"]
    assert payload["command"] == "rules eval"
    assert payload["state"] == "blocked"
    assert payload["summary"] == {
        "phase": "prewrite",
        "digest": "digest",
        "attestation": {"actor": "agent", "scope": "repository", "digest": "digest"},
    }
    assert payload["required_gaps"] == ["gap"]


def test_rules_coverage_surface_uses_workspace_status_when_changed(monkeypatch, tmp_path: Path):
    emitted = _capture_emit(monkeypatch)
    monkeypatch.setattr(rules_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        rules_cli,
        "workspace_status",
        lambda _repo: {"changed_paths": ["a.py", "docs/guide.md"]},
    )
    monkeypatch.setattr(
        rules_cli,
        "coverage_report",
        lambda _repo, changed_paths: {
            "ok": True,
            "covered_paths": list(changed_paths),
            "uncovered_paths": [],
            "required_gaps": [],
            "next_action_contract": [],
        },
    )

    rules_cli.rules_coverage(root=tmp_path, changed=True, json_output=True)

    payload = emitted[0]["payload"]
    assert payload["command"] == "rules coverage"
    assert payload["state"] == "covered"
    assert payload["summary"] == {"covered_path_count": 2, "uncovered_path_count": 0}
    assert emitted[0]["enforce"] is False


def test_rules_compile_explain_and_exceptions_surfaces(monkeypatch, tmp_path: Path):
    emitted = _capture_emit(monkeypatch)
    monkeypatch.setattr(rules_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(rules_cli, "compile_rules", lambda _repo: {"rules": [{"id": "one"}]})
    monkeypatch.setattr(
        rules_cli,
        "explain_rules_target",
        lambda _repo, target: {"target": target, "next_action_contract": ["read docs"]},
    )
    monkeypatch.setattr(
        rules_cli,
        "policy_exceptions_report",
        lambda _repo: {"ok": False, "required_gaps": ["exception_expired"]},
    )

    rules_cli.rules_compile(root=tmp_path, json_output=True)
    rules_cli.rules_explain("docs/guide.md", root=tmp_path, json_output=True)
    rules_cli.rules_exceptions(root=tmp_path, json_output=True)

    compiled, explained, exceptions = [item["payload"] for item in emitted]
    assert compiled["command"] == "rules compile"
    assert compiled["state"] == "compiled"
    assert compiled["summary"] == {"rule_count": 1}
    assert explained["command"] == "rules explain"
    assert explained["next_actions"] == ["read docs"]
    assert exceptions["command"] == "rules exceptions"
    assert exceptions["ok"] is False
    assert exceptions["required_gaps"] == ["exception_expired"]
