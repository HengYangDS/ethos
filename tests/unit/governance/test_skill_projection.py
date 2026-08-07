from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import cast

import pytest

from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.assistants.skills.portfolio import portfolio_retirement
from ethos.contracts.review import ReviewResult
from ethos.contracts.skill.activation import compile_skill_activation
from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.playbooks import write_v2_playbook_package


def _registry(*skills: dict[str, object]) -> dict[str, Any]:
    return normalize_skill_activation(
        {"meta": {"version": 2}, "skill": list(skills)},
        source="test",
    )


def _review_results(
    plan: dict[str, Any],
    *,
    head: str | None = None,
) -> list[dict[str, object]]:
    return [
        ReviewResult(
            review_plan=cast("str", plan["digest"]),
            inputs=cast("str", plan["inputs"]),
            head=head or cast("str", plan["head"]),
            tree=cast("str", plan["tree"]),
            phase=plan["phase"],
            lens=lens["id"],
            verifier=f"reviewer:{lens['id']}",
            verdict="pass",
            next_action="continue",
        ).model_dump(mode="json")
        for lens in plan["lenses"]
    ]


def _review_plan_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.playbooks_report",
        lambda _root: {"registry": _registry(), "required_gaps": []},
        raising=False,
    )
    first = run_ethos("plan", "--root", repo.as_posix(), "--json", cwd=repo)
    return repo, first, first["data"]["review_plan"]


def test_activation_registry_contains_only_current_v2_semantics() -> None:
    registry = _registry({"id": "sample"})

    record = registry["records"][0]
    assert "commands" not in record
    assert (
        not {
            "declared_id",
            "declared_name",
            "identifier_source",
            "source_version",
            "extensions",
        }
        & record.keys()
    )


@pytest.mark.parametrize("retired_key", ["name", "may_coactivate", "unexpected"])
def test_skill_activation_schema_rejects_retired_or_unknown_fields(retired_key: str) -> None:
    skill = {
        "id": "sample",
        "subject": "sample",
        "operation": "plan",
        "path": ".agents/skills/sample/SKILL.md",
        "package_manifest": ".agents/skills/sample/package.toml",
        "authority": "primary",
        "lifecycle": "active",
        "path_globs": ["src/**"],
        "pre_reads": ["AGENTS.md"],
        "post_checks": ["ethos status --json"],
        retired_key: ["sample"] if retired_key == "may_coactivate" else "sample",
    }

    result = validate_schema_instance(
        "skill-activation.schema.json",
        {
            "meta": {"version": 2, "source_of_truth": "repository"},
            "coverage": {
                "required_primary_subjects": ["sample"],
                "single_owner_subjects": ["sample"],
            },
            "skill": [skill],
        },
    )

    assert result["verdict"] == "block"


def test_skill_activation_compiles_an_ordered_dependency_complete_set() -> None:
    registry = _registry(
        {
            "id": "change-lifecycle",
            "subject": "change-lifecycle",
            "operation": "plan",
            "path_globs": ["src/**"],
            "pre_reads": ["AGENTS.md"],
        },
        {
            "id": "python-quality",
            "subject": "quality-gates",
            "operation": "prove",
            "path_globs": ["src/**/*.py"],
            "requires": ["change-lifecycle"],
            "pre_reads": ["ruff.toml"],
        },
    )
    result = compile_skill_activation(
        registry,
        operation="plan",
        subjects=("change-lifecycle",),
        changed_paths=("src/ethos/result.py",),
    )

    assert result.verdict == "pass"
    assert [skill.id for skill in result.skills] == [
        "change-lifecycle",
        "python-quality",
    ]
    assert result.context.model_dump(mode="json") == {
        "pre_reads": ["AGENTS.md", "ruff.toml"],
        "during_rules": [],
        "post_checks": [],
    }


