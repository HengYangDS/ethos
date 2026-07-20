"""Focused regressions for the repository-owned shell lexer."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.source_budget.measurement.native.core as native_core
import ethos.adapters.repo.source_budget.measurement.native.shell.core as shell_core
import ethos.adapters.repo.source_budget.measurement.native.shell.grammar as shell_grammar
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement.native.shell.core import shell_tokens

if TYPE_CHECKING:
    from typing import Any

    from ethos_core.contracts.source_budget.metrics import MetricContract

ROOT = Path(__file__).resolve().parents[5]
CASES_PATH = ROOT / "tests" / "fixtures" / "source-budget-v2" / "cases.toml"


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict[str, Any]]:
    payload = tomllib.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in payload["case"]}


@lru_cache(maxsize=1)
def _registry():
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _content(case_id: str) -> bytes:
    case = _cases()[case_id]
    return str(case["text"]).encode() if "text" in case else bytes.fromhex(str(case["hex"]))


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    return tuple(
        sorted(
            (item for item in _registry().contracts if item.metric_profile == profile),
            key=lambda item: (item.metric_id, item.unit, item.contract_id),
        )
    )


def _measure(case_id: str):
    case = _cases()[case_id]
    return native_core.measure_native(_content(case_id), _contracts(str(case["profile"])))


def _success(case_id: str):
    load = _measure(case_id)
    assert load.required_gaps == ()
    assert load.measurement is not None
    return load.measurement


def _failure(case_id: str, expected_gap: str) -> None:
    load = _measure(case_id)
    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)


def _values(measurement) -> dict[str, int]:
    return {item.metric_id: item.value for item in measurement.values}


@pytest.mark.parametrize(
    "source",
    [
        "f() { :; }\n",
        "f () { :; }\n",
        "f()\n{ :; }\n",
        "function f { :; }\n",
        "function f() { :; }\n",
        "function f\n{ :; }\n",
    ],
)
@pytest.mark.timeout(2)
def test_shell_accepts_function_definition_brace_context(source: str) -> None:
    assert shell_tokens(source)[-1] == ("OP", "}")


def test_shell_keeps_non_function_brace_as_a_word() -> None:
    assert shell_tokens("echo {\n") == (("WORD", "echo"), ("WORD", "{"))


def test_shell_preserves_command_start_across_line_continuation() -> None:
    tokens = shell_tokens("if true && \\\n{ :; }\n")

    assert ("OP", "{") in tokens


def test_assignment_prefix_uses_a_positional_compiled_match(monkeypatch) -> None:
    assignment_prefix_end = vars(shell_core)["_assignment_prefix_end"]
    monkeypatch.setattr(
        shell_core.re,
        "match",
        lambda *_args, **_kwargs: pytest.fail("tail-copying re.match call"),
    )

    assert assignment_prefix_end("name=value", 0) == 5


@pytest.mark.parametrize(
    ("text", "message"),
    [(";", "shell lexer made no progress"), ("", "shell word is empty")],
)
def test_shell_word_defensive_guards(text: str, message: str) -> None:
    shell_word = vars(shell_core)["_shell_word"]
    with pytest.raises(ValueError, match=message):
        shell_word(
            text,
            0,
            allow_array_assignment=False,
        )


def test_shell_array_assignment_depth_paths() -> None:
    assert shell_tokens("a[x[y]]=v\n") == (("WORD", "a[x[y]]=v"),)
    assert shell_tokens("a[=v\n") == (("WORD", "a[=v"),)


def test_nested_case_redirection_paths() -> None:
    assert shell_tokens("echo $(case x in esac 2>/dev/null)\n")
    assert shell_tokens("echo $(case x in esac <<EOF\nbody\nEOF\n)\n")


def test_parameter_expansion_defensive_progress_guard(monkeypatch) -> None:
    parameter_expansion_end = vars(shell_core)["_parameter_expansion_end"]
    monkeypatch.setattr(
        shell_core,
        "_shell_word",
        lambda _text, index, **_kwargs: ((), index, False),
    )
    with pytest.raises(ValueError, match="shell lexer made no progress"):
        parameter_expansion_end("${x}", 1)


def test_closing_brace_without_boundary_remains_word_text() -> None:
    assert shell_tokens("echo }x\n") == (("WORD", "echo"), ("WORD", "}x"))


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("function 1 { :; }\n", "shell function name is invalid"),
        ("f() word\n", "shell function body is missing"),
        ("function (\n", "shell function name is missing"),
        ("f( ;\n", "shell function signature is not empty"),
        ("f() ;\n", "shell function body is missing"),
        ("function\n", "shell function header is incomplete"),
        ("case x in esac > >\n", "shell case redirection target is missing"),
        ("case x in esac (\n", "shell case closure tail is invalid"),
        ("case x in |\n", "shell case pattern alternative is empty"),
    ],
)
def test_shell_rejects_finite_grammar_error_states(source: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        shell_tokens(source)


def test_shell_accepts_disabled_function_tracking_and_direct_case_close() -> None:
    assert shell_tokens("echo $((\n1))\n")
    assert shell_tokens("case x in x) esac")


def test_heredoc_fragment_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="shell heredoc delimiter is invalid"):
        shell_grammar.heredoc_fragment("NOPE", "x")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("$'x\\ty'", "x\ty"), ("$'\\101'", "A"), ("$'\\q'", "\\q")],
)
def test_ansi_c_heredoc_escape_decoding(value: str, expected: str) -> None:
    assert shell_grammar.heredoc_fragment("ANSI_QUOTED", value) == expected


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("$'\\'", "shell ANSI-C escape is unterminated"),
        ("$'\\u'", "shell ANSI-C Unicode escape is invalid"),
        ("$'\\c'", "shell ANSI-C control escape is invalid"),
    ],
)
def test_ansi_c_heredoc_escape_errors(value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        shell_grammar.heredoc_fragment("ANSI_QUOTED", value)


@pytest.mark.parametrize(
    "case_id",
    [
        "shell-arithmetic-shifts",
        "shell-case-keyword-words",
        "shell-heredoc-word-fragments",
        "shell-heredoc-double-quoted-fragments",
    ],
)
def test_shell_accepts_arithmetic_case_and_heredoc_word_boundaries(
    case_id: str,
) -> None:
    assert _success(case_id).values


def test_shell_rejects_unterminated_backtick_inside_double_quotes() -> None:
    _failure(
        "shell-unterminated-backtick-in-double-quote",
        "source_budget_native_parse_failed:shell",
    )
    _failure(
        "shell-operator-heredoc-delimiter",
        "source_budget_native_parse_failed:shell",
    )


def test_shell_rejects_every_unclosed_or_unmatched_group() -> None:
    for case_id in (
        "shell-unclosed-quoted-parameter",
        "shell-unclosed-array",
        "shell-unclosed-test",
        "shell-unclosed-arithmetic-command",
        "shell-unmatched-group",
        "shell-heredoc-missing-delimiter",
    ):
        _failure(case_id, "source_budget_native_parse_failed:shell")
    load = native_core.measure_native(b"cat <<\n", _contracts("shell-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_parse_failed:shell",)
    assert _success("shell-ansi-heredoc").values


@pytest.mark.parametrize(
    "case_id",
    [
        "shell-array-arithmetic-shifts",
        "shell-parameter-literal-shifts",
        "shell-ansi-escaped-heredoc",
        "shell-line-continuation-heredoc",
        "shell-literal-expansion-heredoc-delimiters",
        "shell-array-assignment-fragments",
        "shell-reserved-spellings-in-words",
        "shell-command-words-in-arguments",
        "shell-case-optional-leading-paren",
        "shell-inline-empty-case",
        "shell-noncase-expansion-contexts",
        "shell-ansi-c-heredoc-delimiters",
        "shell-case-closure-redirection-tails",
    ],
)
def test_shell_accepts_array_parameter_and_quote_removed_heredoc_forms(
    case_id: str,
) -> None:
    assert _success(case_id).values


@pytest.mark.parametrize(
    ("case_id", "expected_lexical_tokens"),
    [
        ("shell-unmatched-bracket-word-boundaries", 6),
        ("shell-spaced-bracket-word-boundaries", 5),
    ],
)
def test_shell_preserves_non_assignment_bracket_word_boundaries(
    case_id: str,
    expected_lexical_tokens: int,
) -> None:
    assert _values(_success(case_id))["lexical_tokens"] == expected_lexical_tokens


@pytest.mark.parametrize(
    "case_id",
    [
        "shell-comment-heredoc-delimiter-attached",
        "shell-comment-heredoc-delimiter-separated",
    ],
)
def test_shell_rejects_comment_instead_of_heredoc_delimiter(case_id: str) -> None:
    _failure(case_id, "source_budget_native_parse_failed:shell")


def test_shell_rejects_mixed_unclosed_nested_substitution() -> None:
    _failure("shell-unclosed-nested-substitution", "source_budget_native_parse_failed:shell")


def test_shell_accepts_ansi_c_escaped_quote() -> None:
    assert _success("shell-ansi-escaped-quote").values


def test_shell_accepts_mixed_nested_substitution() -> None:
    assert _success("shell-nested-substitution").values


@pytest.mark.parametrize(
    "source",
    [
        "echo $(echo $(date))\n",
        "echo <(cat <(printf x))\n",
        'value="$(echo $(date))"\n',
        'echo "$((1 + $(printf 2)))"\n',
    ],
)
def test_shell_accepts_contextual_nested_substitution_closers(source: str) -> None:
    load = native_core.measure_native(source.encode(), _contracts("shell-source-v2"))

    assert load.required_gaps == ()
    assert load.measurement is not None


def test_shell_accepts_bounded_deep_parameter_expansion() -> None:
    depth = 20
    source = "echo " + ("${x:-" * depth) + "z" + ("}" * depth) + "\n"

    load = native_core.measure_native(source.encode(), _contracts("shell-source-v2"))

    assert load.required_gaps == ()
    assert load.measurement is not None


def test_shell_recursion_exhaustion_reports_stable_resource_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contracts = _contracts("shell-source-v2")
    assert native_core.measure_native(b"echo ready\n", contracts).measurement is not None

    def exhausted(_source: str) -> tuple[str, ...]:
        message = "SENSITIVE"
        raise RecursionError(message)

    monkeypatch.setattr(native_core, "shell_tokens", exhausted)
    load = native_core.measure_native(b"echo unreachable\n", contracts)

    assert load.required_gaps == ("source_budget_native_resource_exhausted",)
    assert load.measurement is None


def test_shell_rejects_unclosed_group_inside_substitution() -> None:
    _failure(
        "shell-unclosed-group-in-substitution",
        "source_budget_native_parse_failed:shell",
    )
