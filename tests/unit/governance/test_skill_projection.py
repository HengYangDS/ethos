from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.assistants.skills.portfolio import portfolio_retirement
from ethos.contracts.skill.activation import normalize_skill_activation
from tests.support.playbooks import write_v2_playbook_package


def test_activation_metadata_does_not_duplicate_package_capabilities() -> None:
    registry = normalize_skill_activation(
        {
            "meta": {"version": 2},
            "skill": [{"id": "sample"}],
        },
        source="test",
    )

    record = registry["records"][0]
    assert "commands" not in record
    assert "commands" not in record["extensions"]


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