def test_skill_activation_fails_closed_for_missing_or_cyclic_requirements() -> None:
    missing = _registry(
        {
            "id": "quality",
            "subject": "quality",
            "operation": "prove",
            "path_globs": ["src/**"],
            "requires": ["absent"],
        },
    )
    cyclic = _registry(
        {
            "id": "first",
            "subject": "first",
            "operation": "plan",
            "path_globs": ["src/**"],
            "requires": ["second"],
        },
        {
            "id": "second",
            "subject": "second",
            "operation": "prove",
            "path_globs": ["tests/**"],
            "requires": ["first"],
        },
    )

    missing_result = compile_skill_activation(
        missing, operation="plan", changed_paths=("src/a.py",)
    )
    cyclic_result = compile_skill_activation(cyclic, operation="plan", changed_paths=("src/a.py",))

    assert missing_result.verdict == "block"
    assert list(missing_result.required_gaps) == [
        "skill_activation_requirement_missing:quality:absent"
    ]
    assert cyclic_result.verdict == "block"
    assert list(cyclic_result.required_gaps) == ["skill_activation_dependency_cycle"]


def test_skill_activation_rejects_mutually_exclusive_capabilities() -> None:
    registry = _registry(
        {
            "id": "fast-path",
            "subject": "change",
            "operation": "plan",
            "path_globs": ["src/**"],
            "excludes": ["deep-review"],
        },
        {
            "id": "deep-review",
            "subject": "quality",
            "operation": "prove",
            "path_globs": ["src/**"],
        },
    )

    result = compile_skill_activation(
        registry,
        operation="plan",
        changed_paths=("src/a.py",),
    )

    assert result.verdict == "block"
    assert list(result.required_gaps) == [
        "skill_activation_exclusion_conflict:fast-path:deep-review"
    ]


