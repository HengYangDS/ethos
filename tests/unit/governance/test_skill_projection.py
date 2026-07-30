from __future__ import annotations

from pathlib import Path

import pytest

from ethos.assistants.skills.packages import validate_skill_package_manifest
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

    assert result["ok"] is False
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
