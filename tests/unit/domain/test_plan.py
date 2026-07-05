from __future__ import annotations

from ethos.domain import plan


def test_path_matches_supports_prefix_and_glob_patterns():
    assert plan.path_matches("docs/guide.md", "docs/**") is True
    assert plan.path_matches("docs", "docs/**") is True
    assert plan.path_matches("src/app.py", "*.py") is True
    assert plan.path_matches("src/app.py", "src/*.py") is True


def test_matching_rule_gates_filters_invalid_rules_and_projects_gate_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(
        plan,
        "rules_config",
        lambda _root: {
            "gates": {
                "tests": {"command": "pytest", "blocking": True},
                "lint": {"command": "ruff", "blocking": False},
            },
            "rule": [
                "not-a-rule",
                {
                    "id": "python",
                    "risk": "medium",
                    "paths": ["src/**", 7],
                    "requires": ["tests", "lint"],
                    "evidence": ["pytest", 3],
                },
                {"id": "docs", "paths": ["docs/**"], "requires": ["missing"]},
            ],
        },
    )

    matched, gates = plan.matching_rule_gates(tmp_path, ("src/app.py",))

    assert [rule["id"] for rule in matched] == ["python"]
    assert matched[0]["matched_paths"] == ["src/app.py"]
    assert matched[0]["evidence"] == ["pytest", "3"]
    assert gates == [
        {"id": "tests", "command": "pytest", "blocking": True},
        {"id": "lint", "command": "ruff", "blocking": False},
    ]


def test_graph_for_paths_defaults_and_sorts_inputs():
    graph = plan.graph_for_paths(("b.py", "a.py"))
    default_graph = plan.graph_for_paths(())

    assert graph.nodes[0].id == "status"
    assert graph.nodes[0].inputs == ("a.py", "b.py")
    assert graph.nodes[1].command == ("ethos", "prove", "--json")
    assert default_graph.nodes[0].inputs == ("pyproject.toml",)


def test_rule_fact_snapshot_uses_supplied_payloads_and_prewrite_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        plan,
        "claims_report",
        lambda _repo: {"ok": False, "required_gaps": ["claims_missing", "digest_stale:x"]},
    )
    monkeypatch.setattr(
        plan,
        "command_registry_report",
        lambda _repo: {"ok": True, "required_gaps": [], "public_commands": ["ethos status"]},
    )
    monkeypatch.setattr(plan, "projection_contract", lambda: {"truth": plan.ASSISTANT_TRUTH_BOUNDARY})

    snapshot = plan.rule_fact_snapshot(
        tmp_path,
        phase="prewrite",
        head="abc123",
        changed_paths=("src/app.py",),
        mutation=True,
        authorized=True,
        actor="agent",
        scope="repo",
        status_payload={
            "branch": "work/x",
            "role": "work_lane",
            "changed_paths": ["src/app.py"],
            "dirty": True,
            "required_gaps": [],
        },
        prewrite_report={
            "ok": True,
            "role": "work_lane",
            "required_gaps": [],
            "paths": [{"relative_path": "src/app.py"}],
        },
        audit_payload={"mode": "adopter", "ok": True, "required_gaps": [], "openspec": {"ok": True}},
    )

    assert snapshot.phase == "prewrite"
    assert snapshot.head == "abc123"
    assert "ethos-adapters.prewrite" in snapshot.source_refs
    assert snapshot.facts["prewrite"]["value"]["ok"] is True
    assert snapshot.facts["claim_state"]["value"]["ok"] is False
    assert snapshot.facts["claim_state"]["value"]["required_gaps"] == ["digest_stale:x"]
    assert snapshot.facts["projection_drift"]["value"]["ok"] is True


def test_rule_fact_snapshot_marks_missing_prewrite_guard_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(plan, "workspace_status", lambda _repo: {"branch": "dev", "role": "accepted_root"})
    monkeypatch.setattr(plan, "audit_for_root", lambda _repo: {"mode": "product", "ok": True, "required_gaps": []})
    monkeypatch.setattr(plan, "claims_report", lambda _repo: {"ok": True, "required_gaps": []})
    monkeypatch.setattr(plan, "command_registry_report", lambda _repo: {"ok": True, "required_gaps": [], "public_commands": []})
    monkeypatch.setattr(plan, "projection_contract", lambda: {"truth": "wrong"})

    snapshot = plan.rule_fact_snapshot(tmp_path, phase="prewrite", head="head")

    assert snapshot.facts["prewrite"]["available"] is False
    assert snapshot.facts["prewrite"]["fresh"] is False
    assert snapshot.facts["prewrite"]["value"] == {"required_gaps": ["prewrite_guard_not_supplied"]}
    assert snapshot.facts["projection_drift"]["value"]["ok"] is False


def test_rule_fact_snapshot_converts_adapter_failures_to_unavailable_facts(tmp_path, monkeypatch):
    def explode(_repo):
        raise RuntimeError("boom")

    monkeypatch.setattr(plan, "workspace_status", explode)
    monkeypatch.setattr(plan, "audit_for_root", explode)
    monkeypatch.setattr(plan, "claims_report", explode)
    monkeypatch.setattr(plan, "command_registry_report", explode)
    monkeypatch.setattr(plan, "projection_contract", lambda: (_ for _ in ()).throw(RuntimeError("bad")))

    snapshot = plan.rule_fact_snapshot(tmp_path, phase="plan", head="head")

    assert snapshot.facts["worktree"]["available"] is False
    assert snapshot.facts["openspec_state"]["value"]["message"] == "boom"
    assert snapshot.facts["claim_state"]["value"]["error"] == "RuntimeError"
    assert snapshot.facts["command_registry"]["available"] is False
    assert snapshot.facts["projection_drift"]["value"]["message"] == "bad"


def test_rule_attestation_for_evaluation_binds_digest_and_io():
    attestation = plan.rule_attestation_for_evaluation(
        {
            "head": "abc",
            "digest": "eval",
            "rule_set_digest": "rules",
            "compiled_policy_digest": "policy",
            "fact_snapshot_digest": "facts",
            "input_snapshot": {"phase": "plan"},
            "state": "allow",
            "required_gaps": [],
            "required_gates": [{"id": "tests"}],
        },
        actor="codex",
        scope="repository",
    )

    assert attestation["head"] == "abc"
    assert attestation["evaluation_digest"] == "eval"
    assert attestation["runner_identity"] == "ethos-cli"
    assert attestation["output"]["required_gates"] == [{"id": "tests"}]
