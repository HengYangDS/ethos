from __future__ import annotations

import json
from typing import cast

import ethos.domain.report as report_domain
import ethos.domain.reporting.gaps as reporting_gaps
import ethos.domain.reporting.parity.core as reporting_parity
import ethos.domain.reporting.scoring as reporting_scoring
from ethos.repository.evidence.hosted.core import FLAGS
from ethos.repository.evidence.hosted.core import RUN
from ethos.repository.evidence.hosted.core import hosted_observation_report
from ethos.repository.evidence.hosted.core import provider_command
from ethos.repository.evidence.hosted.core import provider_facts
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY
from tests.support.reporting import OK
from tests.support.reporting import patch_scorecard_dependencies


def _quality(monkeypatch, **reports: dict[str, object]) -> None:
    names = "code_size coverage_quality ty_gate docstring_coverage module_layout generated_artifact_topology product_boundary contributor_policy".split()  # noqa: SIM905
    for name in names:
        report = reports.get(f"{name}_report", {"required_gaps": []})
        monkeypatch.setattr(reporting_scoring, f"{name}_report", lambda _repo, value=report: value)


def test_scorecard_next_actions() -> None:
    cases = {
        ("module_layout_flat_growth:x",): ("ethos quality module-layout --json",),
        ("unknown",): ("ethos quality --json",),
        ("identity_mode_missing:x",): ("ethos quality contributor-policy --json",),
        ("generated_artifact_root_cache_drift:.ruff_cache",): (
            "ethos quality generated-artifacts --json",
        ),
        (): ("ethos prove --full",),
        (
            "coverage_latest_below_floor:x",
            "ty_zero_tolerance_violation:x",
            "docstring_coverage_below_minimum:x",
        ): (
            "ethos quality coverage --json",
            "ethos quality types --json",
            "ethos quality docstrings --json",
        ),
    }
    for gaps, expected in cases.items():
        assert (
            reporting_scoring.scorecard_next_actions(
                parity_pending_count=0, hard_quality_floor={"required_gaps": list(gaps)}
            )
            == expected
        )
    for parity, coordination, expected in (
        (1, (), ("ethos parity gaps --adopter <adopter>",)),
        (
            0,
            ("coordination_gap:x",),
            ("ethos orient --json", "ethos lane status --json"),
        ),
    ):
        assert (
            reporting_scoring.scorecard_next_actions(
                parity_pending_count=parity,
                hard_quality_floor={"required_gaps": []},
                coordination_required_gaps=coordination,
            )
            == expected
        )


def test_advisory_next_actions() -> None:
    cases = {
        "work_lane_closeout_residue_present": (
            "ethos orient --json",
            "ethos lane status --json",
        ),
        "sample:evidence.head_unbound": (
            "ethos quality claims --json",
            "ethos quality evidence-freshness --json",
        ),
        "provider_not_configured:github": (
            f"ETHOS_HOSTED_GITHUB_REPO=<host/owner/repo> ETHOS_HOSTED_OBSERVATION_EXECUTE=1 {RUN}",
        ),
        "source_budget_campaign_growth_overage:global_total:2>1": (
            "ethos quality source-budget --json",
        ),
    }
    for gap, expected in cases.items():
        assert reporting_gaps.advisory_next_actions((gap,)) == expected


def test_terminal_and_absent_workflow_runtime_read_models() -> None:
    assert (
        reporting_scoring.terminal_control(
            result_required_gaps=(),
            hard_quality_gap_count=0,
            stage_gates={"authoring_allowed": True, "integration_allowed": False},
        )
        == "partial"
    )
    assert reporting_scoring._workflow_runtime_score(None) is True


def test_adopter_product_root_resolution(monkeypatch, tmp_path) -> None:
    repo, product, configured = (tmp_path / name for name in ("adopter", "product", "configured"))
    for path in (repo, product, configured):
        path.mkdir()
    monkeypatch.setattr(
        reporting_parity,
        "load_repository_profile",
        lambda _repo: type(
            "Profile",
            (),
            {"tables": {"external_backend": {"product_root": "../configured"}}},
        )(),
    )
    assert (
        reporting_parity.adopter_product_root(
            repo, {"runtime_binding": {"runner_source_root": str(product)}}, None
        )
        == product
    )
    for payload in (
        {"runtime_binding": {"runner_source_root": str(repo)}},
        {"runtime_binding": {"runner_source_root": ""}},
    ):
        assert reporting_parity.adopter_product_root(repo, payload, None) == configured
    assert reporting_parity.adopter_product_root(repo, {}, product) == product


