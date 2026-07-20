from __future__ import annotations

import ast
import hashlib
import importlib
import re
import subprocess
import sys
import tomllib
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.metrics import MetricContract

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType
    from typing import Any

ROOT = Path(__file__).resolve().parents[5]
CASES_PATH = ROOT / "tests" / "fixtures" / "source-budget-v2" / "cases.toml"
NATIVE_MODULE = "ethos.adapters.repo.source_budget.measurement.native.core"
REVIEWED_CONFORMANCE_DIGESTS = {
    "c4": "5f8bac5ef288997b60fb1cedaf08790c8ae1adc5c0471a57f36318e10d35735c",
    "ini": "b502516798252b49f65c0a9a0113e1abc12c9e0f90e782fd20a8af11f18eb2fa",
    "jinja": "337d89fad45ac03517fd3b60d090a8d850f60714b11cd894e0aa8bedf4ca068b",
    "json": "9f66c10e9ca91655f6b6efc1a212d1f28b5a17bba80431a671e63838559e1752",
    "python": "ce3459c91f2d4185791ff067dfb52bba4b53930c2c9e8a1b6ffbd1597a561176",
    "shell": "a4d8d0b5590b4c69b298cbceb4655c9c551948fda7781e4be0bc667a90fc03c7",
    "toml": "4e0a08136432076ce5771746128ef9079c8d839b980157104464a93c5129e2e1",
    "utf8-control": "45d13f0f9cd68df46c317ad4d10d720cfdde11e5ab95d062a64b0938398d0e50",
    "utf8-footprint": "156f5c6465dbf820bdf522220411dbf5f072e53edb3b4866a0e188f4bb92f23d",
    "yaml": "5f6c7dbff96e3281b4b21968f5c1321f9f12cbe19e7be8db352a67d232ae7327",
}
EXPECTED_CASE_IDS = set(
    re.findall(
        r"[a-z0-9-]+",
        """
        c4-a c4-b c4-malformed c4-unknown ini-a ini-b ini-duplicate jinja-base jinja-comment
        jinja-dynamic jinja-invalid json-a json-b json-duplicate json-nonfinite
        python-comment-long python-comment-short python-identifier-a python-identifier-b
        python-invalid python-lines python-literal-a python-literal-b python-packed
        shell-constructs shell-heredoc shell-unterminated-heredoc shell-unterminated-quote
        toml-a toml-b toml-duplicate utf8-bom utf8-crlf utf8-embedded-bom utf8-invalid utf8-lf
        yaml-a yaml-anchor yaml-b yaml-duplicate yaml-nonfinite yaml-on-quoted yaml-on-string
        yaml-tag yaml-unhashable-key ini-default c4-comment-escape c4-wrong-quote
        c4-inline-quote c4-backslash-end c4-empty shell-extra-forms shell-dangling-escape
        shell-literal-dollar shell-case-patterns shell-regex-anchor shell-substitution-comment
        shell-substitution-comment-eof shell-substitution-heredoc-missing-delimiter
        shell-substitution-case-unterminated shell-unterminated-substitution
        shell-literal-expansion-heredoc-delimiters shell-heredoc-no-body jinja-no-trailing-newline
        jinja-trailing-newline jinja-trailing-crlf yaml-date-plain yaml-date-quoted
        yaml-timestamp-explicit shell-unclosed-quoted-parameter shell-unclosed-array
        shell-unclosed-test shell-unclosed-arithmetic-command shell-unmatched-group
        shell-heredoc-missing-delimiter shell-ansi-heredoc shell-unclosed-nested-substitution
        shell-ansi-escaped-quote shell-nested-substitution shell-unclosed-group-in-substitution
        shell-arithmetic-shifts shell-case-keyword-words
        shell-unterminated-backtick-in-double-quote shell-heredoc-word-fragments
        yaml-legacy-octal-plain yaml-legacy-octal-quoted yaml-core-octal yaml-decimal-ten
        yaml-sexagesimal-plain yaml-sexagesimal-quoted yaml-scientific yaml-exponent
        yaml-float-thousand yaml-decimal-twelve yaml-leading-zero-eight yaml-decimal-eight
        yaml-underscored-plain yaml-underscored-quoted yaml-negative-hex-plain
        yaml-negative-hex-quoted yaml-binary-plain yaml-binary-quoted yaml-merge-token-plain
        yaml-merge-token-quoted yaml-value-token-plain yaml-value-token-quoted
        yaml-explicit-core-valid yaml-explicit-int-invalid yaml-explicit-float-invalid
        yaml-explicit-bool-invalid yaml-explicit-null-invalid yaml-leading-zero-duplicate
        yaml-version-1-2 yaml-version-1-1 shell-heredoc-double-quoted-fragments
        shell-operator-heredoc-delimiter yaml-core-hex yaml-decimal-fifty-eight
        yaml-positive-inf yaml-negative-inf shell-array-arithmetic-shifts
        shell-comment-heredoc-delimiter-attached shell-comment-heredoc-delimiter-separated
        jinja-dynamic-literal-short jinja-dynamic-literal-long
        shell-parameter-literal-shifts shell-ansi-escaped-heredoc
        shell-line-continuation-heredoc shell-array-assignment-fragments
        shell-reserved-spellings-in-words shell-command-words-in-arguments
        shell-case-optional-leading-paren shell-inline-empty-case shell-case-subject-missing
        shell-case-subject-multiple shell-case-subject-fragment shell-case-empty-pattern
        shell-case-subject-newline shell-case-after-if-unterminated
        shell-case-after-time-unterminated shell-noncase-expansion-contexts
        shell-ansi-c-heredoc-delimiters shell-unmatched-standalone-brace
        shell-unmatched-bracket-word-boundaries shell-spaced-bracket-word-boundaries
        shell-array-shift-in-argument shell-case-pattern-multiple-words
        shell-case-pattern-newline shell-case-alternative-newline shell-case-closure-extra-word
        shell-case-closure-redirection-extra-word shell-case-closure-trailing-separator
        shell-case-closure-redirection-tails
        """,
    )
)


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict[str, Any]]:
    payload = tomllib.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert payload["schema"] == "ethos-source-budget-native-cases-v1"
    rows = payload["case"]
    assert isinstance(rows, list)
    result = {str(row["id"]): row for row in rows}
    assert len(result) == len(rows)
    return result


