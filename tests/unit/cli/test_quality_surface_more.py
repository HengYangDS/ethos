from __future__ import annotations

import json
from pathlib import Path

import ethos.surface.cli.quality.core as q
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw


def _capture(monkeypatch):
    emitted = []

    def capture_emit(result, *, json_output=False, enforce=True):
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(q, "emit", capture_emit)
    monkeypatch.setattr(q.tool_results, "emit", capture_emit)
    monkeypatch.setattr(q, "resolve_root", lambda root: root or Path.cwd())
    return emitted


def test_quality_tool_surfaces_delegate_to_configured_adapter(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(q.git_adapter, "git_files", lambda _repo, *patterns: [f"file{patterns[0]}"])

    def fake_report(**kwargs):
        return {"ok": True, "required_gaps": [], "state": "passed", **kwargs}

    monkeypatch.setattr(q.tool_results, "quality_tool_report", fake_report)
    q.markdown_links(root=tmp_path, json_output=True)
    q.shell_quality(root=tmp_path, json_output=True)
    q.toml_quality(root=tmp_path, json_output=True)
    q.yaml_quality(root=tmp_path, json_output=True)

    commands = [item["command"] for item in emitted]
    assert commands == [
        "quality markdown-links",
        "quality shell",
        "quality toml",
        "quality yaml",
    ]
    assert emitted[0]["data"]["tool"] == "lychee"
    assert emitted[1]["data"]["command"][:2] == [
        "bash",
        "tools/ci/scripts/run-shell-lint.sh",
    ]
    assert emitted[2]["data"]["command"][:2] == [
        "bash",
        "tools/ci/scripts/run-config-lint.sh",
    ]
    assert emitted[3]["data"]["command"][:2] == [
        "bash",
        "tools/ci/scripts/run-config-lint.sh",
    ]


def test_quality_code_size_and_npm_project_reports(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q.prove_domain,
        "code_size_report",
        lambda _repo: {"ok": False, "required_gaps": ["too_big"]},
    )
    monkeypatch.setattr(
        q,
        "module_layout_report",
        lambda _repo: {
            "ok": False,
            "state": "blocked",
            "summary": {"suffix_module_count": 1},
            "required_gaps": ["module_layout_suffix_module:x"],
        },
    )
    monkeypatch.setattr(
        q.tool_results,
        "quality_tool_report",
        lambda **kwargs: {"ok": False, "required_gaps": ["npm_bad"], **kwargs},
    )
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    q.code_size(root=tmp_path, json_output=True)
    q.module_layout(root=tmp_path, json_output=True)
    q.npm_quality(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality code-size"
    assert emitted[0]["state"] == "blocked"
    assert emitted[0]["required_gaps"] == ["too_big"]
    assert emitted[1]["command"] == "quality module-layout"
    assert emitted[1]["state"] == "blocked"
    assert emitted[1]["summary"] == {"suffix_module_count": 1}
    assert emitted[2]["command"] == "quality npm"
    assert emitted[2]["data"]["files"] == ["package.json"]


def test_quality_release_commit_sbom_and_attestation_surfaces(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q,
        "signature_policy_report",
        lambda _repo: {
            "required_gaps": [],
            "head_subject_ok": False,
            "head_signature_ok": False,
        },
    )
    monkeypatch.setattr(
        q.repository_audit_module,
        "release_files_report",
        lambda _repo: {"ok": False, "missing": ["LICENSE"]},
    )
    monkeypatch.setattr(
        q,
        "release_policy_report",
        lambda _repo: {
            "ok": False,
            "required_gaps": ["policy_gap"],
            "host_profile": {"provider": "gitlab"},
        },
    )
    monkeypatch.setattr(q, "sbom_projection", lambda _repo: {"packages": [{"name": "ethos"}]})
    monkeypatch.setattr(q.git_adapter, "current_head", lambda _repo: "abc123")

    def fake_release_attestation(root, head, evidence_digest):
        return {"predicate": {"tag": "v1"}, "head": head, "digest": evidence_digest}

    monkeypatch.setattr(q, "release_attestation", fake_release_attestation)

    q.commits(enforce_head=True, root=tmp_path, json_output=True)
    q.release(root=tmp_path, json_output=True)
    q.release_policy(root=tmp_path, json_output=True)
    q.sbom(root=tmp_path, json_output=True)
    q.release_attestation_command(evidence_digest="sha256:x", root=tmp_path, json_output=True)

    assert emitted[0]["required_gaps"] == [
        "head_subject_not_conventional",
        "head_signature_not_good",
    ]
    assert emitted[1]["command"] == "quality release"
    assert emitted[1]["next_actions"] == [
        "uv build --all-packages --out-dir build/artifacts/python --clear"
    ]
    assert emitted[2]["command"] == "quality release-policy"
    assert emitted[2]["next_actions"] == ["ethos quality release-attestation"]
    assert emitted[3]["summary"] == {"package_count": 1}
    assert emitted[4]["summary"] == {"tag": "v1"}


def test_quality_coverage_reports_policy_and_latest_artifact(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    report = {
        "ok": True,
        "state": "clean",
        "policy": {"current_hard_floor": 95.0},
        "latest_artifact": {"line_percent": 96.0},
        "required_gaps": [],
    }
    monkeypatch.setattr(q, "coverage_quality_report", lambda _repo: report)

    q.coverage(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality coverage"
    assert emitted[0]["ok"] is True
    assert emitted[0]["summary"] == {
        "current_hard_floor": 95.0,
        "latest_line_percent": 96.0,
        "writer_active": False,
    }
    assert emitted[0]["data"] == report


def test_quality_coverage_surfaces_active_writer(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    report = {
        "ok": True,
        "state": "in_progress",
        "policy": {"current_hard_floor": 95.0},
        "latest_artifact": {"line_percent": None, "writer_active": True},
        "required_gaps": [],
        "advisory_gaps": [
            "coverage_artifact_writer_active:build/evidence/quality/tests/coverage/.write.lock"
        ],
    }
    monkeypatch.setattr(q, "coverage_quality_report", lambda _repo: report)

    q.coverage(root=tmp_path, json_output=True)

    assert emitted[0]["state"] == "in_progress"
    assert emitted[0]["summary"] == {
        "current_hard_floor": 95.0,
        "latest_line_percent": None,
        "writer_active": True,
    }
    assert emitted[0]["required_gaps"] == []


def test_quality_docstrings_reports_policy_coverage(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    report = {
        "ok": False,
        "state": "blocked",
        "coverage_percent": 50.0,
        "fail_under": 95.0,
        "documented_count": 1,
        "public_count": 2,
        "missing": [
            {
                "path": "pkg/mod.py",
                "qualified_name": "mod.public",
                "kind": "function",
                "line": 3,
            }
        ],
        "required_gaps": ["docstring_coverage_below_minimum:50.00<95.00"],
    }
    monkeypatch.setattr(q, "docstring_coverage_report", lambda _repo: report)

    q.docstrings(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality docstrings"
    assert emitted[0]["ok"] is False
    assert emitted[0]["state"] == "blocked"
    assert emitted[0]["summary"] == {
        "coverage_percent": 50.0,
        "documented_count": 1,
        "public_count": 2,
        "style_issue_count": 0,
        "advisory_missing_count": 0,
    }
    assert emitted[0]["required_gaps"] == ["docstring_coverage_below_minimum:50.00<95.00"]
    assert emitted[0]["data"]["missing"][0]["qualified_name"] == "mod.public"


def test_quality_claims_surfaces_advisory_summary_without_blocking(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(q.git_adapter, "current_head", lambda _repo: "head-123")

    def fake_claims_report(repo, *, current_head=""):
        return {
            "ok": True,
            "required_gaps": [],
            "advisory_gaps": ["sample:evidence.head_unbound"],
            "claims": {"sample": {"state": "active"}},
            "claims_root": "evidence/claims",
        }

    monkeypatch.setattr(q, "claims_report", fake_claims_report)

    q.claims(root=tmp_path, json_output=True)

    assert emitted[0]["ok"] is True
    assert emitted[0]["state"] == "advisory"
    assert emitted[0]["required_gaps"] == []
    assert emitted[0]["summary"] == {
        "claim_count": 1,
        "advisory_gap_count": 1,
    }
    assert emitted[0]["data"]["advisory_gaps"] == ["sample:evidence.head_unbound"]


def test_quality_claim_surfaces_bind_reports_to_current_head(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    seen: dict[str, str] = {}
    monkeypatch.setattr(q.git_adapter, "current_head", lambda _repo: "head-123")

    def fake_claims_report(repo, *, current_head=""):
        seen["claims_repo"] = repo.as_posix()
        seen["claims_head"] = current_head
        return {"ok": True, "required_gaps": [], "advisory_gaps": [], "claims": {}}

    def fake_freshness_report(repo, *, current_head=""):
        seen["freshness_repo"] = repo.as_posix()
        seen["freshness_head"] = current_head
        return {
            "ok": True,
            "summary": {"evidence_roots": ["evidence"]},
            "required_gaps": [],
            "data": {"claims": {}},
        }

    monkeypatch.setattr(q, "claims_report", fake_claims_report)
    monkeypatch.setattr(q, "evidence_freshness_report", fake_freshness_report)

    q.claims(root=tmp_path, json_output=True)
    q.evidence_freshness(root=tmp_path, json_output=True)

    assert emitted[0]["state"] == "clean"
    assert emitted[0]["summary"] == {"claim_count": 0, "advisory_gap_count": 0}
    assert seen == {
        "claims_repo": tmp_path.as_posix(),
        "claims_head": "head-123",
        "freshness_repo": tmp_path.as_posix(),
        "freshness_head": "head-123",
    }
    assert [item["command"] for item in emitted] == [
        "quality claims",
        "quality evidence-freshness",
    ]


def test_quality_provenance_emits_planned_evidence_envelope(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(q.git_adapter, "current_head", lambda _repo: "head-abc")

    q.provenance(objective="closeout proof", root=tmp_path, json_output=True)

    payload = emitted[0]
    assert payload["command"] == "quality provenance"
    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["next_actions"] == ["ethos prove --json"]
    evidence = payload["data"]["evidence"]
    assert evidence["id"] == "ethos:closeout proof"
    assert evidence["head"] == "head-abc"
    assert evidence["runs"][0] == {
        "action_id": "planned-proof",
        "command": ["ethos", "prove", "--json"],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "state": "planned",
        "evidence_class": "proof",
        "verdict": "not_run",
        "trust_bearing": False,
        "diagnostics": [],
        "governance_ref": "",
    }
    assert payload["summary"] == {"evidence_digest": evidence["digest"]}
    assert payload["data"]["provenance"]["subject"][0]["digest"]["sha256"] == evidence["digest"]


def test_quality_commits_enforce_head_keeps_subject_and_signature_gaps_independent(
    monkeypatch,
) -> None:
    emitted = _capture(monkeypatch)
    reports = [
        {"required_gaps": [], "head_subject_ok": False, "head_signature_ok": True},
        {"required_gaps": [], "head_subject_ok": True, "head_signature_ok": False},
    ]
    monkeypatch.setattr(q, "signature_policy_report", lambda _repo: reports.pop(0))

    q.commits(enforce_head=True, json_output=True)
    q.commits(enforce_head=True, json_output=True)

    assert emitted[0]["required_gaps"] == ["head_subject_not_conventional"]
    assert emitted[1]["required_gaps"] == ["head_signature_not_good"]


def test_quality_commits_enforce_head_adds_signature_and_subject_gaps(monkeypatch) -> None:
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q,
        "signature_policy_report",
        lambda _repo: {
            "required_gaps": [],
            "head_subject_ok": False,
            "head_signature_ok": False,
        },
    )

    q.commits(enforce_head=True, json_output=True)

    assert emitted[0]["ok"] is False
    assert emitted[0]["required_gaps"] == [
        "head_subject_not_conventional",
        "head_signature_not_good",
    ]


def test_full_gate_registry_includes_official_openspec_validation() -> None:
    payload = run_ethos("quality", "gates", "--json")

    assert payload["ok"] is True
    assert "self-audit" not in payload["data"]["gates"]
    assert payload["data"]["gates"]["repository-audit"]["command"][1:] == [
        "-m",
        "ethos.cli",
        "audit",
        "--mode",
        "shape",
        "--json",
    ]
    assert payload["data"]["gates"]["openspec"]["command"] == [
        "openspec",
        "validate",
        "--all",
        "--strict",
        "--json",
    ]
    assert payload["data"]["gates"]["python-types"]["command"] == [
        "ethos",
        "quality",
        "types",
        "--json",
    ]


def test_quality_determinism_commands_are_available() -> None:
    for command in (
        ("quality", "command-surface", "--json"),
        ("quality", "format-policy", "--json"),
        ("quality", "projection-drift", "--json"),
        ("quality", "evidence-freshness", "--json"),
        ("quality", "command-examples", "--json"),
        ("quality", "coupling-audit", "--json"),
        ("quality", "docs-registry", "--json"),
        ("quality", "provenance", "--json"),
        ("quality", "claims", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_quality_evidence_freshness_reports_evolution_protocol() -> None:
    payload = run_ethos("quality", "evidence-freshness", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["evolution"]["ok"] is True
    assert payload["data"]["evolution"]["required_gaps"] == []
    assert payload["data"]["topology"]["ok"] is True
    assert payload["data"]["topology"]["layout"]["claims_root"] == "evidence/claims"
    assert payload["data"]["topology"]["layout"]["chronicle_root"] == ("evidence/chronicle")
    assert payload["summary"]["topology_issue_count"] == 0


def test_quality_coupling_audit_reports_git_native_boundary() -> None:
    payload = run_ethos("quality", "coupling-audit", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality coupling-audit"
    assert payload["required_gaps"] == []
    assert payload["data"]["git_native"]["strongly_bound"] is True
    assert payload["data"]["git_native"]["layer"] == "product_semantic_hard_binding"
    assert payload["data"]["openspec_governance"]["layer"] == ("mandatory_governance_dependency")
    assert payload["data"]["openspec_governance"]["not_a_second_command_plane"] is True
    assert payload["data"]["native_protocols"]["layer"] == "native_protocol_binding"
    assert payload["data"]["native_protocols"]["provider_optional"] is False
    assert payload["data"]["release_host_profile"]["provider"] == "gitlab"
    assert payload["data"]["product_toolchain"]["profile"] == "product-toolchain"
    assert payload["data"]["product_toolchain"]["layer"] == ("product_toolchain_binding")
    assert {
        "kind": "schema_validation",
        "target": "data",
        "schema": "coupling-audit.schema.json",
        "ok": True,
        "required_gaps": [],
    } in payload["diagnostics"]
    assert "schema_validation" not in payload["data"]


def test_quality_types_enforces_ty_policy_tiers() -> None:
    completed = run_ethos_raw("quality", "types", "--json")
    payload = json.loads(completed.stdout)

    assert payload["command"] == "quality types"
    packages = payload["data"]["packages"]
    # Zero-tolerance tier packages must report a zero limit; ratchet tiers a baseline.
    # ethos-core absorbs the former ethos-contracts and ethos-quality zero-tolerance
    # packages; ethos remains the ratchet-tier runtime.
    assert packages["packages/ethos-core"]["limit"] == 0
    assert packages["packages/ethos-core"]["tier"] == "zero_tolerance"
    assert packages["packages/ethos"]["tier"] == "ratchet"
    assert packages["packages/ethos"]["limit"] == 63
    assert packages["packages/ethos"]["count"] <= packages["packages/ethos"]["limit"]
    # The gate binds its verdict to exit status (fail-closed): a breach exits non-zero.
    assert completed.returncode == (0 if payload["ok"] else 1)