def test_scorecard_blocks_hard_quality_floor(monkeypatch, tmp_path) -> None:
    patch_scorecard_dependencies(monkeypatch)
    gap = "code_size_exceeded:tests/unit/product/test_flat.py:999>800"
    monkeypatch.setattr(
        reporting_scoring,
        "hard_quality_floor_report",
        lambda _repo: {"ok": False, "required_gaps": [gap]},
    )

    payload = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is False and payload["required_gaps"] == (gap,)  # noqa: PT018
    assert payload["next_actions"] == ("ethos quality code-size --json",)
    assert payload["data"]["gap_layers"]["hard_quality_floor"]["required_gaps"] == [gap]


def test_scorecard_surfaces_global_compression_separately(monkeypatch, tmp_path) -> None:
    patch_scorecard_dependencies(monkeypatch)
    gap = "source_budget_exceeded:toml:12531>12516"
    monkeypatch.setattr(
        reporting_scoring,
        "global_compression_report",
        lambda _repo: {"ok": False, "required_gaps": [gap]},
    )

    payload = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is True and payload["required_gaps"] == ()  # noqa: PT018
    assert payload["state"] == "advisory"
    assert payload["next_actions"] == ("ethos quality source-budget --json",)
    assert payload["data"]["hard_quality_floor"]["ok"] is True
    layer = payload["data"]["gap_layers"]["global_compression"]
    assert layer["scope"] == "global_compression"
    assert layer["blocking"] is False
    assert layer["ok"] is False
    assert layer["required_gaps"] == [gap]
    assert layer["gap_count"] == 1
    assert layer["invalid_states"]["category_count"] == 1
    assert payload["data"]["advisory_signals"]["advisory_gaps"] == [gap]


def test_scorecard_surfaces_coordination_advisories(monkeypatch, tmp_path) -> None:
    patch_scorecard_dependencies(monkeypatch)
    gaps = ["foreign_work_lane_present", "work_lane_missing_lease:work/orphan"]
    monkeypatch.setattr(
        report_domain,
        "workspace_status",
        lambda _repo, **_kwargs: {"coordination": {"advisory_gaps": gaps}},
    )

    payload = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is True
    assert payload["state"] == "advisory"
    assert payload["summary"]["advisory_gap_count"] == 2
    advisory = payload["data"]["advisory_signals"]
    assert advisory["advisory_gaps"] == gaps
    assert advisory["next_actions"] == [
        "ethos orient --json",
        "ethos lane status --json",
    ]


def test_hard_quality_floor_boundaries(monkeypatch, tmp_path) -> None:
    _quality(monkeypatch, product_boundary_report={"required_gaps": ["product-boundary:x"]})
    floor = reporting_scoring.hard_quality_floor_report(tmp_path)
    assert floor["ok"] is False
    assert reporting_scoring.scorecard_next_actions(
        parity_pending_count=0, hard_quality_floor=floor
    ) == ("ethos quality product-boundary --json",)

    _quality(
        monkeypatch,
        coverage_quality_report={"required_gaps": ["coverage_artifact_missing:x"]},
        ty_gate_report={"required_gaps": ["ty_zero_tolerance_violation:x"]},
        docstring_coverage_report={"required_gaps": ["public_docstring_missing:x"]},
        generated_artifact_topology_report={
            "required_gaps": ["generated_artifact_root_cache_drift:.ruff_cache"]
        },
    )
    floor = reporting_scoring.hard_quality_floor_report(tmp_path)
    expected = (  # noqa: SIM905
        "python-size coverage types docstrings module-layout generated-artifacts product-boundary contributor-policy"
    ).split()
    assert floor["gate_ids"] == expected
    assert len(floor["required_gaps"]) == 4


def _generic_parity(**kwargs: object) -> dict[str, object]:
    adopter = kwargs.get("adopter")
    pending = [] if adopter else [{"gap": "parity_pending:work-lane-lifecycle"}]
    return {
        "ok": adopter == "domain-adopter",
        "adopter": adopter or "generic",
        "required_gaps": [] if adopter else ["parity_pending:work-lane-lifecycle"],
        "pending_packages": pending,
        "evidence": {"path": "docs/evidence/parity/domain-adopter-shadow.json"} if adopter else {},
    }


