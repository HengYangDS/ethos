"""Keep skill activation declarative and evaluation evidence non-authorizing."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

import pytest
import tomli_w

from ethos.assistants.skills.capabilities import capability_records
from ethos.assistants.skills.packages import compute_skill_package_digest
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_coverage
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.assistants.skills.portfolio import portfolio_retirement
from ethos.assistants.skills.portfolio import skill_portfolio_report
from ethos.contracts.skill.activation import compile_skill_activation
from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import declare_fixture_documentation_proof
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import initialize_adopted_fixture
from tests.support.governed_repository import write_active_commitment
from tests.support.literal_cases import literal_case
from tests.support.skills import write_skill_package


def _registry(*skills: dict[str, object]) -> dict[str, Any]:
    return normalize_skill_activation(
        {
            "meta": {"version": 2, "source_of_truth": "repository"},
            "coverage": {"required_primary_subjects": [], "single_owner_subjects": []},
            "skill": list(skills),
        },
        source="test",
    )


def _skill(skill_id: str, **updates: object) -> dict[str, object]:
    return {
        "id": skill_id,
        "subject": skill_id,
        "operation": "plan",
        "path_globs": ["src/**"],
        "path": f".agents/skills/{skill_id}/SKILL.md",
        "package_manifest": f".agents/skills/{skill_id}/package.toml",
        "authority": "primary",
        "lifecycle": "active",
        "boundary": "repository-truth",
        "pre_reads": ["AGENTS.md"],
        "post_checks": ["ethos status --json"],
    } | updates


def test_activation_registry_contains_only_current_contract_semantics() -> None:
    registry = _registry({"id": "sample"})

    record = registry["records"][0]
    assert (
        not {
            "commands",
            "declared_id",
            "declared_name",
            "identifier_source",
            "source_version",
            "extensions",
        }
        & record.keys()
    )
    path = Path(__file__).resolve().parents[3] / ".agents/skills/activation.toml"
    live = normalize_skill_activation(tomllib.loads(path.read_text()), source=str(path))
    feedback = compile_skill_activation(
        live,
        operation="plan",
        subjects=("feedback-loop",),
        registry_gaps=(),
        observed_records=tuple({**record, "required_gaps": []} for record in live["records"]),
    )
    assert [skill.id for skill in feedback.skills] == ["ethos-repository-governance"]
    assert "rules/agents.md" in feedback.context.pre_reads


def test_skill_registry_schema_rejects_an_unowned_digest_projection() -> None:
    registry = _registry(_skill("sample"))
    assert validate_schema_instance("skill-registry.schema.json", registry)["verdict"] == "pass"
    registry["digest"] = "sha256:" + "a" * 64

    result = validate_schema_instance("skill-registry.schema.json", registry)

    assert result["verdict"] == "block"


@pytest.mark.parametrize("retired_key", ["name", "may_coactivate", "unexpected"])
def test_skill_activation_schema_rejects_retired_or_unknown_fields(retired_key: str) -> None:
    skill = _skill("sample") | {
        retired_key: ["sample"] if retired_key == "may_coactivate" else "sample",
    }
    registry = _registry()
    result = validate_schema_instance(
        "skill-activation.schema.json",
        {
            "meta": registry["meta"],
            "coverage": registry["coverage"],
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
            pre_reads=[".config/checks/ruff/ruff.toml"],
        ),
    )
    result = compile_skill_activation(
        registry,
        operation="plan",
        subjects=("repository-governance",),
        changed_paths=("src/ethos/result.py",),
        registry_gaps=(),
        observed_records=tuple({**record, "required_gaps": []} for record in registry["records"]),
    )

    assert result.verdict == "pass"
    assert [skill.id for skill in result.skills] == [
        "repository-governance",
        "python-quality",
    ]
    assert result.context.model_dump(mode="json") == {
        "pre_reads": ["AGENTS.md", ".config/checks/ruff/ruff.toml"],
        "during_rules": [],
        "post_checks": ["ethos status --json"],
    }


@pytest.mark.parametrize(
    ("records", "gap"),
    [
        (
            [_skill("quality", operation="prove", requires=["absent"])],
            "skill_activation_requirement_missing:quality:absent",
        ),
        (
            [
                _skill("first", requires=["second"]),
                _skill("second", operation="prove", path_globs=["tests/**"], requires=["first"]),
            ],
            "skill_activation_dependency_cycle",
        ),
        (
            [
                _skill("fast-path", subject="change", excludes=["deep-review"]),
                _skill("deep-review", subject="quality", operation="prove"),
            ],
            "skill_activation_exclusion_conflict:fast-path:deep-review",
        ),
    ],
)
def test_skill_activation_rejects_invalid_selected_relations(
    records: list[dict[str, object]], gap: str
) -> None:
    registry = _registry(*records)
    result = compile_skill_activation(
        registry,
        operation="plan",
        changed_paths=("src/a.py",),
        registry_gaps=(),
        observed_records=tuple({**record, "required_gaps": []} for record in registry["records"]),
    )
    assert result.verdict == "block"
    assert result.required_gaps == (gap,)
    assert result.skills == ()


@pytest.mark.parametrize(
    "package_state",
    ["valid", "tampered", "missing", "optional", "narrowed", "identity", "registry"],
)
def test_plan_projects_the_compiled_skill_activation(tmp_path: Path, package_state: str) -> None:
    """Only validated selected packages and their dependencies may be activated."""
    repo = init_git_repo(tmp_path / "adopter")
    initialize_adopted_fixture(repo)
    declare_fixture_documentation_proof(repo)
    skills = repo / ".agents/skills"
    records = []
    for skill_id in ("feedback-intent", "read-source", "release-checks"):
        write_skill_package(skills, skill_id)
        records.append(
            _skill(
                skill_id,
                operation="plan" if skill_id == "feedback-intent" else skill_id,
                path_globs=[f"{skill_id}/**"],
                subjects=[skill_id],
                intent_tokens=[skill_id],
                requires=["read-source"] if skill_id == "feedback-intent" else [],
            )
        )
    registry = _registry()
    (skills / "activation.toml").write_text(
        tomli_w.dumps(
            {"meta": registry["meta"], "coverage": registry["coverage"], "skill": records}
        )
    )
    (skills / "README.md").write_text("# Skills\n")
    write_active_commitment(repo, change_id="feedback-intent")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    if package_state == "registry":
        (skills / "activation.toml").write_text("invalid [\n")
    elif package_state != "valid":
        entry = (
            skills
            / ("release-checks" if package_state == "optional" else "read-source")
            / "SKILL.md"
        )
        content = entry.read_text()
        if package_state == "missing":
            entry.unlink()
        else:
            entry.write_text(
                content.replace("## Trust Boundary", "## Boundary")
                if package_state == "narrowed"
                else content.replace("name: read-source", "name: different")
                if package_state == "identity"
                else content + "\nChanged package content.\n"
            )
        if package_state in {"narrowed", "identity"}:
            manifest = entry.with_name("package.toml")
            policy = tomllib.loads(manifest.read_text())
            policy["expected_digest"] = compute_skill_package_digest(entry.parent, [entry.name])
            if package_state == "narrowed":
                policy["required_sections"] = ["Workflow"]
            else:
                policy["id"] = "different"
            manifest.write_text(tomli_w.dumps(policy))
    rejected = package_state not in {"valid", "optional"}
    for selection in ((), ("--changed",)):
        result = run_ethos_raw(
            "plan", "--change", "feedback-intent", *selection, "--json", cwd=repo
        )
        payload = json.loads(result.stdout)
        activation = payload["data"]["skill_activation"]
        assert payload["verdict"] == ("block" if rejected else "pass"), payload
        assert [skill["id"] for skill in activation["skills"]] == (
            [] if rejected else ["read-source", "feedback-intent"]
        )
        assert not rejected or payload["required_gaps"]
        assert rejected or activation["context"]["pre_reads"] == ["AGENTS.md"]
        assert not {"review_plan", "review_decision"} & payload["data"].keys()


@pytest.mark.parametrize(
    ("old", "new", "gap"),
    cast(
        "list[tuple[str, str, str]]",
        literal_case(
            "governance.test_skill_projection:parametrize:test_skill_package_schema_owns_manifest_structure:0"
        ),
    ),
)
def test_skill_package_schema_owns_manifest_structure(
    tmp_path: Path, old: str, new: str, gap: str
) -> None:
    manifest = Path(write_skill_package(tmp_path / ".agents" / "skills", "sample-skill"))
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["required_gaps"] == [gap]
    assert result["capabilities"] == []


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
    records: list[dict[str, object]] = [
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
    records: list[dict[str, object]] = [
        _skill(skill_id, lifecycle=lifecycle, primary_subject=subject)
        for skill_id, lifecycle, subject in (
            ("first", "active", "governance"),
            ("second", "active", "governance"),
            ("retired", "retired", "release"),
        )
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
    records: list[dict[str, object]] = [
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
    packages: list[dict[str, object]] = [
        {
            "id": skill_id,
            "files": [str(index) for index in range(7)] if skill_id == "first" else [],
            "capabilities": [{"command": ["ethos", "status"]}],
        }
        for skill_id in ("first", "second", "third")
    ]

    result = portfolio_design(records, packages)

    assert set(cast("list[str]", result["required_gaps"])) == {
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


@pytest.mark.parametrize("declared", [True, False])
def test_eval_metadata_remains_evidence_and_never_progress_state(
    tmp_path: Path, *, declared: bool
) -> None:
    manifest = Path(write_skill_package(tmp_path / ".agents" / "skills", "sample-skill"))
    relative = manifest.relative_to(tmp_path).as_posix()
    assert validate_skill_package_manifest(tmp_path, relative)["eval"] == {}
    payload = tomllib.loads(manifest.read_text())
    payload["eval"] = {
        "treatment_id": "candidate",
        "metrics": ["pass_at_k", "pass_power_k", "instability_gap"],
        "pass_at_k": 0.8,
        "pass_power_k": 0.6,
        "instability_gap": 0.1,
        "evidence_refs": ["evidence/attestations/workflow-eval.json"],
        **({} if declared else {"undeclared": "forbidden"}),
    }
    manifest.write_text(tomli_w.dumps(payload))

    result = validate_skill_package_manifest(tmp_path, relative)
    assert result["verdict"] == ("pass" if declared else "block")
    if declared:
        assert result["eval"]["truth_boundary"] == "skill_metadata_only"
        assert not {"done", "progress", "status", "tasks"} & result["eval"].keys()
    else:
        assert "skill_package_eval_invalid:sample-skill" in result["required_gaps"]


def _write_portfolio_state(skills: Path, state: str) -> None:
    """Build native portfolio presence states without supplying missing governance."""
    if state in {"dangling", "dangling_root"}:
        target = skills.parent if state == "dangling" else skills
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to("missing-portfolio", target_is_directory=True)
        return
    if state in {"absent", "required_absent"}:
        return
    skills.mkdir(parents=True, exist_ok=True)
    if state != "missing_readme":
        (skills / "README.md").write_text("# Skills\n")
    if state in {"empty", "missing_readme"}:
        registry = _registry()
        (skills / "activation.toml").write_text(
            tomli_w.dumps({"meta": registry["meta"], "coverage": registry["coverage"], "skill": []})
        )
    elif state == "unbound":
        write_skill_package(skills, "read-source")
    elif state == "malformed":
        (skills / "activation.toml").write_text("invalid [\n")
    elif state == "invalid_encoding":
        (skills / "activation.toml").write_bytes(b"\xff")
    elif state == "non_file":
        (skills / "activation.toml").mkdir()


def test_portfolio_structural_read_failure_remains_a_gap(tmp_path: Path, monkeypatch) -> None:
    """Filesystem errors also remain fail-closed on the Python 3.12 boundary."""
    repo = init_git_repo(tmp_path / "repo")
    initialize_adopted_fixture(repo)
    skills = repo / ".agents/skills"
    _write_portfolio_state(skills, "empty")
    native_exists = Path.exists

    def observed_exists(path: Path) -> bool:
        if path == skills:
            raise PermissionError(path)
        return native_exists(path)

    monkeypatch.setattr(Path, "exists", observed_exists)
    report = skill_portfolio_report(repo, required=False)
    assert report["verdict"] == "block"
    gaps = report["registry_required_gaps"]
    assert isinstance(gaps, list)
    assert ".agents/skills:unreadable" in gaps


@pytest.mark.parametrize(
    "state",
    [
        "absent",
        "empty",
        "unbound",
        "malformed",
        "missing_readme",
        "required_absent",
        "dangling",
        "dangling_root",
        "invalid_encoding",
        "non_file",
    ],
)
def test_plan_optional_portfolio_requires_positive_absence(tmp_path: Path, state: str) -> None:
    """Absent optional projections never block; present invalid state cannot disappear."""
    repo = init_git_repo(tmp_path / "repo")
    initialize_adopted_fixture(repo)
    declare_fixture_documentation_proof(repo)
    write_active_commitment(repo, change_id="optional-skills")
    if state == "required_absent":
        gate_path = repo / "system/gates.toml"
        gates = tomllib.loads(gate_path.read_text())
        gates["gates"][0]["depends_on"] = ["portfolio-contract"]
        gates["gates"].append(
            {
                "id": "portfolio-contract",
                "kind": "governance",
                "providers": [
                    f"{skill_portfolio_report.__module__}:{skill_portfolio_report.__name__}"
                ],
                "execution_mode": "provider",
            }
        )
        gate_path.write_text(tomli_w.dumps(gates))
    _write_portfolio_state(repo / ".agents/skills", state)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare optional portfolio")
    result = run_ethos_raw("plan", "--json", cwd=repo)
    report = json.loads(result.stdout)
    accepted = state in {"absent", "empty"}
    assert report["verdict"] == ("pass" if accepted else "block"), report["required_gaps"]
    assert bool(report["required_gaps"]) is not accepted
    if state == "required_absent":
        assert ".agents/skills/activation.toml" in report["required_gaps"]
        assert {"openspec-baseline", "portfolio-contract"} <= {
            node["id"] for node in report["data"]["transition_plan"]["nodes"]
        }
    if state == "missing_readme":
        assert ".agents/skills/README.md" in report["required_gaps"]
