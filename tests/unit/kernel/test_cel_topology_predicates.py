"""CEL topology predicate regression and property tests."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

import ethos_core.contracts.artifacts.topology as topology_contract
from ethos_core.contracts.artifacts.topology import GeneratedArtifactTopologyDeclaration
from ethos_core.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos_core.contracts.artifacts.topology import path_policy_from_declaration
from ethos_core.contracts.policy.cel import evaluate_cel_gap_groups
from ethos_core.contracts.policy.cel import evaluate_cel_predicate
from ethos_core.contracts.policy.cel import evaluate_cel_value
from ethos_core.contracts.workflow import CampaignGapGroup

_PREFIX_RULE = 'facts.path == rule.prefix || facts.path.startsWith(rule.prefix + "/")'


@pytest.mark.parametrize(
    ("path", "prefix", "outcome"),
    [
        ("build/runtime/report.json", "build", "match"),
        ("build/runtime/report.json", "build/runtime", "match"),
        ("build/runtime/report.json", "build/runtime/work", "no-match"),
        ("build-tools/report.json", "build", "no-match"),
    ],
)
def test_restricted_cel_prefix_predicate_preserves_path_boundary(
    path: str, prefix: str, outcome: str
) -> None:
    assert evaluate_cel_predicate(
        _PREFIX_RULE,
        facts={"path": path, "name": path.rsplit("/", maxsplit=1)[-1]},
        policy={},
        rule={"prefix": prefix},
    ) is (outcome == "match")


def test_cel_predicate_rejects_non_boolean_forms() -> None:
    with pytest.raises(TypeError, match="must return a boolean"):
        evaluate_cel_predicate(
            "facts.path",
            facts={"path": "build/report.json", "name": "report.json"},
            policy={},
            rule={},
        )


def test_cel_value_projects_native_json_shapes() -> None:
    assert evaluate_cel_value(
        '{"ready": size(facts.gaps) == 0, "gaps": facts.gaps}',
        facts={"gaps": ["repair"]},
        policy={},
        rule={},
    ) == {"ready": False, "gaps": ["repair"]}


def test_cel_gap_group_rejects_non_list_value() -> None:
    group = CampaignGapGroup(prefix='"gap:"', values='"not-a-list"')

    with pytest.raises(TypeError, match="must return a list"):
        evaluate_cel_gap_groups((group,), facts={}, policy={})


def test_cel_declaration_fails_closed_for_incomplete_or_invalid_rule_decisions() -> None:
    payload = load_generated_artifact_topology_declaration().model_dump(mode="json")
    payload["cel_rule"] = payload["cel_rule"][:-1]

    with pytest.raises(ValueError, match="unique and complete"):
        GeneratedArtifactTopologyDeclaration.model_validate(payload)

    payload = load_generated_artifact_topology_declaration().model_dump(mode="json")
    payload["cel_rule"][0]["decision"] = "allow"

    with pytest.raises(ValueError, match="generated rule must classify"):
        GeneratedArtifactTopologyDeclaration.model_validate(payload)

    payload = load_generated_artifact_topology_declaration().model_dump(mode="json")
    payload["cel_rule"][1]["decision"] = "classify"

    with pytest.raises(ValueError, match="only generated may classify"):
        GeneratedArtifactTopologyDeclaration.model_validate(payload)


def test_named_cel_helpers_fail_closed_for_missing_rule() -> None:
    with pytest.raises(ValueError, match="missing topology CEL rule"):
        topology_contract._cel_rule(load_generated_artifact_topology_declaration(), "missing")


@given(
    path=st.from_regex(r"[a-z][a-z0-9-]{0,8}(?:/[a-z][a-z0-9-]{0,8}){0,3}", fullmatch=True),
    prefix=st.from_regex(r"[a-z][a-z0-9-]{0,8}(?:/[a-z][a-z0-9-]{0,8}){0,2}", fullmatch=True),
)
def test_restricted_cel_prefix_predicate_matches_segment_boundary(path: str, prefix: str) -> None:
    actual = evaluate_cel_predicate(
        _PREFIX_RULE,
        facts={"path": path, "name": path.rsplit("/", maxsplit=1)[-1]},
        policy={},
        rule={"prefix": prefix},
    )
    expected = path == prefix or path.startswith(f"{prefix}/")

    assert actual is expected


def test_topology_cel_rules_compile_and_first_match_witnesses_cover_every_rule() -> None:
    declaration = load_generated_artifact_topology_declaration()
    witnesses = {
        "product-adopter-root": "adopters/acme/report.json",
        "denied-prefix": ".config/ci/scripts/run-python-tests.sh",
        "denied-root-cache": ".import_linter_cache/cache.sqlite",
        "cache-flat": ".cache/tool/state.json",
        "denied-legacy-generated": "build/cache/lychee/archive.tar.gz",
        "runtime-flat": "build/runtime/random-cache/state.json",
        "declarative": ".config/ethos/policy.toml",
        "allowed": "build/ethos/proof/report.json",
        "review": "docs/evidence/2026-07-07.md",
        "denied-generated": ".config/ethos/report.json",
        "repo-root-generated": "report.json",
    }

    assert [rule.id for rule in declaration.cel_rule] == ["generated", *witnesses]
    assert [
        next(
            rule.id
            for rule in declaration.cel_rule
            if rule.decision != "classify"
            and evaluate_cel_predicate(
                rule.expression,
                facts={
                    "path": path,
                    "name": path.rsplit("/", maxsplit=1)[-1],
                    "suffix": ".json" if path.endswith(".json") else "",
                    "generated": path.endswith(".json"),
                },
                policy=declaration.cel_policy(),
                rule={"prefix_group": rule.prefix_group},
            )
        )
        for path in witnesses.values()
    ] == list(witnesses)
    assert [
        path_policy_from_declaration(path, declaration)["decision"] for path in witnesses.values()
    ] == [
        "deny",
        "deny",
        "deny",
        "deny",
        "deny",
        "deny",
        "review",
        "allow",
        "review",
        "deny",
        "deny",
    ]