@lru_cache(maxsize=1)
def _registry():
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _case(case_id: str) -> dict[str, Any]:
    return _cases()[case_id]


def _content(case_id: str) -> bytes:
    case = _case(case_id)
    if "text" in case:
        return str(case["text"]).encode("utf-8")
    return bytes.fromhex(str(case["hex"]))


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    contracts = tuple(item for item in _registry().contracts if item.metric_profile == profile)
    assert contracts
    return tuple(sorted(contracts, key=lambda item: (item.metric_id, item.unit, item.contract_id)))


def _native() -> ModuleType:
    try:
        return importlib.import_module(NATIVE_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name and NATIVE_MODULE.startswith(exc.name):
            pytest.fail(f"missing native measurement provider:{NATIVE_MODULE}", pytrace=False)
        raise


def _measure(case_id: str, contracts: tuple[MetricContract, ...] | None = None):
    case = _case(case_id)
    resolved = contracts or _contracts(str(case["profile"]))
    return _native().measure_native(_content(case_id), resolved)


def _success(case_id: str):
    load = _measure(case_id)
    assert load.required_gaps == ()
    assert load.measurement is not None
    return load.measurement


def _failure(case_id: str, expected_gap: str):
    load = _measure(case_id)
    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)
    return load


def _values(measurement) -> dict[str, int]:
    return {item.metric_id: item.value for item in measurement.values}


@pytest.fixture(autouse=True)
def _isolate_native_conformance_cache() -> Iterator[None]:
    module = sys.modules.get(NATIVE_MODULE)
    if module is not None:
        importlib.reload(module)
    yield
    module = sys.modules.get(NATIVE_MODULE)
    if module is not None:
        importlib.reload(module)


