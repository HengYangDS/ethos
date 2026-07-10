from __future__ import annotations

from ethos.domain import plan

BOOM_MESSAGE = "boom"


def test_path_matches_supports_prefix_and_glob_patterns():
    assert plan.path_matches("docs/guide.md", "docs/**") is True
    assert plan.path_matches("docs", "docs/**") is True
    assert plan.path_matches("src/app.py", "*.py") is True
    assert plan.path_matches("src/app.py", "src/*.py") is True


def test_matching_rule_gates_filters_invalid_rules_and_projects_gate_metadata(
    tmp_path, monkeypatch
):
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


def test_contract_profile_matches_filters_invalid_profiles_and_contracts(tmp_path, monkeypatch):
    policy = tmp_path / "rules" / "contracts.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        """
[[contract]]
id = "unmatched"
surface = "docs"
paths = ["docs/**"]
protects = ["docs"]
required_evidence = ["markdown"]

[[contract]]
id = "cache"
surface = "cache"
paths = ["packages/cache/**"]
protects = ["cache shape"]
required_evidence = ["cache-tree"]
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        plan,
        "rules_config",
        lambda _root: {
            "contract_profile": [
                "not-a-profile",
                {"id": "missing-policy-key"},
                {"id": "missing-policy-file", "policy": "rules/missing.toml"},
                {"id": "domain", "policy": "rules/contracts.toml"},
            ],
        },
    )

    matches = plan.contract_profile_matches(
        tmp_path,
        ("packages/cache/src/cache/__init__.py",),
    )

    assert matches == [
        {
            "profile": "domain",
            "contract": "cache",
            "surface": "cache",
            "matched_paths": ["packages/cache/src/cache/__init__.py"],
            "protects": ["cache shape"],
            "required_evidence": ["cache-tree"],
        }
    ]


def test_contract_profile_matches_skips_non_table_contract_entries(tmp_path, monkeypatch):
    policy = tmp_path / "rules" / "contracts.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text('contract = ["not-a-contract-table"]\n', encoding="utf-8")
    monkeypatch.setattr(
        plan,
        "rules_config",
        lambda _root: {
            "contract_profile": [{"id": "domain", "policy": "rules/contracts.toml"}],
        },
    )

    assert plan.contract_profile_matches(tmp_path, ("packages/cache/__init__.py",)) == []


def test_graph_for_paths_compiles_declared_workflow_nodes_and_sorts_inputs():
    graph = plan.graph_for_paths(("b.py", "a.py"))
    default_graph = plan.graph_for_paths(())

    assert [node.id for node in graph.nodes] == ["status", "plan", "prove"]
    assert graph.nodes[0].inputs == ("a.py", "b.py")
    assert graph.nodes[1].command == ("ethos", "plan", "--json")
    assert graph.nodes[1].outputs == ("action_graph", "workflow_runtime_read_model")
    assert graph.nodes[2].depends_on == ("plan",)
    assert graph.nodes[2].metadata["source"] == "system/workflows.toml"
    assert default_graph.nodes[0].inputs == ("pyproject.toml",)


def test_rule_fact_snapshot_uses_supplied_payloads_and_prewrite_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        plan,
        "claims_report",
        lambda _repo, *, current_head: {
            "ok": False,
            "head": current_head,
            "required_gaps": ["claims_missing", "digest_stale:x"],
        },
    )
    monkeypatch.setattr(
        plan,
        "command_registry_report",
        lambda _repo: {"ok": True, "required_gaps": [], "public_commands": ["ethos status"]},
    )
    monkeypatch.setattr(
        plan, "projection_contract", lambda: {"truth": plan.ASSISTANT_TRUTH_BOUNDARY}
    )

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
        audit_payload={
            "mode": "adopter",
            "ok": True,
            "required_gaps": [],
            "openspec": {"ok": True},
        },
    )

    assert snapshot.phase == "prewrite"
    assert snapshot.head == "abc123"
    assert "ethos-adapters.prewrite" in snapshot.source_refs
    assert snapshot.facts["prewrite"]["value"]["ok"] is True
    assert snapshot.facts["claim_state"]["value"]["ok"] is False
    assert snapshot.facts["claim_state"]["value"]["required_gaps"] == ["digest_stale:x"]
    assert snapshot.facts["projection_drift"]["value"]["ok"] is True


