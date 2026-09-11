"""CEL topology predicate regression and property tests."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

import ethos.contracts.artifacts.topology as topology_contract
from ethos.contracts.artifacts.topology import GeneratedArtifactTopologyDeclaration
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.contracts.policy.cel import CelEvaluationError
from ethos.contracts.policy.cel import evaluate_cel_gap_groups
from ethos.contracts.policy.cel import evaluate_cel_predicate
from ethos.contracts.policy.cel import evaluate_cel_rules
from ethos.contracts.policy.cel import evaluate_cel_value
from ethos.contracts.policy.cel import validate_cel_expression
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path

_PREFIX_RULE = 'facts.path == rule.prefix || facts.path.startsWith(rule.prefix + "/")'


def test_runtime_topology_is_not_selected_by_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unrelated checkout cannot replace the executing runtime's policy."""
    expected = load_generated_artifact_topology_declaration()
    override = tmp_path / "system/policies/generated-artifact-topology.toml"
    override.parent.mkdir(parents=True)
    override.write_text("incompatible_successor = [\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert load_generated_artifact_topology_declaration() == expected


@pytest.mark.parametrize("present", [False, True])
def test_invalid_runtime_policy_never_falls_back_to_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, present: bool
) -> None:
    """A missing or malformed package resource is a broken runtime, not an override."""
    if present:
        (tmp_path / "topology.toml").write_text("incompatible = [\n", encoding="utf-8")
    monkeypatch.setattr(topology_contract.resources, "files", lambda _package: tmp_path)

    with pytest.raises(tomllib.TOMLDecodeError if present else FileNotFoundError):
        load_generated_artifact_topology_declaration()


@pytest.mark.parametrize(
    ("path", "prefix", "outcome"),
    cast(
        "list[tuple[str, str, str]]",
        literal_case(
            "kernel.test_cel_topology_predicates:parametrize:test_restricted_cel_prefix_predicate_preserves_path_boundary:0"
        ),
    ),
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


def test_cel_evaluation_errors_fail_closed() -> None:
    with pytest.raises(CelEvaluationError, match="divide by zero"):
        evaluate_cel_value("1 / 0", facts={}, policy={}, rule={})


def test_cel_rule_and_gap_group_public_projection_matrix() -> None:
    class Rule:
        def __init__(self, expression: str, gap: str) -> None:
            self.expression, self.gap = expression, gap

    class Group:
        def __init__(self, values: str, prefix: str) -> None:
            self.values, self.prefix = values, prefix

    assert evaluate_cel_rules(
        (Rule("facts.allowed", "'blocked:' + facts.name"), Rule("true", "'unused'")),
        facts={"allowed": False, "name": "change"},
        policy={},
    ) == ["blocked:change"]
    assert evaluate_cel_gap_groups(
        (Group("facts.paths", "'uncovered:'"),),
        facts={"paths": ["src/a.py", "tests/a.py"]},
        policy={},
    ) == ["uncovered:src/a.py", "uncovered:tests/a.py"]
    with pytest.raises(TypeError, match="CEL gap group must return a list"):
        evaluate_cel_gap_groups(
            (Group("facts.path", "'uncovered:'"),),
            facts={"path": "src/a.py"},
            policy={},
        )


def test_cel_expression_validation_rejects_invalid_declarations() -> None:
    expression = "facts.allowed == true"
    assert validate_cel_expression(expression) == expression
    with pytest.raises(ValueError, match="invalid CEL expression"):
        validate_cel_expression("facts[")


def test_cel_declaration_fails_closed_for_incomplete_or_invalid_rule_decisions() -> None:
    payload = load_generated_artifact_topology_declaration().model_dump(mode="json")
    payload["cel_rule"] = payload["cel_rule"][:-1]

    with pytest.raises(ValueError, match="unique and complete"):
        GeneratedArtifactTopologyDeclaration.model_validate(payload)

    payload = load_generated_artifact_topology_declaration().model_dump(mode="json")
    payload["cel_rule"][0]["decision"] = "classify"
    with pytest.raises(ValueError, match="Input should be"):
        GeneratedArtifactTopologyDeclaration.model_validate(payload)


def test_topology_format_does_not_supply_origin() -> None:
    declaration = load_generated_artifact_topology_declaration()
    for path in ("report.json", ".config/settings.json", "docs/page.html"):
        ordinary = path_policy_from_declaration(path, declaration)
        assert ordinary["origin"] == "unclassified"
        assert ordinary["decision"] == "ignore"
        generated = path_policy_from_declaration(path, declaration, origin="machine_evidence")
        assert generated["decision"] == "deny"
        projection = path_policy_from_declaration(path, declaration, origin="projection")
        assert projection["decision"] == "allow"


def test_external_method_pack_shadow_authority_is_denied() -> None:
    policy = path_policy_from_declaration(
        ".superpowers/sdd/tasks/progress.md",
        load_generated_artifact_topology_declaration(),
    )

    assert policy["decision"] == "deny"
    assert policy["required_gap"] == (
        "external_method_pack_shadow_authority:.superpowers/sdd/tasks/progress.md"
    )


def test_topology_path_policy_reuses_immutable_declaration_decision(monkeypatch) -> None:
    declaration = load_generated_artifact_topology_declaration()
    calls = 0
    original = topology_contract.evaluate_cel_predicate

    def counted(*args, **kwargs) -> bool:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(topology_contract, "evaluate_cel_predicate", counted)
    first = path_policy_from_declaration("tools/ci/scripts/cache-regression.md", declaration)
    first_calls = calls
    first["decision"] = "mutated-by-caller"
    second = path_policy_from_declaration("tools/ci/scripts/cache-regression.md", declaration)

    assert first_calls > 0
    assert calls == first_calls
    assert second["decision"] == "review"


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
        "product-adopter-root": ("adopters/sample-adopter/report.json", "unclassified", "deny"),
        "denied-prefix": (".config/ci/scripts/run-python-tests.sh", "unclassified", "deny"),
        "denied-root-cache": (".import_linter_cache/cache.sqlite", "runtime_cache", "deny"),
        "cache-flat": (".cache/tool/state.json", "runtime_cache", "deny"),
        "denied-legacy-generated": ("build/cache/lychee/archive.tar.gz", "runtime_cache", "deny"),
        "runtime-flat": ("build/runtime/random-cache/state.json", "runtime_cache", "deny"),
        "declarative": (".config/ethos/policy.toml", "unclassified", "review"),
        "allowed": ("build/ethos/proof/report.json", "machine_evidence", "allow"),
        "review": ("tools/ci/scripts/check-source.sh", "unclassified", "review"),
        "owned-projection": ("docs/architecture/diagram.mmd", "projection", "allow"),
        "denied-generated": (".config/ethos/report.json", "machine_evidence", "deny"),
        "repo-root-generated": ("report.json", "machine_evidence", "deny"),
    }
    assert [rule.id for rule in declaration.cel_rule] == list(witnesses)
    for identity, (path, origin, decision) in witnesses.items():
        matched = next(
            rule.id
            for rule in declaration.cel_rule
            if evaluate_cel_predicate(
                rule.expression,
                facts={"path": path, "origin": origin, "generated": origin != "unclassified"},
                policy=declaration.cel_policy(),
                rule={"prefix_group": rule.prefix_group},
            )
        )
        assert matched == identity
        assert (
            path_policy_from_declaration(path, declaration, origin=origin)["decision"] == decision
        )