def test_case_carrier_is_complete_xor_and_materializes_logical_suffixes(
    tmp_path: Path,
) -> None:
    cases = _cases()
    assert set(cases) == EXPECTED_CASE_IDS
    for case_id, case in cases.items():
        assert case["id"] == case_id
        assert isinstance(case["filename"], str)
        assert Path(case["filename"]).name == case["filename"]
        assert isinstance(case["profile"], str)
        assert case["profile"]
        assert ("text" in case) ^ ("hex" in case)
        content = _content(case_id)
        if "hex" in case:
            assert str(case["hex"]) == content.hex()
        target = tmp_path / str(case["filename"])
        target.write_bytes(content)
        assert target.suffix == Path(str(case["filename"])).suffix
        assert target.read_bytes() == content


def test_utf8_bom_and_newlines_normalize_values_but_preserve_raw_identity() -> None:
    measurements = tuple(_success(case_id) for case_id in ("utf8-lf", "utf8-crlf", "utf8-bom"))
    assert len({item.normalized_digest for item in measurements}) == 1
    assert len({item.values for item in measurements}) == 1
    assert len({item.content_sha256 for item in measurements}) == 3
    for case_id, measurement in zip(
        ("utf8-lf", "utf8-crlf", "utf8-bom"), measurements, strict=True
    ):
        assert measurement.content_sha256 == hashlib.sha256(_content(case_id)).hexdigest()


@pytest.mark.parametrize(
    ("case_id", "expected_gap"),
    [
        ("utf8-invalid", "source_budget_native_text_invalid_utf8"),
        ("utf8-embedded-bom", "source_budget_native_text_embedded_bom"),
    ],
)
def test_invalid_or_ambiguous_text_fails_without_partial_metrics(
    case_id: str,
    expected_gap: str,
) -> None:
    _failure(case_id, expected_gap)


def test_python_statement_packing_cannot_reduce_native_coordinates() -> None:
    lines = _values(_success("python-lines"))
    packed = _values(_success("python-packed"))
    assert packed["lexical_tokens"] >= lines["lexical_tokens"]
    assert packed["normalized_bytes"] >= lines["normalized_bytes"]


@pytest.mark.parametrize(
    ("left_id", "right_id"),
    [
        ("python-identifier-a", "python-identifier-b"),
        ("python-literal-a", "python-literal-b"),
    ],
)
def test_python_identifier_and_literal_spelling_remain_visible(
    left_id: str,
    right_id: str,
) -> None:
    left = _success(left_id)
    right = _success(right_id)
    assert _values(left)["lexical_tokens"] == _values(right)["lexical_tokens"]
    assert left.normalized_digest != right.normalized_digest


def test_python_comment_payload_is_counted_without_changing_token_cardinality() -> None:
    short = _values(_success("python-comment-short"))
    long = _values(_success("python-comment-long"))
    assert long["lexical_tokens"] == short["lexical_tokens"]
    assert long["normalized_bytes"] > short["normalized_bytes"]


def test_python_syntax_failure_returns_one_stable_gap() -> None:
    _failure("python-invalid", "source_budget_native_parse_failed:python")


@pytest.mark.parametrize(
    ("left_id", "right_id"),
    [
        ("toml-a", "toml-b"),
        ("json-a", "json-b"),
        ("yaml-a", "yaml-b"),
        ("yaml-on-string", "yaml-on-quoted"),
        ("ini-a", "ini-b"),
        ("c4-a", "c4-b"),
    ],
)
def test_structured_formatting_and_declaration_order_do_not_change_metrics(
    left_id: str,
    right_id: str,
) -> None:
    left = _success(left_id)
    right = _success(right_id)
    assert left.normalized_digest == right.normalized_digest
    assert left.values == right.values


@pytest.mark.parametrize(
    ("case_id", "provider_id"),
    [
        ("toml-duplicate", "toml"),
        ("json-duplicate", "json"),
        ("json-nonfinite", "json"),
        ("yaml-duplicate", "yaml"),
        ("yaml-nonfinite", "yaml"),
        ("yaml-tag", "yaml"),
        ("yaml-anchor", "yaml"),
        ("ini-duplicate", "ini"),
        ("c4-malformed", "c4"),
        ("c4-unknown", "c4"),
    ],
)
def test_structured_ambiguity_or_invalid_grammar_fails_closed(
    case_id: str,
    provider_id: str,
) -> None:
    _failure(case_id, f"source_budget_native_parse_failed:{provider_id}")


