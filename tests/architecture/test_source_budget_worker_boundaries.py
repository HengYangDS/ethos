from __future__ import annotations

import ast
import importlib
import inspect
import subprocess
import sys
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import replay_worker_result
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any

    from ethos_core.contracts.source_budget.metrics import MetricContract

ROOT = Path(__file__).resolve().parents[2]
MEASUREMENT_ROOT = ROOT / "packages/ethos/src/ethos/adapters/repo/source_budget/measurement"
CASES_PATH = ROOT / "tests/fixtures/source-budget-v2/cases.toml"
ROUTER_MODULE = "ethos.adapters.repo.source_budget.measurement.router"
IDENTITY_MODULE = "ethos.adapters.repo.source_budget.measurement.native.identity"
BOUNDED_MODULE = "ethos.adapters.repo.source_budget.measurement.native.bounded.core"
ISOLATED_MODULE = "ethos.adapters.repo.source_budget.measurement.native.isolated.core"
SUPERVISOR_MODULE = "ethos.adapters.repo.source_budget.measurement.worker.supervisor.core"
BOUNDED_PARSERS = frozenset({"utf8-footprint", "utf8-control", "diagram-contract"})
ISOLATED_PARSERS = frozenset(
    {
        "python-tokenize",
        "json-stdlib",
        "tomllib",
        "pyyaml-safe",
        "configparser",
        "jinja2",
        "shell-lexical",
    }
)
PARENT_GAPS = (
    "source_budget_worker_unavailable",
    "source_budget_worker_isolation_unsupported",
    "source_budget_worker_timeout",
    "source_budget_worker_resource_exhausted",
    "source_budget_worker_output_exceeded",
    "source_budget_worker_protocol_invalid",
    "source_budget_worker_failed",
)
SAMPLE_CONTENT = {
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
GOLDENS = {
    "utf8-footprint": {
        "case": "utf8-lf",
        "values": (("normalized_bytes", "normalized_byte", 11),),
        "content": "e49c81e2d2f84e259d40e2fb8192f3bcd198b355184845d76d8f58807d0d78ee",
        "normalized": "e49c81e2d2f84e259d40e2fb8192f3bcd198b355184845d76d8f58807d0d78ee",
        "measurement": "eda27b04ce436ac6acc15775570409b94a0a1772cf0ff1c29da391aef6c146e9",
    },
    "utf8-control": {
        "profile": "control-source-v2",
        "content_bytes": b"alpha\r\nbeta\r",
        "values": (("normalized_bytes", "normalized_byte", 11),),
        "content": "9f582519fb21e19307c20b3c7734a71fc7631d4ae779b8c219e361eb8c40271c",
        "normalized": "e49c81e2d2f84e259d40e2fb8192f3bcd198b355184845d76d8f58807d0d78ee",
        "measurement": "e536545ac53a6a1d8e5cc81a5b5f0dd82f1eadd420ea5b5ae676cd58a4e179e7",
    },
    "diagram-contract": {
        "case": "c4-a",
        "values": (
            ("normalized_scalar_bytes", "normalized_scalar_byte", 227),
            ("semantic_nodes", "semantic_node", 24),
        ),
        "content": "825a141f80065cbb662fcb4d85948269606613fb508cf6ae283630603d13db92",
        "normalized": "68646c68805640a08f008a02fda66f6a16048a8539137df8de1f1dcda7538030",
        "measurement": "990fc858a5f5a4b381d9de58006363b5528b6279f642603d493d0abda19f03a6",
    },
    "python-tokenize": {
        "case": "python-lines",
        "values": (
            ("lexical_tokens", "lexical_token", 6),
            ("normalized_bytes", "normalized_byte", 57),
        ),
        "content": "e3ae9422aeb2f4b2edcfb2bc949a2059363b7d8b83dbdaa8657b446b252f2e6e",
        "normalized": "2f7c811a8ced6215aef9e9ccf74b4a9db2a5ad4aca37d2cd43f3d953c3520fbf",
        "measurement": "a54d39266858261f52a18758c385de45e4f846eeae452bb446ff3f1499c0dc0c",
    },
    "json-stdlib": {
        "case": "json-a",
        "values": (
            ("normalized_scalar_bytes", "normalized_scalar_byte", 57),
            ("semantic_nodes", "semantic_node", 8),
        ),
        "content": "57476314076760edfbdb6e70a6a7be1c2fdbdf8ba3df783cfc7427363dc0d340",
        "normalized": "0ae769707d5173c043ccf6a150375bf5cdbe6106ae63ccb45b9a5bfa5b9f2817",
        "measurement": "c84fc42e4a6e7ae1d834f8977b355cd28d3385eed829029d74ea5e21da4e3c89",
    },
    "tomllib": {
        "case": "toml-a",
        "values": (
            ("normalized_scalar_bytes", "normalized_scalar_byte", 74),
            ("semantic_nodes", "semantic_node", 9),
        ),
        "content": "74fa59208bffb1faac7d56341d4305b742f3bef38717e9e547b397f4a05da14a",
        "normalized": "24016eeaa15d2ff09fd8bf429aa70bc1a7c2fb35490b5632f1a017cce082fe2b",
        "measurement": "0aa40c1e48735b5d0bd5e52b162b91c8016bc0c668a736f33f0280dc9fa0ff4f",
    },
    "pyyaml-safe": {
        "case": "yaml-a",
        "values": (
            ("normalized_scalar_bytes", "normalized_scalar_byte", 57),
            ("semantic_nodes", "semantic_node", 8),
        ),
        "content": "73a6521b748a5d015a5333c5dadecb02d7d2acf58566c7160a6e924ce1f8eeab",
        "normalized": "0ae769707d5173c043ccf6a150375bf5cdbe6106ae63ccb45b9a5bfa5b9f2817",
        "measurement": "9ffd0cb233e417d789fc73099055aebda8a0b45b4e3b976fa17ca954ac371b3c",
    },
    "configparser": {
        "case": "ini-a",
        "values": (
            ("normalized_scalar_bytes", "normalized_scalar_byte", 52),
            ("semantic_nodes", "semantic_node", 7),
        ),
        "content": "20fef3b2efae00b4c7d4930f881f9c854f186fa9eec3746bcbb29a1ddc260566",
        "normalized": "5ad308dcd4f1eb2a2d55484c338d78300eee2e78fc9302996ef2a501a73ca82c",
        "measurement": "ecd77ede7424cd43fedbbb118053543a71759988ffeefafd6050ff4488ea8071",
    },
    "jinja2": {
        "case": "jinja-base",
        "values": (
            ("template_dynamic_bytes", "template_dynamic_byte", 205),
            ("template_dynamic_units", "template_dynamic_unit", 2),
            ("template_static_bytes", "template_static_byte", 14),
        ),
        "content": "2b3d52f80cab10326254625165dc5599970195fefac2c3512b579cd1838a98b4",
        "normalized": "51518f6cef009c32b428e294a18b6b7d2bfc61aec048c571927e9a7e6d725998",
        "measurement": "e32e6ea21ce95593cfdac60dfaa54e27e110ee420226532352d14bf7a7bb4de0",
    },
    "shell-lexical": {
        "case": "shell-constructs",
        "values": (
            ("lexical_tokens", "lexical_token", 24),
            ("normalized_bytes", "normalized_byte", 385),
        ),
        "content": "c22ada25c9f5771f30b01b9aed1f45d0c85b93a6d3157dc9716dbe163c1e61a7",
        "normalized": "be22931d87301628f46451028539bb2c19970a4f10cf9de832b4e3d2e3b73ce6",
        "measurement": "cd974b480b0ee54713ec3b7bf18fd8a3f6deb7a233e5e02e3c854b3fb229cd44",
    },
}


@lru_cache(maxsize=1)
def _registry():
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict[str, Any]]:
    payload = tomllib.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in payload["case"]}


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    contracts = tuple(item for item in _registry().contracts if item.metric_profile == profile)
    assert contracts
    return tuple(sorted(contracts, key=lambda item: (item.metric_id, item.unit, item.contract_id)))