def test_plan_projects_the_compiled_skill_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    activation_path = repo / ".agents" / "skills" / "activation.toml"
    activation_path.parent.mkdir(parents=True)
    activation_path.write_text("[meta]\nversion = 2\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    registry = _registry(
        {
            "id": "change-lifecycle",
            "subject": "change-lifecycle",
            "operation": "plan",
            "path_globs": ["**"],
            "pre_reads": ["AGENTS.md"],
        },
    )
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.playbooks_report",
        lambda _root: {"registry": registry, "required_gaps": []},
        raising=False,
    )

    payload = run_ethos("plan", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["data"]["skill_activation"] == {
        "verdict": "pass",
        "skills": [
            {
                "id": "change-lifecycle",
                "path": ".agents/skills/change-lifecycle/SKILL.md",
                "operation": "plan",
            }
        ],
        "context": {
            "pre_reads": ["AGENTS.md"],
            "during_rules": [],
            "post_checks": [],
        },
        "required_gaps": [],
    }
    review_plan = payload["data"]["review_plan"]
    transition_facts = payload["data"]["transition_plan"]["facts"]["values"]
    assert payload["summary"]["required_review_lens_count"] == len(review_plan["lenses"])
    assert review_plan["head"] == payload["data"]["transition_plan"]["facts"]["head"]
    assert review_plan["tree"] == payload["data"]["transition_plan"]["facts"]["tree"]
    assert transition_facts["review_plan"]["digest"] == review_plan["digest"]


def test_plan_reduces_external_review_results_through_the_same_bound_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, first, plan = _review_plan_fixture(tmp_path, monkeypatch)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(json.dumps(_review_results(plan)), encoding="utf-8")

    reviewed = run_ethos(
        "plan",
        "--root",
        repo.as_posix(),
        "--review-results",
        results_path.as_posix(),
        "--json",
        cwd=repo,
    )

    assert reviewed["required_gaps"] == first["required_gaps"]
    assert reviewed["data"]["review_decision"] == {
        "review_plan": plan["digest"],
        "verdict": "pass",
        "state": "reviewed",
        "required_gaps": [],
        "next_action": "continue the governed lifecycle",
        "user_decision_required": False,
    }


def test_plan_fails_closed_for_stale_review_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, plan = _review_plan_fixture(tmp_path, monkeypatch)
    stale_path = tmp_path / "stale-review-results.json"
    stale_path.write_text(
        json.dumps(_review_results(plan, head="0" * 40)),
        encoding="utf-8",
    )

    stale_result = run_ethos(
        "plan",
        "--root",
        repo.as_posix(),
        "--review-results",
        stale_path.as_posix(),
        "--json",
        cwd=repo,
    )

    assert stale_result["data"]["review_decision"]["state"] == "gapped"
    assert stale_result["data"]["review_decision"]["required_gaps"] == [
        f"review_result_binding_mismatch:{lens['id']}" for lens in plan["lenses"]
    ]
    assert stale_result["next_action"] == "rerun the missing or stale review lenses"


def test_plan_fails_closed_without_traceback_for_malformed_review_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, first, _ = _review_plan_fixture(tmp_path, monkeypatch)
    malformed_path = tmp_path / "malformed-review-results.json"
    malformed_path.write_text("{", encoding="utf-8")

    result = run_ethos(
        "plan",
        "--root",
        repo.as_posix(),
        "--review-results",
        malformed_path.as_posix(),
        "--json",
        cwd=repo,
    )

    assert result["verdict"] == "block"
    assert result["required_gaps"] == [
        *first["required_gaps"],
        "review_results_invalid",
    ]
    assert result["next_action"] == "repair the review result file and rerun ethos plan --json"
    assert "review_decision" not in result["data"]


def test_skill_package_manifest_rejects_undeclared_eval_fields(tmp_path: Path) -> None:
    manifest = Path(write_v2_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + """

[eval]
treatment_id = "runtime-v1"
metrics = ["pass_at_k"]
pass_at_k = 0.8
evidence_refs = ["evidence/sample.json"]
undeclared = "forbidden"
""",
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["verdict"] == "block"
    assert "skill_package_eval_invalid:sample-skill" in result["required_gaps"]


@pytest.mark.parametrize(
    ("old", "new", "gap"),
    [
        (
            "schema_version = 2\n",
            "",
            "skill_package_schema_version_invalid:sample-skill",
        ),
        (
            'kind = "command_readonly"',
            'kind = "unknown"',
            "skill_package_capability_kind_unknown:sample-skill:unknown",
        ),
        (
            'command = ["ethos", "status", "--json"]\n',
            "",
            "skill_package_capability_command_missing:sample-skill:0",
        ),
        ("sha256:", "md5:", "skill_package_expected_digest_invalid:sample-skill"),
        (
            'kind = "command_readonly"',
            'kind = "command_mutation_guarded"',
            "skill_package_capability_guard_missing:sample-skill:ethos.status",
        ),
    ],
)
def test_skill_package_schema_owns_manifest_structure(
    tmp_path: Path, old: str, new: str, gap: str
) -> None:
    manifest = Path(write_v2_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["required_gaps"] == [gap]
    assert result["capabilities"] == []


def test_skill_package_omits_absent_eval_projection(tmp_path: Path) -> None:
    manifest = Path(write_v2_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["eval"] == {}


def test_skill_novelty_requires_one_owner_per_semantic_boundary() -> None:
    records: list[dict[str, object]] = [
        {
            "id": skill_id,
            "primary_subject": subject,
            "subjects": [subject],
            "path_globs": [f"{skill_id}/**"],
            "intent_tokens": [subject],
            "operation": "govern",
        }
        for skill_id, subject in (("first", "alpha"), ("second", "alpha"))
    ]

    result = portfolio_design(records, [])

    assert result["required_gaps"] == ["skill_portfolio_route_duplicate:alpha:govern:first,second"]
    novelty = cast("dict[str, object]", result["novelty"])
    assert novelty["duplicate_routes"] == {"alpha:govern": ["first", "second"]}


def test_retired_skill_requires_complete_disposition_and_absent_carrier(tmp_path: Path) -> None:
    path = tmp_path / ".agents/skills/retired-skill"
    path.mkdir(parents=True)
    registry: dict[str, object] = {
        "retired": {
            "retired-skill": {
                "reason": "replaced",
                "path": ".agents/skills/retired-skill",
            }
        }
    }

    result = portfolio_retirement(registry, [], tmp_path)

    assert result["required_gaps"] == [
        "skill_retirement_field_missing:retired-skill:retired_on",
        "skill_retirement_field_missing:retired-skill:kill_signal",
        "skill_retirement_live_path:retired-skill:.agents/skills/retired-skill",
    ]


def test_eval_metadata_remains_evidence_and_never_progress_state(tmp_path: Path) -> None:
    manifest = Path(write_v2_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + """

[eval]
treatment_id = "candidate"
metrics = ["pass_at_k", "pass_power_k", "instability_gap"]
pass_at_k = 0.8
pass_power_k = 0.6
instability_gap = 0.1
evidence_refs = ["evidence/attestations/workflow-eval.json"]
""",
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["verdict"] == "pass"
    assert result["eval"]["truth_boundary"] == "skill_metadata_only"
    assert not {"done", "progress", "status", "tasks"} & result["eval"].keys()