def test_jinja_separates_dynamic_structure_from_static_and_comment_payload() -> None:
    base = _values(_success("jinja-base"))
    comment = _values(_success("jinja-comment"))
    dynamic = _values(_success("jinja-dynamic"))
    assert base["template_dynamic_units"] > 0
    assert base["template_static_bytes"] > 0
    assert comment["template_dynamic_units"] == base["template_dynamic_units"]
    assert comment["template_static_bytes"] > base["template_static_bytes"]
    assert dynamic["template_dynamic_units"] > base["template_dynamic_units"]
    assert dynamic["template_static_bytes"] == base["template_static_bytes"]


def test_jinja_dynamic_payload_bytes_cannot_be_laundered_by_ast_unit_count() -> None:
    short = _values(_success("jinja-dynamic-literal-short"))
    long = _values(_success("jinja-dynamic-literal-long"))
    assert short["template_dynamic_units"] == long["template_dynamic_units"]
    assert long["template_dynamic_bytes"] > short["template_dynamic_bytes"]
    assert short["template_static_bytes"] == long["template_static_bytes"] == 0


@pytest.mark.parametrize(
    "source",
    [
        "{{ 1e999 }}",
        "{{ 1e999999999999999999999999999999999999999999999999999999999999 }}",
    ],
)
def test_jinja_non_finite_literals_fail_closed(source: str) -> None:
    load = _native().measure_native(source.encode(), _contracts("template-jinja-v2"))

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_parse_failed:jinja",)


def test_malformed_jinja_returns_no_partial_vector() -> None:
    _failure("jinja-invalid", "source_budget_native_parse_failed:jinja")


@pytest.mark.parametrize("case_id", ["shell-constructs", "shell-heredoc"])
@pytest.mark.timeout(2)
def test_shell_provider_admits_governed_bash_and_zsh_lexical_constructs(
    case_id: str,
) -> None:
    values = _values(_success(case_id))
    assert values["lexical_tokens"] > 0
    assert values["normalized_bytes"] > 0


@pytest.mark.parametrize(
    "case_id",
    ["shell-unterminated-heredoc", "shell-unterminated-quote"],
)
def test_unterminated_shell_constructs_fail_closed(case_id: str) -> None:
    _failure(case_id, "source_budget_native_parse_failed:shell")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("parser_id", "unknown-parser"),
        ("parser_version", "drifted-version"),
        ("grammar_digest", "0" * 64),
        ("normalization_id", "unknown-normalization"),
        ("normalization_version", "999"),
        ("metric_id", "unknown_metric"),
        ("unit", "semantic_node"),
    ],
)
def test_dispatch_requires_the_complete_exact_provider_signature(
    field: str,
    replacement: str,
) -> None:
    contracts = list(_contracts("python-source-v2"))
    contracts[0] = contracts[0].model_copy(update={field: replacement})
    load = _measure("python-lines", tuple(contracts))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)


@pytest.mark.parametrize(
    "identity",
    [
        ("PyPy", 3, 14),
        ("CPython", 3, 13),
        ("CPython", 3, 15),
    ],
)
def test_only_cpython_314_is_an_admitted_measurement_runtime(
    monkeypatch: pytest.MonkeyPatch,
    identity: tuple[str, int, int],
) -> None:
    module = _native()
    monkeypatch.setattr(module, "_runtime_identity", lambda: identity)
    load = _measure("python-lines")
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_runtime_unsupported",)


def test_provider_dependencies_are_major_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _native()
    monkeypatch.setattr(module, "_dependency_majors", lambda: {"jinja2": 4, "pyyaml": 6})
    load = _measure("jinja-base")
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_dependency_major_mismatch:jinja2",)


def test_provider_conformance_fingerprint_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()

    def drift(provider_id: str) -> str:
        return "0" * 64 if provider_id == "python" else REVIEWED_CONFORMANCE_DIGESTS[provider_id]

    monkeypatch.setattr(module, "_conformance_output_digest", drift)
    load = _measure("python-lines")
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_conformance_mismatch:python",)