def test_adopter_scorecard_uses_profile_parity(monkeypatch, tmp_path) -> None:
    patch_scorecard_dependencies(monkeypatch, profile="gitlab")
    monkeypatch.setattr(report_domain, "parity_gaps_report", _generic_parity)
    monkeypatch.setattr(reporting_parity, "profile_identity", lambda _repo: "domain-adopter")
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": False,
            "mode": mode,
            "required_gaps": ["playbooks_v2_missing_skill_ids"],
            "advisory_gaps": [],
            "v2_compliance": {"score": 0, "max_score": 1},
        },
    )

    payload = report_domain.scorecard_report(tmp_path)

    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["next_actions"] == ("ethos playbooks check --mode v2-strict --json",)
    assert payload["data"]["parity"]["scope"]["domain_profile_parity_closed"] is True


def test_adopter_parity_binds_external_product_root(monkeypatch, tmp_path) -> None:
    product, adopter = tmp_path / "product", tmp_path / "adopter"
    product.mkdir()
    adopter.mkdir()
    calls: list[dict[str, object]] = []
    patch_scorecard_dependencies(monkeypatch, profile="gitlab")
    monkeypatch.setattr(
        report_domain.git_adapter,
        "current_tracked_head",
        lambda root: "product-head" if root == product else "adopter-head",
    )
    monkeypatch.setattr(
        report_domain,
        "parity_gaps_report",
        lambda **kwargs: calls.append(kwargs) or _generic_parity(**kwargs),
    )
    monkeypatch.setattr(reporting_parity, "profile_identity", lambda _repo: "domain-adopter")

    payload = report_domain.scorecard_report(adopter, product_root=product)

    call = next(item for item in calls if item.get("adopter") == "domain-adopter")
    assert (call["root"], call["target"]) == (product, adopter)
    assert (call["current_product_head"], call["current_target_head"]) == (
        "product-head",
        "adopter-head",
    )
    assert payload["summary"]["parity_pending_count"] == 0


def test_workflow_runtime_score_and_gap(monkeypatch, tmp_path) -> None:
    scores = reporting_scoring.product_scores(
        {
            "package_ontology": {"ok": True, "adapter_missing": []},
            "schemas": {"ok": True},
            "openspec": {"ok": True},
        },
        *([OK] * 3),
        {"truth": ASSISTANT_TRUTH_BOUNDARY},
        *([OK] * 6),
        1,
        OK,
    )
    assert scores["workflow_runtime"] == 1

    patch_scorecard_dependencies(monkeypatch)
    monkeypatch.setattr(
        report_domain,
        "workflow_runtime_report",
        lambda _repo: {
            "ok": False,
            "required_gaps": ["workflow_runtime_public_commands_invalid"],
        },
    )
    payload = report_domain.scorecard_report(tmp_path)
    assert payload["data"]["scores"]["workflow_runtime"] == 0
    assert "workflow_runtime_public_commands_invalid" in payload["required_gaps"]


# fmt: off
def _observation(provider: str, state: str, *, executed) -> dict[str, object]:
    github = provider == "github"
    target = "" if state == "not_configured" else "group/ethos"
    stdout_json = ([{"headSha": "head", "status": "completed", "conclusion": "success", "url": "gh"}]
                   if github else [{"sha": "head", "status": "success", "ref": "dev", "web_url": "gl"}]) if state == "observed" else None
    tool = "gh" if github else "glab"
    return {"provider": provider, "tool": tool, "tool_available": True,
            "tool_path": f"/usr/bin/{tool}", "target_env": f"ETHOS_HOSTED_{provider.upper()}_REPO",
            "target": target, "target_configured": bool(target),
            "command": provider_command(provider, target) if provider in {"github", "gitlab"} else [provider],
            "observation_state": state,
            "executed": executed, "returncode": 0 if executed else None,
            "stdout_json": stdout_json, "hosted_status_claimed": False,
            "provider_facts": provider_facts(provider, stdout_json)}
# fmt: on


def _artifact(head: str = "head", **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "ethos_hosted_provider_observation",
        "evidence_class": "hosted_provider_observation",
        "head": head,
        "state": "partial",
        "ok": False,
        "execute": True,
        "observation_gaps": ["provider_not_configured:github"],
        "observation_gap_count": 1,
        "observations": [
            _observation("github", "not_configured", executed=False),
            _observation("gitlab", "observed", executed=True),
        ],
        **dict.fromkeys(FLAGS, False),
    }
    payload.update(updates)
    return payload


