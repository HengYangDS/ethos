from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import cast

import pytest

from ethos.assistants.skills.capabilities import capability_records
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_coverage
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.assistants.skills.portfolio import portfolio_retirement
from ethos.contracts.skill.activation import compile_skill_activation
from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.literal_cases import literal_case
from tests.support.playbooks import write_playbook_package


def _registry(*skills: dict[str, object]) -> dict[str, Any]:
    return normalize_skill_activation(
        {"meta": {"version": 2}, "skill": list(skills)},
        source="test",
    )


def _skill(skill_id: str, **updates: object) -> dict[str, object]:
    return {
        "id": skill_id,
        "subject": skill_id,
        "operation": "plan",
        "path_globs": ["src/**"],
    } | updates


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


def test_skill_registry_schema_rejects_an_unowned_digest_projection() -> None:
    registry = normalize_skill_activation(
        {
            "meta": {"version": 2, "source_of_truth": "repository"},
            "coverage": {
                "required_primary_subjects": ["sample"],
                "single_owner_subjects": ["sample"],
            },
            "skill": [
                _skill(
                    "sample",
                    path=".agents/skills/sample/SKILL.md",
                    package_manifest=".agents/skills/sample/package.toml",
                    authority="primary",
                    boundary="repository",
                    pre_reads=["AGENTS.md"],
                    post_checks=["ethos status --json"],
                )
            ],
        },
        source="test",
    )
    assert validate_schema_instance("skill-registry.schema.json", registry)["verdict"] == "pass"
    registry["digest"] = "sha256:" + "a" * 64

    result = validate_schema_instance("skill-registry.schema.json", registry)

    assert result["verdict"] == "block"


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
        _skill("repository-governance", pre_reads=["AGENTS.md"]),
        _skill(
            "python-quality",
            subject="quality-gates",
            operation="prove",
            path_globs=["src/**/*.py"],
            requires=["repository-governance"],
            pre_reads=["ruff.toml"],
        ),
    )
    result = compile_skill_activation(
        registry,
        operation="plan",
        subjects=("repository-governance",),
        changed_paths=("src/ethos/result.py",),
    )

    assert result.verdict == "pass"
    assert [skill.id for skill in result.skills] == [
        "repository-governance",
        "python-quality",
    ]
    assert result.context.model_dump(mode="json") == {
        "pre_reads": ["AGENTS.md", "ruff.toml"],
        "during_rules": [],
        "post_checks": [],
    }


def test_skill_activation_fails_closed_for_missing_or_cyclic_requirements() -> None:
    missing = _registry(
        _skill("quality", operation="prove", requires=["absent"]),
    )
    cyclic = _registry(
        _skill("first", requires=["second"]),
        _skill("second", operation="prove", path_globs=["tests/**"], requires=["first"]),
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
        _skill("fast-path", subject="change", excludes=["deep-review"]),
        _skill("deep-review", subject="quality", operation="prove"),
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
    write_active_commitment(repo)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    registry = _registry(
        _skill("repository-governance", path_globs=["**"], pre_reads=["AGENTS.md"]),
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
                "id": "repository-governance",
                "path": ".agents/skills/repository-governance/SKILL.md",
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
    transition_facts = payload["data"]["transition_plan"]["facts"]["values"]
    assert "required_review_lens_count" not in payload["summary"]
    assert "review_plan" not in payload["data"]
    assert "review_decision" not in payload["data"]
    assert "review_plan" not in transition_facts


def test_skill_package_manifest_rejects_undeclared_eval_fields(tmp_path: Path) -> None:
    manifest = Path(write_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
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
    literal_case(
        "governance.test_skill_projection:parametrize:test_skill_package_schema_owns_manifest_structure:0"
    ),
)
def test_skill_package_schema_owns_manifest_structure(
    tmp_path: Path, old: str, new: str, gap: str
) -> None:
    manifest = Path(write_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["required_gaps"] == [gap]
    assert result["capabilities"] == []


def test_skill_package_omits_absent_eval_projection(tmp_path: Path) -> None:
    manifest = Path(write_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))

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


def test_skill_capability_semantics_fail_closed_matrix(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    records = [
        {"id": "mutating", "kind": "command_readonly", "command": ["ethos", "land"]},
        {"id": "unknown", "kind": "command_readonly", "command": ["external", "read"]},
        {"id": "empty", "kind": "script_readonly", "command": []},
        {"id": "interpreter", "kind": "script_readonly", "command": ["python", "read.py"]},
        {"id": "escape", "kind": "script_readonly", "command": ["../read.sh"]},
        {"id": "proof", "kind": "command_proof", "command": ["ethos", "status"]},
    ]

    gaps, projected = capability_records(
        "governance", records, package_dir=package, included_files=frozenset({"read.sh"})
    )

    assert gaps == [
        "skill_package_capability_readonly_mutating:governance:mutating",
        "skill_package_capability_readonly_untrusted:governance:unknown",
        "skill_package_capability_readonly_untrusted:governance:empty",
        "skill_package_capability_readonly_untrusted:governance:interpreter",
        "skill_package_capability_readonly_untrusted:governance:escape",
        "skill_package_capability_proof_invalid:governance:proof",
    ]
    assert [record["id"] for record in projected] == [record["id"] for record in records]


def test_skill_portfolio_coverage_requires_one_active_primary_owner() -> None:
    records = [
        {
            "id": "first",
            "authority": "primary",
            "lifecycle": "active",
            "primary_subject": "governance",
        },
        {
            "id": "second",
            "authority": "primary",
            "lifecycle": "active",
            "primary_subject": "governance",
        },
        {
            "id": "retired",
            "authority": "primary",
            "lifecycle": "retired",
            "primary_subject": "release",
        },
    ]

    result = portfolio_coverage(
        {
            "required_primary_subjects": ["governance", "release", "governance"],
            "single_owner_subjects": ["governance"],
        },
        records,
    )

    assert result["required_gaps"] == [
        "skill_portfolio_subject_missing:release",
        "skill_portfolio_subject_duplicate:governance:first,second",
    ]
    assert result["owners"] == {"governance": ["first", "second"]}


def test_skill_portfolio_design_reports_every_owner_collision() -> None:
    records = [
        {
            "id": skill_id,
            "primary_subject": "governance",
            "subjects": [] if skill_id == "first" else ["governance"],
            "path_globs": ["src/**"],
            "intent_tokens": ["govern"],
            "operation": "plan",
        }
        for skill_id in ("first", "second", "third")
    ]
    packages = [
        {
            "id": skill_id,
            "files": [str(index) for index in range(7)] if skill_id == "first" else [],
            "capabilities": [{"command": ["ethos", "status"]}],
        }
        for skill_id in ("first", "second", "third")
    ]

    result = portfolio_design(records, packages)

    assert set(result["required_gaps"]) == {
        "skill_portfolio_primary_subject_not_routed:first",
        "skill_portfolio_package_overloaded:first:7",
        "skill_portfolio_path_glob_duplicate:src/**:first,second,third",
        "skill_portfolio_intent_token_overclaimed:govern:first,second,third",
        "skill_portfolio_route_duplicate:governance:plan:first,second,third",
    }
    assert result["command_owner_count"] == {"ethos status": 3}


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
    manifest = Path(write_playbook_package(tmp_path / ".agents" / "skills", "sample-skill"))
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