def test_mixed_startup_gaps_remain_stably_sorted_through_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    gaps = {
        "c4": "source_budget_native_provider_unavailable:c4",
        "python": "source_budget_native_conformance_mismatch:python",
    }
    monkeypatch.setattr(module, "_conformance_gap", gaps.get)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == (
        "source_budget_native_conformance_mismatch:python",
        "source_budget_native_provider_unavailable:c4",
    )


def test_registry_contracts_are_complete_deterministic_and_publicly_dispatchable() -> None:
    samples = {
        "configparser": b"[service]\nname=ethos\n",
        "diagram-contract": b'system ETHOS "Governance"\n',
        "jinja2": b"{{ value | upper }}\n",
        "json-stdlib": b'{"name":"ethos"}\n',
        "python-tokenize": b"name = 'ethos'\n",
        "pyyaml-safe": b"name: ethos\n",
        "shell-lexical": b"printf '%s\\n' ethos\n",
        "tomllib": b"name='ethos'\n",
        "utf8-control": b"ethos\r\n",
        "utf8-footprint": b"ethos\r\n",
    }
    profiles: dict[str, list[MetricContract]] = {}
    for contract in _registry().contracts:
        profiles.setdefault(contract.metric_profile, []).append(contract)
        assert len(contract.grammar_digest) == 64
        assert contract.grammar_digest != "0" * 64
        assert contract.parser_version not in {
            "stdlib-3.14",
            "posix-v1",
            "3.x-contract",
            "6.x-contract",
        }
    for contracts in profiles.values():
        ordered = tuple(sorted(contracts, key=lambda item: (item.metric_id, item.unit)))
        content = samples[ordered[0].parser_id]
        first = _native().measure_native(content, ordered)
        second = _native().measure_native(content, ordered)
        assert first.required_gaps == second.required_gaps == ()
        assert first.measurement == second.measurement


def test_native_owner_is_the_only_new_public_measurement_api() -> None:
    module = _native()
    public = {name for name in vars(module) if not name.startswith("_")}
    assert "measure_native" in public
    assert "measure_carrier" not in public
    assert "measure_snapshot" not in public
    assert NATIVE_MODULE in sys.modules


@pytest.mark.parametrize(
    ("content", "contracts"),
    [
        (bytearray(b"pass\n"), _contracts("python-source-v2")),
        (b"pass\n", ()),
        (b"pass\n", [_contracts("python-source-v2")[0]]),
        (b"pass\n", (object(),)),
    ],
)
def test_native_rejects_non_exact_content_and_contract_containers(
    content: object,
    contracts: object,
) -> None:
    load = _native().measure_native(content, contracts)
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_contract_invalid",)


def test_native_rejects_incomplete_provider_coordinate_vector() -> None:
    load = _native().measure_native(
        _content("python-lines"),
        (_contracts("python-source-v2")[0],),
    )
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)


def test_native_canonicalizes_internal_value_failures_without_partial_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    assert _success("python-lines").values
    monkeypatch.setattr(module, "_measure_provider", lambda _provider, _text: (b"stream", {}))
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_contract_invalid",)