def test_hosted_observation_reader_fails_closed(tmp_path) -> None:
    def state() -> object:
        return hosted_observation_report(tmp_path, current_head="head")["state"]

    assert state() == "not_applicable"
    config = tmp_path / ".config/checks/ci/hosted-observation.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        'output = "build/evidence/hosted-ci/observation.json"\nproviders = ["github", "gitlab"]\n'
        '[provider.github]\nrepository_target_env = "ETHOS_HOSTED_GITHUB_REPO"\n'
        '[provider.gitlab]\nrepository_target_env = "ETHOS_HOSTED_GITLAB_REPO"\n',
        encoding="utf-8",
    )
    output = tmp_path / "build/evidence/hosted-ci/observation.json"
    assert state() == "missing"
    output.parent.mkdir(parents=True)
    output.write_text("{", encoding="utf-8")
    assert state() == "invalid"
    output.write_text(json.dumps(_artifact("old")), encoding="utf-8")
    assert state() == "stale"
    for artifact in (
        _artifact(execute="yes"),
        _artifact(observations=[]),
        _artifact(
            observations=[
                _observation("wrong", "not_configured", executed=False),
                _observation("gitlab", "observed", executed=True),
            ]
        ),
        _artifact(hosted_github_status_claimed=True),
        _artifact(state="observed", ok=True, observation_gaps=[], observation_gap_count=0),
    ):
        output.write_text(json.dumps(artifact), encoding="utf-8")
        assert state() == "invalid"
    # fmt: off
    for index, updates in ((0, {"target": "forged/repo"}), (0, {"target_env": "FORGED_TARGET"}),
                           (0, {"target_configured": True}), (0, {"command": ["gh"]}),
                           (1, {"tool_available": False, "tool_path": ""}), (1, {"tool_path": 1}), (1, {"returncode": 7}), (1, {"returncode": "0"}),
                           (1, {"stdout_json": [{"status": "forged"}]}),
                           (1, {"provider_facts": {"latest_head": "forged"}}),
                           (0, {"observation_state": []}), (0, {"stdout_json": []})):
        artifact = _artifact()
        cast("list[dict[str, object]]", artifact["observations"])[index].update(updates)
        output.write_text(json.dumps(artifact), encoding="utf-8")
        assert state() == "invalid"
    # fmt: on
    missing = _artifact()
    del cast("list[dict[str, object]]", missing["observations"])[0]["target"]
    output.write_text(json.dumps(missing), encoding="utf-8")
    assert state() == "invalid"
    output.write_bytes(b"\xff")
    assert state() == "invalid"
    dry_run = _artifact(
        state="dry_run",
        ok=True,
        execute=False,
        observation_gaps=[],
        observation_gap_count=0,
        observations=[
            _observation("github", "not_configured", executed=False),
            _observation("gitlab", "not_executed", executed=False),
        ],
    )
    output.write_text(json.dumps(dry_run), encoding="utf-8")
    assert state() == "dry_run"
    output.write_text(json.dumps(_artifact()), encoding="utf-8")
    report = hosted_observation_report(tmp_path, current_head="head")
    assert report["state"] == "partial"
    assert report["provider_states"] == {
        "github": "not_configured",
        "gitlab": "observed",
    }
    assert all(report[key] is False for key in FLAGS)


def test_report_projects_hosted_and_local_publication(monkeypatch, tmp_path) -> None:
    patch_scorecard_dependencies(monkeypatch)
    hosted = {
        "state": "partial",
        "ok": False,
        "provider_states": {"github": "not_configured", "gitlab": "observed"},
        "advisory_gaps": ["provider_not_configured:github"],
    }
    monkeypatch.setattr(report_domain, "hosted_observation_report", lambda *_a, **_k: hosted)

    payload = report_domain.scorecard_report(tmp_path)

    assert payload["state"] == "advisory"
    assert payload["summary"]["hosted_observation_state"] == "partial"
    assert payload["summary"]["local_publication_state"] == "local_publish_ready"
    assert payload["data"]["hosted_observation"] == hosted
    assert payload["data"]["local_publication"]["remote_publication_claimed"] is False

    blocked = reporting_gaps.local_publication_projection(
        (), {"blocking": True, "required_gaps": ["executed_proof_missing"]}
    )
    assert (blocked["state"], blocked["required_gaps"]) == (
        "blocked",
        ["executed_proof_missing"],
    )
