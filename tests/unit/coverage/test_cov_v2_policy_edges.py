# ruff: noqa: ARG005, FLY002
"""Coverage-closure edge tests for the policy rules/docstrings/exceptions cluster.

Each test drives one or more previously-uncovered lines in
``ethos.repository.policy.rules``, ``ethos.repository.policy.docstrings`` and
``ethos.repository.policy.rules_exceptions`` (v2 100% no-exemption campaign).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import ethos.repository.policy.docstrings.core as docstrings_mod
import ethos.repository.policy.docstrings.style as docstring_style
from ethos.repository.policy.rules import check as check_mod
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.exceptions import _is_product_root
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.exceptions import ttl_days_or_none
from ethos.repository.policy.rules.migration import migrate_legacy_rules
from tests.support import write_text as _write

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_rules(root: Path, toml: str) -> None:
    (root / ".ethos").mkdir(parents=True, exist_ok=True)
    (root / ".ethos" / "rules.toml").write_text(toml, encoding="utf-8")


# ---------------------------------------------------------------------------
# ethos.repository.policy.rules
# ---------------------------------------------------------------------------


def test_migrate_emits_invalid_marker_for_non_table_rule(tmp_path: Path) -> None:
    # `rule` is a list whose entry is not a table -> _configured_rules records the
    # {"id": "", "_invalid": "rule_not_table"} marker and continues (rules.py 202-203).
    # The blank id then makes _rules_toml_text skip the rule (rules.py 930).
    _write_rules(tmp_path, 'rule = ["not-a-table"]\n')

    report = migrate_legacy_rules(tmp_path)

    assert report["target"]["rule"] == [{"id": "", "_invalid": "rule_not_table"}]
    assert "[[rule]]" not in report["target_text"]


def test_migrate_serializes_version_and_non_waivable(tmp_path: Path) -> None:
    # non_waivable present -> _configured_rules coerces it to bool (rules.py 244).
    # version != 1 -> emitted (rules.py 946); non_waivable in rule -> emitted (rules.py 957).
    _write_rules(
        tmp_path,
        "\n".join(
            [
                "[[rule]]",
                'id = "custom.x"',
                'owner = "team"',
                "version = 2",
                "non_waivable = true",
                'authority_ref = "docs/x.md"',
                'contract_ref = "docs/x.md"',
                'path_globs = ["x/**"]',
                'severity = "advisory"',
                "required_gates = []",
                'stop_condition = "x_gap"',
                "",
            ]
        ),
    )

    target = migrate_legacy_rules(tmp_path)["target"]
    text = migrate_legacy_rules(tmp_path)["target_text"]

    assert target["rule"][0]["non_waivable"] is True
    assert "version = 2" in text
    assert "non_waivable = true" in text


def test_gate_config_non_table_entry_is_ignored(tmp_path: Path) -> None:
    # A `[gates]` value that is a string rather than a table is skipped by both
    # _gate_definitions (rules.py 276, reached through rules_check_report) and
    # _configured_gate_tables (rules.py 901, reached through migrate_legacy_rules).
    _write_rules(
        tmp_path,
        '[profiles]\nactive = ["generic"]\n\n[gates]\nfoo = "not-a-table"\n',
    )

    check = rules_check_report(tmp_path)
    migration = migrate_legacy_rules(tmp_path)

    assert "foo" not in check["required_gaps"]
    assert migration["target"].get("gates", {}) == {}


def test_rules_check_skips_non_dict_compiled_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A non-dict entry inside compiled["rules"] is skipped by the `if not isinstance`
    # guard inside rules_check_report (rules.py 443).
    real = compile_rules(tmp_path)
    payload = {**real, "rules": ["bogus-not-a-dict", *real["rules"]]}
    monkeypatch.setattr(check_mod, "compile_rules", lambda root: payload)

    report = rules_check_report(tmp_path)

    assert "bogus-not-a-dict" not in report["resolved_rules"]
    assert report["resolved_rules"]


def test_is_product_root_is_false_without_product_markers(tmp_path: Path) -> None:
    # Executes the module-local _is_product_root body (rules.py 985); an empty tmp
    # tree lacks packages/ethos/README.md so the conjunction short-circuits to False.
    assert _is_product_root(tmp_path) is False


# ---------------------------------------------------------------------------
# ethos.repository.policy.docstrings
# ---------------------------------------------------------------------------


def test_advisory_inventory_skips_private_and_overload_defs(tmp_path: Path) -> None:
    # Private (_private) and typing-overload defs are skipped by the guard at
    # docstrings.py 222; the overload detection covers both the ast.Name form
    # (@overload -> 254) and the ast.Attribute form (@mod.overload -> 256).
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        'paths = ["packages/sample/src/sample/api.py"]\nfail_under = 0\nexclude_roots = []\n',
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '"""Sample module."""\n'
        "import mod\n\n"
        "def _private():\n    pass\n\n"
        "@overload\ndef f(): ...\n\n"
        "@mod.overload\ndef g(): ...\n",
    )

    report = docstrings_mod.docstring_coverage_report(tmp_path)
    inventory = report["advisory_public_definition_inventory"]

    # Only the (documented) module itself is counted; all body defs were skipped.
    assert inventory["total_count"] == 1
    assert inventory["missing_count"] == 0


def test_style_issues_short_circuit_for_non_google_style(tmp_path: Path) -> None:
    # A non-"google" style makes _style_issues return [] immediately (docstrings.py 262),
    # so the legacy :param marker in the docstring raises no style issue.
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        'paths = ["packages/sample/src/sample/api.py"]\n'
        "fail_under = 0\n"
        'style = "rst"\n'
        "exclude_roots = []\n",
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '"""Module."""\n'
        '__all__ = ["thing"]\n\n'
        "def thing():\n"
        '    """Legacy.\n\n    :param x: value.\n    """\n',
    )

    report = docstrings_mod.docstring_coverage_report(tmp_path)

    assert report["style_issue_count"] == 0


def test_docstring_issues_flag_empty_colon_and_weak_summaries() -> None:
    # Whitespace-only docstring -> empty summary issue (docstrings.py 295);
    # summary ending in ":" -> summary_colon issue (297); weak generic word -> 301.
    empty = docstring_style.docstring_issues("api.py", "m.f", 1, "   ")
    colon = docstring_style.docstring_issues("api.py", "m.f", 1, "Configure things:")
    weak = docstring_style.docstring_issues("api.py", "m.f", 1, "helper")

    assert [issue.code for issue in empty] == ["empty"]
    assert [issue.code for issue in colon] == ["summary_colon"]
    assert "weak_summary" in {issue.code for issue in weak}


def test_signature_arg_names_include_var_and_kw_args() -> None:
    # *args populates the vararg branch (docstrings.py 361) and **kwargs the kwarg
    # branch (363); self is filtered out.
    node = ast.parse("def f(self, a, *args, **kwargs): ...").body[0]

    names = docstring_style.signature_arg_names(node)

    assert names == ("a", "args", "kwargs")


def test_documented_args_strips_bullet_prefix() -> None:
    # A bullet-prefixed arg line has its leading marker stripped before matching
    # the arg name (docstrings.py 372).
    assert docstring_style.documented_args(("- value (int): Input value.",)) == {"value"}


def test_sections_resets_current_on_unindented_heading() -> None:
    # A new unindented heading line that is not a Google section resets `current`
    # to None (docstrings.py 390), so the following text is not captured.
    docstring = "Summary.\n\nArgs:\n    value: desc\nCustom:\n    ignored\n"

    sections = docstring_style.sections(docstring)

    assert sections["Args"] == ("    value: desc",)
    assert "Custom" not in sections


def test_legacy_markers_capture_field_prefix() -> None:
    # A legacy `:param` field line yields its first token as a marker (docstrings.py 411).
    assert docstring_style.legacy_docstring_markers(":param value: input.") == (":param",)


def test_explicit_exports_skips_non_all_assignment() -> None:
    # A plain assignment that is not __all__ is skipped via `continue` (docstrings.py 457),
    # while the real __all__ list is still collected.
    tree = ast.parse("x = 5\n__all__ = ['exported']\n")

    assert docstrings_mod._explicit_exports(tree) == {"exported"}


def test_decorator_is_command_matches_name_and_rejects_other() -> None:
    # A bare *command Name decorator matches via fnmatch (docstrings.py 474-475);
    # a decorator that is neither Call/Attribute/Name falls through to False (476).
    name_deco = ast.parse("@app_command\ndef f(): ...").body[0].decorator_list[0]

    assert docstrings_mod._decorator_is_command(name_deco) is True
    assert docstrings_mod._decorator_is_command(ast.Constant(value=1)) is False


# ---------------------------------------------------------------------------
# ethos.repository.policy.rules_exceptions
# ---------------------------------------------------------------------------


def test_policy_exceptions_flag_non_table_exception(tmp_path: Path) -> None:
    # An `exception` list entry that is not a table records the malformed gap and
    # continues (rules_exceptions.py 66-67).
    path = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    path.parent.mkdir(parents=True)
    path.write_text('exception = ["not-a-table"]\n', encoding="utf-8")

    report = policy_exceptions_report(tmp_path)

    assert "policy_exception_malformed" in report["required_gaps"]


def test_ttl_days_requires_day_suffix() -> None:
    # A max_ttl value lacking the trailing "d" is not a valid TTL (rules_exceptions.py 232).
    assert ttl_days_or_none("10") is None
