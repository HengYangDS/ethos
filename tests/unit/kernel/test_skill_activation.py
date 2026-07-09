from __future__ import annotations

from copy import deepcopy

from ethos_core.contracts.skill.activation import normalize_skill_activation
from ethos_core.contracts.skill.activation import skill_registry_digest


def test_normalizes_activation_contract_without_compatibility_surface() -> None:
    payload = {
        "meta": {"version": 2, "source_of_truth": "repository"},
        "skill": [
            {
                "id": "code-change",
                "path": ".agents/skills/code-change/SKILL.md",
                "subject": "implementation",
                "authority": "primary",
                "subjects": ["implementation"],
                "path_globs": ["src/**", "tests/**"],
                "intent_tokens": ["implement", "refactor"],
                "pre_reads": ["README.md"],
                "post_checks": ["ethos prove"],
                "may_coactivate": ["quality-gate"],
                "commands": ["ethos status"],
                "boundary": "thin-playbook-projection",
            }
        ],
    }

    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")

    assert registry["schema_version"] == 2
    assert registry["source"] == ".agents/skills/activation.toml"
    record = registry["records"][0]
    assert record["id"] == "code-change"
    assert record["declared_id"] == "code-change"
    assert record["identifier_source"] == "id"
    assert record["path"] == ".agents/skills/code-change/SKILL.md"
    assert record["route_subjects"] == ["implementation", "changed-scope"]
    assert record["activation"]["path_globs"] == ["src/**", "tests/**"]
    assert record["routing"]["intent_tokens"] == ["implement", "refactor"]
    assert record["obligations"]["pre_reads"] == ["README.md"]
    assert record["obligations"]["post_checks"] == ["ethos prove"]
    assert record["relations"]["may_coactivate"] == ["quality-gate"]
    assert record["commands"] == ["ethos status"]
    assert record["boundary"] == "thin-playbook-projection"
    assert record["source_version"] == 2
    assert "legacy" not in record


def test_normalizes_external_v2_style_activation_contract() -> None:
    payload = {
        "meta": {"version": 2, "owner": "architecture-committee"},
        "coverage": {"required_roots": ["docs", "packages"]},
        "retired": {"skill_names": ["old-skill"]},
        "skill": [
            {
                "id": "external-openspec-governance",
                "priority": 30,
                "subject": "openspec-governance",
                "operation": "govern",
                "authority": "primary",
                "lifecycle": "active",
                "supports": ["openspec-change-explore"],
                "excludes": ["retired-openspec"],
                "path_globs": ["openspec/**"],
                "pre_reads": ["openspec/changes/README.md"],
                "during_rules": ["use official OpenSpec CLI surfaces first"],
                "post_checks": ["openspec validate --all --strict --json"],
                "broadcast_targets": ["coordinator", "verify", "knowledge"],
                "closure_artifacts": ["control-plane task state updates"],
            }
        ],
    }

    registry = normalize_skill_activation(
        payload,
        source=".config/tooling/repo/skill_activation_contracts.toml",
    )

    record = registry["records"][0]
    assert registry["coverage"]["required_roots"] == ["docs", "packages"]
    assert registry["retired"]["skill_names"] == ["old-skill"]
    assert record["id"] == "external-openspec-governance"
    assert record["primary_subject"] == "openspec-governance"
    assert record["operation"] == "govern"
    assert record["authority"] == "primary"
    assert record["lifecycle"] == "active"
    assert record["route_subjects"] == ["openspec-governance", "changed-scope"]
    assert record["relations"]["supports"] == ["openspec-change-explore"]
    assert record["relations"]["excludes"] == ["retired-openspec"]
    assert record["obligations"]["during_rules"] == ["use official OpenSpec CLI surfaces first"]
    assert record["extensions"] == {
        "broadcast_targets": ["coordinator", "verify", "knowledge"],
        "closure_artifacts": ["control-plane task state updates"],
    }


def test_skill_registry_digest_is_stable_and_content_addressed() -> None:
    payload = {
        "meta": {"version": 2},
        "skill": [
            {
                "name": "repo-governance",
                "subject": "repository-governance",
                "operation": "govern",
                "authority": "primary",
                "lifecycle": "active",
                "path_globs": ["docs/**"],
                "post_checks": ["ethos report --json"],
            }
        ],
    }
    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")

    assert skill_registry_digest(registry) == skill_registry_digest(deepcopy(registry))

    changed = deepcopy(registry)
    changed["records"][0]["operation"] = "audit"
    assert skill_registry_digest(registry) != skill_registry_digest(changed)
