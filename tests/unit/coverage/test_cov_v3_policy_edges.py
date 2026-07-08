# ruff: noqa: FLY002
"""Coverage-closure v3: policy reachable branches (100% no-exemption)."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import ethos.repository.policy.coupling.registry as coupling_registry
import ethos.repository.policy.coupling.toolchain as coupling_toolchain
import ethos.repository.policy.docstrings.core as docstrings_mod
import ethos.repository.policy.docstrings.style as docstring_style
import ethos.repository.policy.gates as gates_mod
from ethos.repository.policy.gates import Gate
from ethos.repository.policy.rules.check import rules_layer_report
from ethos.repository.policy.rules.config import configured_gate_tables
from ethos.repository.policy.rules.config import configured_rules
from ethos.repository.policy.rules.evaluation import active_valid_exceptions
from ethos.repository.policy.rules.evaluation import match_waiver
from ethos.repository.policy.rules.evaluation import required_gate_details
from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.migration import rules_toml_text
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_rules(root: Path, toml: str) -> None:
    (root / ".ethos").mkdir(parents=True, exist_ok=True)
    (root / ".ethos" / "rules.toml").write_text(toml, encoding="utf-8")


# ---------------------------------------------------------------------------
# ethos.repository.policy.coupling
# ---------------------------------------------------------------------------


def test_gate_profile_gaps_flag_profile_and_toolchain_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A product gate whose profile != "product-toolchain" hits the append at
    # coupling.py 377, and toolchain != "uv-python" hits the append at 379.
    fake = {
        "unit-architecture": Gate(
            id="unit-architecture",
            kind="test",
            command=(),
            profile="mismatch",
            toolchain="mismatch",
        ),
        "ruff": Gate(
            id="ruff",
            kind="lint",
            command=(),
            profile="product-toolchain",
            toolchain="uv-python",
        ),
        "build": Gate(
            id="build",
            kind="package",
            command=(),
            profile="product-toolchain",
            toolchain="uv-python",
        ),
    }
    monkeypatch.setattr(coupling_toolchain, "gate_registry", lambda: fake)

    gaps = coupling_toolchain.gate_profile_gaps()

    assert "gate_profile_mismatch:unit-architecture:mismatch" in gaps
    assert "gate_toolchain_mismatch:unit-architecture:mismatch" in gaps


def test_branch_role_metadata_recovers_from_invalid_workspace_toml(tmp_path: Path) -> None:
    # A workspace.toml that exists but is not valid TOML triggers the
    # TOMLDecodeError handler that resets payload to {} (coupling.py 425-426).
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "workspace.toml").write_text("[section\n", encoding="utf-8")

    metadata = coupling_registry.branch_role_policy_metadata(tmp_path)

    assert metadata["default_policy"] is True


def test_binding_taxonomy_flags_non_hard_binding_owning_semantics() -> None:
    # expected owns_product_semantics is True (so the 559 guard is skipped) while a
    # non-hard-binding entry claims product semantics -> the append at coupling.py 569.
    gaps = coupling_registry.binding_taxonomy_gaps(
        "x",
        {"layer": "profile_or_adapter_binding", "owns_product_semantics": True},
        {"layer": "product_semantic_hard_binding", "owns_product_semantics": True},
    )

    assert "binding_registry_product_semantics:x" in gaps


def test_adapter_admission_flags_missing_required_field() -> None:
    # An adapter entry whose admission dict lacks a required field appends the
    # per-field gap inside the loop (coupling.py 582).
    gaps = coupling_registry.adapter_admission_gaps(
        "x",
        {"layer": "profile_or_adapter_binding", "admission": {}},
    )

    assert "binding_registry_adapter_admission_field:x:authority_ref" in gaps


# ---------------------------------------------------------------------------
# ethos.repository.policy.docstrings
# ---------------------------------------------------------------------------


def test_signature_issues_empty_when_all_args_documented() -> None:
    # With no missing args the `if missing` at docstrings.py 334 is False (334->344),
    # and with no extra args the `if extra` at 344 is False (344->354) -> returns [].
    node = ast.parse(
        'def f(a):\n    """Do it.\n\n    Args:\n        a: the value.\n    """\n'
    ).body[0]
    docstring = ast.get_docstring(node)

    assert docstring_style.signature_issues("api.py", "m.f", node, docstring) == []


def test_documented_args_skips_non_matching_line() -> None:
    # A blank/non-identifier line produces no regex match, so the `if match` at
    # docstrings.py 374 is False and control loops back to 369 (374->369).
    assert docstring_style.documented_args(("   ",)) == set()


def test_module_name_without_src_segment() -> None:
    # A relative path with no "src" segment makes the guard at docstrings.py 441
    # False, skipping the slice and falling to 443 (441->443).
    assert docstrings_mod._module_name("foo/bar.py") == "foo.bar"


def test_explicit_exports_ignores_non_sequence_all_value() -> None:
    # An `__all__` assigned a non list/tuple/set value fails the isinstance guard at
    # docstrings.py 458 and loops back to 450 (458->450) -> nothing collected.
    tree = ast.parse('__all__ = "single"\n')

    assert docstrings_mod._explicit_exports(tree) == set()


def test_explicit_exports_skips_non_constant_element() -> None:
    # A non-Constant element (a Name) inside __all__ fails the guard at
    # docstrings.py 460 and loops back to 459 (460->459); the str constant is kept.
    tree = ast.parse("__all__ = [foo, 'ok']\n")

    assert docstrings_mod._explicit_exports(tree) == {"ok"}


# ---------------------------------------------------------------------------
# ethos.repository.policy.gates
# ---------------------------------------------------------------------------


def test_gate_registry_does_not_overwrite_existing_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A quality gate whose id already exists in the base registry makes the guard at
    # gates.py 192 False so it loops back to 191 without overwriting (192->191).
    monkeypatch.setattr(
        gates_mod,
        "quality_gate_registry",
        lambda: {"ruff": Gate(id="ruff", kind="lint", command=("overwritten",))},
    )

    registry = gates_mod.gate_registry()

    assert registry["ruff"].command == ("tools/ci/scripts/run-python-lint.sh",)


# ---------------------------------------------------------------------------
# ethos.repository.policy.rules
# ---------------------------------------------------------------------------


def test_configured_rules_without_globs_or_gates(tmp_path: Path) -> None:
    # A rule table lacking path_globs (rules.py 237 False -> 237->239) and
    # required_gates (239 False -> 239->241) omits both keys from the payload.
    _write_rules(tmp_path, '[[rule]]\nid = "x.y"\nowner = "team"\n')

    rules = configured_rules(tmp_path)

    assert rules == [{"id": "x.y", "owner": "team", "version": 1, "profile_layers": []}]


def test_active_valid_exceptions_skips_inactive_item() -> None:
    # A dict exception whose status is not "active" fails the guard at rules.py 547
    # and loops back to 546 (547->546) without being collected.
    active = active_valid_exceptions({"required_gaps": [], "exceptions": [{"status": "expired"}]})

    assert active == []


def test_match_waiver_skips_scope_mismatch() -> None:
    # A matching rule_id whose scope does not match the path fails the check at
    # rules.py 562 and loops back to 558 (562->558) -> no waiver returned.
    waiver = match_waiver(
        rule_id="r",
        path="src/a.py",
        exceptions=[{"rule_id": "r", "scope": "path:other"}],
    )

    assert waiver is None


def test_rules_evaluation_prove_skips_gate_requirements(tmp_path: Path) -> None:
    # phase == "prove" makes the guard at rules.py 621 False (621->626), so a matched
    # blocking rule contributes no gate_required gaps.
    report = rules_evaluation_report(tmp_path, phase="prove", changed_paths=(".ethos/rules.toml",))

    gaps = [str(gap) for gap in report["required_gaps"]]
    assert not any(gap.startswith("gate_required:") for gap in gaps)


def test_required_gate_details_skips_idless_detail() -> None:
    # A required_gates_detail entry without an "id" fails the guard at rules.py 758
    # and loops back to 757 (758->757) -> nothing collected.
    assert required_gate_details([{"required_gates_detail": [{"command": "x"}]}]) == []


def test_rules_layer_report_strict_with_full_subject_depth(tmp_path: Path) -> None:
    # A strict profile whose configured rules cover every depth subject makes the
    # `if missing` at rules.py 806 False, skipping the append and falling to 809.
    rule_block = "\n".join(
        "\n".join(
            [
                "[[rule]]",
                f'id = "custom.{subject}"',
                'owner = "team"',
                'authority_ref = "docs/x.md"',
                'contract_ref = "docs/x.md"',
                f'subject = "{subject}"',
                'path_globs = ["x/**"]',
                'severity = "advisory"',
                "required_gates = []",
                'stop_condition = "x_gap"',
                "",
            ]
        )
        for subject in ("contract", "transition", "evidence", "stop")
    )
    _write_rules(tmp_path, '[profiles]\nactive = ["strict"]\n\n' + rule_block)

    report = rules_layer_report(tmp_path)

    assert report["strict"] is True
    assert "rules_strict_subject_coverage_missing" not in report["required_gaps"]


def test_configured_gate_tables_command_blocking_and_empty(tmp_path: Path) -> None:
    # only_blocking has no "command" (904->906); only_command has no "blocking"
    # (906->908); empty_gate yields an empty payload so `if payload` is False and the
    # entry is dropped (908->899).
    _write_rules(
        tmp_path,
        "\n".join(
            [
                "[gates.only_blocking]",
                "blocking = true",
                "",
                "[gates.only_command]",
                'command = "run x"',
                "",
                "[gates.empty_gate]",
                'note = "z"',
                "",
            ]
        ),
    )

    gates = configured_gate_tables(tmp_path)

    assert gates == {
        "only_blocking": {"blocking": True},
        "only_command": {"command": "run x"},
    }


def test_rules_toml_text_gate_missing_one_key() -> None:
    # A gate dict with only "command" makes the `if key in gate` at rules.py 925 False
    # for "blocking", looping back to 924 (925->924); the command line is still emitted.
    text = rules_toml_text([], gates={"g": {"command": "run x"}})

    assert "[gates.g]" in text
    assert "command = " in text
    assert "blocking = " not in text


# ---------------------------------------------------------------------------
# ethos.repository.profile
# ---------------------------------------------------------------------------


def test_load_profile_skips_non_string_root_and_non_list_evidence(tmp_path: Path) -> None:
    # An empty-string root value fails the guard at profile.py 80 (80->79) so the
    # default root is preserved; a non-list evidence value fails 85 (85->84) so the
    # evidence key is not collected.
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "profile.toml").write_text(
        '[roots]\ndocs = ""\n\n[evidence]\ndurable_roots = "x"\n',
        encoding="utf-8",
    )

    profile = load_repository_profile(tmp_path)

    assert profile.roots["docs"] == "docs"
    assert "durable_roots" not in profile.evidence