def _case(case_id: str) -> tuple[bytes, tuple[MetricContract, ...]]:
    row = _cases()[case_id]
    content = str(row["text"]).encode("utf-8") if "text" in row else bytes.fromhex(str(row["hex"]))
    return content, _contracts(str(row["profile"]))


def _module(name: str) -> ModuleType:
    return importlib.import_module(name)


def _child_load(
    content: bytes,
    contracts: tuple[MetricContract, ...],
) -> NativeMeasurementLoad:
    identity = _module(IDENTITY_MODULE).resolve_native_provider(contracts)
    request = WorkerRequest.create(
        content=content,
        contracts=identity.contracts,
        provider_descriptor=identity.provider_descriptor,
        execution_descriptor=identity.execution_descriptor,
    )
    result = _module(ISOLATED_MODULE).measure_isolated(request, content)
    assert type(result) is WorkerResult
    if result.gap is not None:
        return NativeMeasurementLoad(None, (result.gap,))
    return NativeMeasurementLoad(replay_worker_result(request, result), ())


def _route_contracts(parser_id: str) -> tuple[MetricContract, ...]:
    profile = next(
        item.metric_profile for item in _registry().contracts if item.parser_id == parser_id
    )
    return _contracts(profile)


@pytest.mark.parametrize("parser_id", sorted(BOUNDED_PARSERS))
def test_bounded_parser_ids_route_once_only_to_bounded_engine(
    monkeypatch: pytest.MonkeyPatch,
    parser_id: str,
) -> None:
    router = _module(ROUTER_MODULE)
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object) -> NativeMeasurementLoad:
        calls["bounded"] += 1
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    def supervisor(*_args: object) -> NativeMeasurementLoad:
        calls["supervisor"] += 1
        return NativeMeasurementLoad(None, ("source_budget_worker_unavailable",))

    monkeypatch.setattr(router, "measure_bounded", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    load = router.measure_native(SAMPLE_CONTENT[parser_id], _route_contracts(parser_id))

    assert load.required_gaps == ("source_budget_native_runtime_unsupported",)
    assert calls == {"bounded": 1, "supervisor": 0}


@pytest.mark.parametrize("parser_id", sorted(ISOLATED_PARSERS))
def test_isolated_parser_ids_route_once_only_to_supervisor(
    monkeypatch: pytest.MonkeyPatch,
    parser_id: str,
) -> None:
    router = _module(ROUTER_MODULE)
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object) -> NativeMeasurementLoad:
        calls["bounded"] += 1
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    def supervisor(request: WorkerRequest, content: bytes) -> NativeMeasurementLoad:
        assert type(request) is WorkerRequest
        assert content == SAMPLE_CONTENT[parser_id]
        calls["supervisor"] += 1
        return NativeMeasurementLoad(None, ("source_budget_worker_unavailable",))

    monkeypatch.setattr(router, "measure_bounded", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    load = router.measure_native(SAMPLE_CONTENT[parser_id], _route_contracts(parser_id))

    assert load.required_gaps == ("source_budget_worker_unavailable",)
    assert calls == {"bounded": 0, "supervisor": 1}


def test_parser_identity_alone_fixes_execution_mode_across_profiles_and_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = _module(ROUTER_MODULE)
    signature = inspect.signature(router.measure_native)
    assert tuple(signature.parameters) == ("content", "contracts")
    observed: list[tuple[str, str]] = []

    def bounded(_content: bytes, contracts: tuple[MetricContract, ...]) -> NativeMeasurementLoad:
        observed.append((contracts[0].parser_id, "bounded"))
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    def supervisor(request: WorkerRequest, _content: bytes) -> NativeMeasurementLoad:
        observed.append((request.contracts[0].parser_id, "isolated"))
        return NativeMeasurementLoad(None, ("source_budget_worker_unavailable",))

    monkeypatch.setattr(router, "measure_bounded", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    for profile in sorted({item.metric_profile for item in _registry().contracts}):
        contracts = _contracts(profile)
        router.measure_native(SAMPLE_CONTENT[contracts[0].parser_id], contracts)

    expected = {
        (item.parser_id, "bounded" if item.parser_id in BOUNDED_PARSERS else "isolated")
        for item in _registry().contracts
    }
    assert set(observed) == expected


def test_mixed_or_forged_execution_tuple_fails_before_any_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = _module(ROUTER_MODULE)
    original = _contracts("python-source-v2")
    bounded = _contracts("control-source-v2")[0]
    replacement = {
        "execution_mode": bounded.execution_mode,
        "max_carrier_bytes": bounded.max_carrier_bytes,
        "execution_contract_id": bounded.execution_contract_id,
        "execution_contract_digest": bounded.execution_contract_digest,
    }
    forged = tuple(item.model_copy(update=replacement) for item in original)
    mixed = (original[0].model_copy(update=replacement), *original[1:])
    calls = 0

    def engine(*_args: object) -> NativeMeasurementLoad:
        nonlocal calls
        calls += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    monkeypatch.setattr(router, "measure_bounded", engine)
    monkeypatch.setattr(router, "run_isolated_worker", engine)
    for contracts in (forged, mixed):
        load = router.measure_native(b"value = 1\n", contracts)
        assert load.measurement is None
        assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)
    assert calls == 0


def test_parent_imports_do_not_load_isolated_or_complex_provider_modules() -> None:
    script = f"""
import sys
import {ROUTER_MODULE}
import ethos.adapters.repo.source_budget.measurement.core
forbidden = (
    {ISOLATED_MODULE!r},
    'ethos.adapters.repo.source_budget.measurement.native.isolated.structured',
    'ethos.adapters.repo.source_budget.measurement.native.shell',
    'jinja2',
    'yaml',
)
loaded = sorted(name for name in sys.modules if any(name == item or name.startswith(item + '.') for item in forbidden))
assert loaded == [], loaded
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_c4_bounded_execution_cannot_load_complex_provider_engines() -> None:
    script = f"""
import builtins
import importlib
import sys
from pathlib import Path
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
contracts = load_metric_contracts(Path('.')).contracts
assert contracts is not None
resolved = tuple(sorted(
    (item for item in contracts.contracts if item.metric_profile == 'diagram-source-v2'),
    key=lambda item: (item.metric_id, item.unit, item.contract_id),
))
blocked = (
    'configparser',
    'tomllib',
    'yaml',
    'jinja2',
    'ethos.adapters.repo.source_budget.measurement.native.isolated',
    'ethos.adapters.repo.source_budget.measurement.native.shell',
)
for name in tuple(sys.modules):
    if any(name == item or name.startswith(item + '.') for item in blocked):
        del sys.modules[name]
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if any(name == item or name.startswith(item + '.') for item in blocked):
        raise AssertionError('blocked complex import:' + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
module = importlib.import_module({BOUNDED_MODULE!r})
load = module.measure_bounded(b'system ETHOS "Governance"\\n', resolved)
assert load.measurement is not None, load.required_gaps
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_parent_source_graph_has_no_isolated_engine_edge_or_compatibility_shell() -> None:
    paths = (
        MEASUREMENT_ROOT / "core.py",
        MEASUREMENT_ROOT / "router.py",
        MEASUREMENT_ROOT / "worker/supervisor/core.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        imported.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert not any("measurement.native.isolated" in name for name in imported)
        assert not any("measurement.native.shell" in name for name in imported)
        assert not any("measurement.native.isolated" in value for value in strings)
        assert "measure_isolated" not in source
    orchestration = (MEASUREMENT_ROOT / "core.py").read_text(encoding="utf-8")
    assert "from ethos.adapters.repo.source_budget.measurement.router import measure_native" in (
        orchestration
    )
    assert not (MEASUREMENT_ROOT / "native/core.py").exists()
    assert not (MEASUREMENT_ROOT / "native/_structured.py").exists()


@pytest.mark.parametrize("gap", PARENT_GAPS)
def test_every_supervisor_gap_returns_without_bounded_fallback(
    monkeypatch: pytest.MonkeyPatch,
    gap: str,
) -> None:
    router = _module(ROUTER_MODULE)
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object) -> NativeMeasurementLoad:
        calls["bounded"] += 1
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    def supervisor(*_args: object) -> NativeMeasurementLoad:
        calls["supervisor"] += 1
        return NativeMeasurementLoad(None, (gap,))

    monkeypatch.setattr(router, "measure_bounded", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    load = router.measure_native(b"value = 1\n", _contracts("python-source-v2"))

    assert load.measurement is None
    assert load.required_gaps == (gap,)
    assert calls == {"bounded": 0, "supervisor": 1}


def test_wrong_or_forged_supervisor_success_fails_closed_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = _module(ROUTER_MODULE)
    contracts = _contracts("python-source-v2")
    other = _child_load(b"value = 2\n", contracts)
    assert other.measurement is not None
    bounded_calls = 0

    def bounded(*_args: object) -> NativeMeasurementLoad:
        nonlocal bounded_calls
        bounded_calls += 1
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    monkeypatch.setattr(router, "measure_bounded", bounded)
    for result in (object(), other):
        monkeypatch.setattr(router, "run_isolated_worker", lambda *_args, value=result: value)
        load = router.measure_native(b"value = 1\n", contracts)
        assert load.measurement is None
        assert load.required_gaps == ("source_budget_worker_protocol_invalid",)
    assert bounded_calls == 0


def test_bounded_engine_rejects_direct_isolated_contracts() -> None:
    load = _module(BOUNDED_MODULE).measure_bounded(
        b"value = 1\n",
        _contracts("python-source-v2"),
    )

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_execution_contract_invalid",)


@pytest.mark.parametrize("parser_id", sorted(GOLDENS))
def test_all_provider_values_and_digests_match_reviewed_goldens(parser_id: str) -> None:
    golden = GOLDENS[parser_id]
    if "case" in golden:
        content, contracts = _case(str(golden["case"]))
    else:
        content = golden["content_bytes"]
        contracts = _contracts(str(golden["profile"]))
    if parser_id in BOUNDED_PARSERS:
        load = _module(BOUNDED_MODULE).measure_bounded(content, contracts)
    else:
        load = _child_load(content, contracts)

    assert load.required_gaps == ()
    assert load.measurement is not None
    measurement = load.measurement
    assert (
        tuple((value.metric_id, value.unit, value.value) for value in measurement.values)
        == golden["values"]
    )
    assert measurement.content_sha256 == golden["content"]
    assert measurement.normalized_digest == golden["normalized"]
    assert measurement.measurement_digest == golden["measurement"]
