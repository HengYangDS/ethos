from __future__ import annotations

import json

from ethos_adapters import shadow

from tests.support.ethos_cli_runner import run_ethos


def test_parity_ledger_has_no_unclassified_capabilities() -> None:
    payload = run_ethos("parity", "ledger", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "parity ledger"
    assert payload["summary"]["unclassified_count"] == 0
    assert {record["capability"] for record in payload["data"]["records"]} >= {
        "work-lane-lifecycle",
        "proof-evidence-chronicle",
        "campaign-hypothesis-evolution",
        "assistant-playbooks-skills",
        "quality-determinism-local-state",
        "openspec-claims-trust-review",
        "dmgr-domain-contract-profile",
    }


def test_parity_gaps_reports_shadow_gap_without_tracked_evidence(tmp_path) -> None:
    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["command"] == "parity gaps"
    assert "shadow_parity_pending:sample-adopter" in payload["required_gaps"]
    assert len(payload["data"]["pending_packages"]) == len(payload["required_gaps"])


def test_parity_gaps_closes_alphasim_dmgr_from_tracked_evidence() -> None:
    payload = run_ethos("parity", "gaps", "--adopter", "alphasim-dmgr", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == (
        "docs/evidence/parity/alphasim-dmgr-shadow.json"
    )


def test_parity_gaps_uses_tracked_shadow_evidence_to_close_verified_capabilities(
    tmp_path,
) -> None:
    evidence_dir = tmp_path / "docs" / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "adopter": "sample-adopter",
                "target": "/tmp/sample-adopter",
                "generated_on": "2026-07-01",
                "shadow": {"ok": True, "required_gaps": [], "comparison_count": 1},
                "verified_capabilities": [
                    "work-lane-lifecycle",
                    "proof-evidence-chronicle",
                    "campaign-hypothesis-evolution",
                    "assistant-playbooks-skills",
                    "quality-determinism-local-state",
                    "openspec-claims-trust-review",
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == (
        "docs/evidence/parity/sample-adopter-shadow.json"
    )


def test_parity_gaps_rejects_incomplete_shadow_evidence(tmp_path) -> None:
    evidence_dir = tmp_path / "docs" / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(
            {
                "shadow": {"ok": True, "required_gaps": []},
                "verified_capabilities": [
                    "work-lane-lifecycle",
                    "proof-evidence-chronicle",
                    "campaign-hypothesis-evolution",
                    "assistant-playbooks-skills",
                    "quality-determinism-local-state",
                    "openspec-claims-trust-review",
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter" in payload["required_gaps"]
    assert payload["data"]["pending_packages"]


def test_parity_gaps_exposes_concrete_backlog_packages() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    package = payload["data"]["pending_packages"][0]
    assert package["gap"] == "parity_pending:work-lane-lifecycle"
    assert package["capability"] == "work-lane-lifecycle"
    assert package["target_home"] == "ethos-repository + ethos-adapters + ethos-test"
    assert package["required_tests"] == [
        "status/lane/prewrite golden JSON",
        "start lease and execution registry",
        "handoff and closeout dry-run/apply admission",
        "candidate lock and stale-base rejection",
        "foreign lane observe-only protection",
    ]
    assert package["parity_criterion"]
    assert package["rollback_impact"]


def test_parity_shadow_defaults_to_read_only_plan(tmp_path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert payload["data"]["comparisons"]
    assert "ethos quality command-surface --json" in payload["data"]["comparisons"]


def test_parity_shadow_execute_reports_missing_embedded_backend(tmp_path) -> None:
    payload = run_ethos(
        "parity",
        "shadow",
        "--target",
        str(tmp_path),
        "--execute",
        "--timeout-seconds",
        "5",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "different"
    assert any(gap.startswith("embedded_command_failed:") for gap in payload["required_gaps"])


def test_shadow_embedded_runner_accepts_pixi_task_in_pyproject(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[tool.pixi.tasks]
ethos = "python -m ethos.cli"
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], str]] = []

    def fake_run_json_command(
        command: list[str],
        *,
        cwd,
        timeout_seconds: int,
    ) -> dict[str, object]:
        calls.append((command, cwd.as_posix()))
        return {
            "exit_code": 0,
            "stdout": '{"ok": true, "command": "status", "state": "ready"}',
            "stderr": "",
            "json": {"ok": True, "command": "status", "state": "ready"},
        }

    monkeypatch.setattr(shadow, "_run_json_command", fake_run_json_command)

    result = shadow._run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], repo.as_posix())]


def test_shadow_json_verdict_exit_code_one_is_not_infrastructure_failure(
    tmp_path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text("", encoding="utf-8")
    payload = {"ok": False, "command": "status", "state": "blocked", "required_gaps": ["x"]}

    def fake_run_json_command(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "exit_code": 1,
            "stdout": json.dumps(payload),
            "stderr": "",
            "json": payload,
        }

    monkeypatch.setattr(shadow, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(shadow, "_run_json_command", fake_run_json_command)

    report = shadow.run_shadow_parity(repo, timeout_seconds=5)

    assert report["ok"] is True
    assert not any(gap.startswith("external_command_failed:") for gap in report["required_gaps"])
    assert not any(gap.startswith("embedded_command_failed:") for gap in report["required_gaps"])


def test_shadow_semantic_diff_compares_plan_gate_dimension() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 1},
        "data": {"required_gates": [{"id": "unit"}]},
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 0},
        "data": {"required_gates": []},
    }

    diff = shadow._semantic_diff(("plan", "--changed"), external, embedded)

    assert diff == {"required_gate_ids": {"external": ["unit"], "embedded": []}}


def test_shadow_status_projection_accepts_embedded_top_level_fields() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root", "dirty": False, "changed_paths": []},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "required_gaps": [],
        "role": "accepted_root",
        "dirty": False,
        "changed_paths": [],
    }

    assert shadow._semantic_diff(("status",), external, embedded) == {}


def test_shadow_report_projection_normalizes_missing_blocking_gap_count() -> None:
    external = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
    embedded = {
        "ok": True,
        "command": "report",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
        "scorecards": [{"id": "governance", "ok": True, "required_gaps": []}],
    }

    assert shadow._semantic_diff(("report",), external, embedded) == {}


def test_shadow_playbooks_projection_ignores_schema_specific_route_details() -> None:
    external = {
        "ok": True,
        "command": "playbooks route",
        "state": "routed",
        "required_gaps": [],
        "data": {"selected": [{"id": "repo-local-skill"}]},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "required_gaps": [],
        "route_hints": [],
    }

    assert shadow._semantic_diff(("playbooks", "route", "--changed"), external, embedded) == {}


def test_shadow_parse_failure_is_process_failure() -> None:
    result = {
        "exit_code": 0,
        "stdout": "not json",
        "stderr": "",
        "json": {},
    }

    assert shadow._process_failed(result) is True


def test_shadow_timeout_is_process_failure() -> None:
    result = {
        "exit_code": 124,
        "stdout": "",
        "stderr": "timeout",
        "json": {},
    }

    assert shadow._process_failed(result) is True