def test_rule_fact_snapshot_marks_missing_prewrite_guard_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        plan, "workspace_status", lambda _repo: {"branch": "dev", "role": "accepted_root"}
    )
    monkeypatch.setattr(
        plan, "audit_for_root", lambda _repo: {"mode": "product", "ok": True, "required_gaps": []}
    )
    monkeypatch.setattr(
        plan,
        "claims_report",
        lambda _repo, *, current_head: {"ok": True, "head": current_head, "required_gaps": []},
    )
    monkeypatch.setattr(
        plan,
        "command_registry_report",
        lambda _repo: {"ok": True, "required_gaps": [], "public_commands": []},
    )
    monkeypatch.setattr(plan, "projection_contract", lambda: {"truth": "wrong"})

    snapshot = plan.rule_fact_snapshot(tmp_path, phase="prewrite", head="head")

    assert snapshot.facts["prewrite"]["available"] is False
    assert snapshot.facts["prewrite"]["fresh"] is False
    assert snapshot.facts["prewrite"]["value"] == {"required_gaps": ["prewrite_guard_not_supplied"]}
    assert snapshot.facts["projection_drift"]["value"]["ok"] is False


def test_rule_fact_snapshot_converts_adapter_failures_to_unavailable_facts(tmp_path, monkeypatch):
    def explode(_repo):
        raise RuntimeError(BOOM_MESSAGE)

    def explode_claims(_repo, *, current_head: str):
        del current_head
        raise RuntimeError(BOOM_MESSAGE)

    monkeypatch.setattr(plan, "workspace_status", explode)
    monkeypatch.setattr(plan, "audit_for_root", explode)
    monkeypatch.setattr(plan, "claims_report", explode_claims)
    monkeypatch.setattr(plan, "command_registry_report", explode)
    monkeypatch.setattr(
        plan, "projection_contract", lambda: (_ for _ in ()).throw(RuntimeError("bad"))
    )

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


def test_plan_includes_workflow_runtime_projection(tmp_path, monkeypatch):
    monkeypatch.setattr(plan, "workspace_status", lambda _repo: {"changed_paths": ["docs/a.md"]})
    monkeypatch.setattr(plan, "matching_rule_gates", lambda _repo, _paths: ([], []))
    monkeypatch.setattr(plan, "contract_profile_matches", lambda _repo, _paths: [])
    monkeypatch.setattr(
        plan,
        "workflow_runtime_report",
        lambda _repo, changed_paths=(): {
            "ok": True,
            "kind": "workflow_runtime_read_model",
            "truth_boundary": "derived_repository_projection",
            "plan": {"changed_paths": list(changed_paths)},
            "evolution_bridge": {
                "runtime_owns_evolution": False,
                "selection_policy": "evidence_weighted_candidate_comparison",
                "commitment_effect_policy": "practice_claim_declares_create_compose_refine_replace_remove_or_reject_commitment_effect",
            },
            "required_gaps": [],
        },
    )

    paths = ("docs/a.md",)
    graph = plan.graph_for_paths(paths)
    runtime = plan.workflow_runtime_report(tmp_path, changed_paths=paths)

    assert graph.nodes[0].id == "status"
    assert runtime["plan"]["changed_paths"] == ["docs/a.md"]
    assert runtime["evolution_bridge"]["runtime_owns_evolution"] is False
    assert runtime["evolution_bridge"]["commitment_effect_policy"].startswith("practice_claim")


def test_workflow_runtime_report_delegates_to_repository_runtime(tmp_path, monkeypatch):
    paths = ("system/workflows.toml",)
    monkeypatch.setattr(
        plan.workflow_runtime,
        "workflow_runtime_report",
        lambda root, *, changed_paths=(): {
            "root": root,
            "changed_paths": changed_paths,
        },
    )

    runtime = plan.workflow_runtime_report(tmp_path, changed_paths=paths)

    assert runtime == {"root": tmp_path, "changed_paths": paths}