@pytest.mark.parametrize("stage", ["normalize", "provider"])
def test_native_maps_memory_exhaustion_to_stable_gap(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    module = _native()
    assert _success("python-lines").values

    def exhausted(*_args: object) -> None:
        message = "SENSITIVE"
        raise MemoryError(message)

    monkeypatch.setattr(
        module,
        "_normalize_text" if stage == "normalize" else "_measure_provider",
        exhausted,
    )
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_resource_exhausted",)


def test_provider_boundary_maps_memory_exhaustion_without_leaking_detail() -> None:
    module = _native()
    provider_boundary = vars(module)["_ProviderBoundary"]
    message = "SENSITIVE"

    with (
        pytest.raises(ValueError, match="source_budget_native_resource_exhausted"),
        provider_boundary("unused"),
    ):
        raise MemoryError(message)


def test_native_admission_maps_memory_exhaustion_to_stable_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()

    def exhausted(_contract: MetricContract) -> None:
        message = "SENSITIVE"
        raise MemoryError(message)

    monkeypatch.setattr(module, "_provider_id_for_contract", exhausted)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_resource_exhausted",)


def test_native_startup_maps_memory_exhaustion_to_stable_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()

    def exhausted() -> dict[str, int]:
        message = "SENSITIVE-STARTUP"
        raise MemoryError(message)

    monkeypatch.setattr(module, "_runtime_identity", lambda: ("CPython", 3, 14))
    monkeypatch.setattr(module, "_dependency_majors", exhausted)
    startup_conformance = vars(module)["_startup_conformance"]
    startup_conformance.cache_clear()
    try:
        load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    finally:
        startup_conformance.cache_clear()

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_resource_exhausted",)


def test_python_tokenizer_error_becomes_public_parse_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    assert _success("python-lines").values
    token = module.tokenize.TokenInfo(module.tokenize.ERRORTOKEN, "?", (1, 0), (1, 1), "?\n")
    monkeypatch.setattr(module.tokenize, "generate_tokens", lambda _readline: iter((token,)))
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_parse_failed:python",)


def test_jinja_canonicalizer_rejects_unknown_ast_leaves_through_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    assert _success("jinja-base").values

    class FakeNode:
        fields = ("leaf",)
        leaf = object()

        def find_all(self, _node_type: type[object]) -> tuple[object, ...]:
            return ()

    class FakeEnvironment:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def parse(self, _text: str) -> FakeNode:
            return FakeNode()

        def lex(self, _text: str) -> tuple[object, ...]:
            return ()

    fake = SimpleNamespace(
        Environment=FakeEnvironment,
        nodes=SimpleNamespace(Node=FakeNode, TemplateData=type("TemplateData", (), {})),
    )
    monkeypatch.setattr(module, "_provider_module", lambda *_args: fake)
    load = module.measure_native(_content("jinja-base"), _contracts("template-jinja-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_parse_failed:jinja",)


def test_additional_shell_forms_are_measured_and_invalid_states_fail_closed() -> None:
    values = _values(_success("shell-extra-forms"))
    assert values["lexical_tokens"] > 0
    for case_id in (
        "shell-dangling-escape",
        "shell-substitution-comment-eof",
        "shell-substitution-heredoc-missing-delimiter",
        "shell-substitution-case-unterminated",
        "shell-unterminated-substitution",
        "shell-heredoc-no-body",
        "shell-case-subject-missing",
        "shell-case-subject-multiple",
        "shell-case-subject-fragment",
        "shell-case-empty-pattern",
        "shell-case-subject-newline",
        "shell-case-after-if-unterminated",
        "shell-case-after-time-unterminated",
        "shell-unmatched-standalone-brace",
        "shell-array-shift-in-argument",
        "shell-case-pattern-multiple-words",
        "shell-case-pattern-newline",
        "shell-case-alternative-newline",
        "shell-case-closure-extra-word",
        "shell-case-closure-redirection-extra-word",
        "shell-case-closure-trailing-separator",
    ):
        _failure(case_id, "source_budget_native_parse_failed:shell")


def test_shell_accepts_case_patterns_literal_dollar_and_repository_corpus() -> None:
    for case_id in (
        "shell-literal-dollar",
        "shell-case-patterns",
        "shell-regex-anchor",
        "shell-substitution-comment",
    ):
        assert _success(case_id).values
    for relative in (
        ".githooks/pre-push",
        ".githooks/reference-transaction",
        "tools/ci/scripts/download-file.sh",
        "tools/ci/scripts/install-gitleaks.sh",
        "tools/ci/scripts/install-lychee.sh",
        "tools/ci/scripts/install-node.sh",
        "tools/ci/scripts/install-taplo.sh",
        "tools/ci/scripts/require-stable-head.sh",
        "tools/ci/scripts/run-actionlint.sh",
        "tools/ci/scripts/run-config-lint.sh",
        "tools/ci/scripts/run-python-tests.sh",
    ):
        load = _native().measure_native(
            (ROOT / relative).read_bytes(), _contracts("shell-source-v2")
        )
        assert load.required_gaps == ()
        assert load.measurement is not None


def test_structured_additional_boundaries_are_stable() -> None:
    assert _success("ini-default").values
    assert _success("c4-comment-escape").values
    _failure("yaml-unhashable-key", "source_budget_native_parse_failed:yaml")
    for case_id in (
        "c4-wrong-quote",
        "c4-inline-quote",
        "c4-backslash-end",
        "c4-empty",
    ):
        _failure(case_id, "source_budget_native_parse_failed:c4")


def test_structured_temporal_and_unknown_scalars_are_handled_through_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _native()
    temporal = b"date=2026-07-19\ndatetime=2026-07-19T01:02:03Z\ntime=01:02:03\nfloat=1.5\n"
    load = core.measure_native(temporal, _contracts("toml-source-v2"))
    assert load.required_gaps == ()
    assert load.measurement is not None

    monkeypatch.setattr(tomllib, "loads", lambda _text: object())
    load = core.measure_native(_content("toml-a"), _contracts("toml-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_parse_failed:toml",)


def test_forged_exact_metric_contract_fails_closed_before_dispatch() -> None:
    forged = MetricContract.model_construct()
    load = _native().measure_native(_content("python-lines"), (forged,))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_contract_invalid",)


def test_native_core_import_does_not_eagerly_load_provider_modules() -> None:
    script = f"""
import builtins
real_import = builtins.__import__
blocked = {{
    'jinja2',
    'yaml',
    'ethos.adapters.repo.source_budget.measurement.native._structured',
}}
def guarded(name, *args, **kwargs):
    if name in blocked:
        raise ModuleNotFoundError(name=name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import {NATIVE_MODULE} as module
assert not hasattr(module, '__all__')
assert callable(module.measure_native)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_reviewed_conformance_digests_are_a_complete_literal_map() -> None:
    module = _native()
    source = Path(module.__file__).read_text(encoding="utf-8")
    assignment = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_EXPECTED_CONFORMANCE_DIGESTS"
            for target in node.targets
        )
    )
    assert ast.literal_eval(assignment.value) == REVIEWED_CONFORMANCE_DIGESTS


def test_startup_primitive_exception_becomes_stable_conformance_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()

    def explode(provider_id: str) -> str:
        if provider_id == "python":
            raise RuntimeError(provider_id)
        return REVIEWED_CONFORMANCE_DIGESTS[provider_id]

    monkeypatch.setattr(module, "_conformance_output_digest", explode)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_conformance_mismatch:python",)


def test_missing_dependency_becomes_stable_provider_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    real_import = module.importlib.import_module

    def unavailable(name: str):
        if name == "jinja2":
            raise ModuleNotFoundError(name=name)
        return real_import(name)

    monkeypatch.setattr(module.importlib, "import_module", unavailable)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_unavailable:jinja",)


def test_provider_loading_and_version_read_fail_with_stable_gaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    real_import = module.importlib.import_module

    class BrokenVersion:
        @property
        def __version__(self) -> str:
            raise RuntimeError(type(self).__name__)

    def broken(name: str):
        return BrokenVersion() if name == "jinja2" else real_import(name)

    monkeypatch.setattr(module.importlib, "import_module", broken)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_unavailable:jinja",)


def test_conformance_provider_unavailability_is_preserved_through_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    real_import = module.importlib.import_module

    def unavailable(name: str):
        if name.endswith("._structured"):
            raise ModuleNotFoundError(name=name)
        return real_import(name)

    monkeypatch.setattr(module.importlib, "import_module", unavailable)
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == tuple(
        f"source_budget_native_provider_unavailable:{provider_id}"
        for provider_id in ("c4", "ini", "json", "toml", "yaml")
    )


def test_conformance_parse_failure_becomes_provider_mismatch_through_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    monkeypatch.setattr(tomllib, "loads", lambda _text: object())
    load = module.measure_native(_content("python-lines"), _contracts("python-source-v2"))
    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_conformance_mismatch:toml",)


def test_jinja_trailing_newline_is_payload_while_crlf_normalizes_to_lf() -> None:
    without = _success("jinja-no-trailing-newline")
    newline = _success("jinja-trailing-newline")
    crlf = _success("jinja-trailing-crlf")
    assert _values(newline)["template_static_bytes"] == (
        _values(without)["template_static_bytes"] + 1
    )
    assert newline.normalized_digest != without.normalized_digest
    assert newline.normalized_digest == crlf.normalized_digest
    assert newline.values == crlf.values


def test_native_module_avoids_export_barrels() -> None:
    module = _native()

    assert not hasattr(module, "__all__")
    assert callable(module.measure_native)
