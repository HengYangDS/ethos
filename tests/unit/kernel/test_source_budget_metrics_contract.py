from __future__ import annotations

import hashlib
import importlib
import json
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as c
import ethos_core.contracts.source_budget.metrics as m

if TYPE_CHECKING:
    from collections.abc import Callable

_D: dict[str, Any] = json.loads(
    (Path(__file__).parents[2] / "fixtures/source-budget-v2/compression-cases.json").read_text()
)["metrics"]


def _p(**changes: object) -> m.MetricProfile:
    return m.MetricProfile.model_validate(_D["base_profile"] | changes)


def _c(metric_id: str, unit: str, **changes: object) -> m.MetricContract:
    payload = _D["base_contract"] | {"metric_id": metric_id, "unit": unit} | changes
    payload.setdefault("contract_id", f"{payload['metric_profile']}:{metric_id}")
    return m.MetricContract.model_validate(payload)


def _s(profiles: object = None, contracts: object = None) -> m.MetricContractSet:
    default = (_c("lexical_tokens", "lexical_token"), _c("normalized_bytes", "normalized_byte"))
    return m.MetricContractSet(
        schema="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=profiles or (_p(),),
        contracts=contracts or default,
    )


def _raises(error: type[Exception], match: str | None, call: Callable[[], object]) -> None:
    with pytest.raises(error, match=match):
        call()


def _invalid(case: dict[str, Any]) -> m.MetricContractSet:
    profiles = tuple(_p(**item) for item in case["profiles"])
    contracts = tuple(
        _c(
            item["metric_id"],
            item["unit"],
            **{key: value for key, value in item.items() if key not in {"metric_id", "unit"}},
        )
        for item in case["contracts"]
    )
    return _s(profiles, contracts)


def test_metric_validation_matrix() -> None:
    contract = _c("lexical_tokens", "lexical_token")
    _raises(ValidationError, "frozen", lambda: setattr(contract, "metric_id", "mutable"))
    _raises(
        ValidationError,
        "tokenizer",
        lambda: m.MetricContract.model_validate(contract.model_dump() | {"tokenizer": "x"}),
    )
    for field, value in _D["invalid_fields"]:
        payload = contract.model_dump() | {field: value}
        _raises(
            ValidationError, None, lambda payload=payload: m.MetricContract.model_validate(payload)
        )
    for case in _D["invalid_sets"]:
        _raises(ValidationError, case["message"], lambda case=case: _invalid(case))
    payload = _s().model_dump(mode="json", by_alias=True)
    payload["schema_id"] = payload.pop("schema")
    _raises(ValidationError, "schema", lambda: m.MetricContractSet.model_validate(payload))
    values = {"none": None, "contracts": _s(), "object": object()}
    for value_kind, gap_kind, gaps, message in _D["load_envelopes"]:
        required = list(gaps) if gap_kind == "list" else tuple(gaps)
        _raises(
            ValueError,
            message,
            lambda value=values[value_kind], required=required: m.MetricContractSetLoad(
                value, required
            ),
        )
    payload = _s().model_dump(mode="json", by_alias=True) | {"contract_version": 4}
    _raises(
        ValidationError, "contract version", lambda: m.MetricContractSet.model_validate(payload)
    )


def test_metric_behavior_matrix() -> None:
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    sets = tuple(
        _s((_p(required_metric_ids=order),))
        for order in (
            ("normalized_bytes", "lexical_tokens"),
            ("lexical_tokens", "normalized_bytes"),
        )
    )
    assert m.metric_contracts_digest(sets[0]) == m.metric_contracts_digest(sets[1])
    expected = ("lexical_tokens", "normalized_bytes")
    for contracts in sets:
        assert (
            tuple(item.metric_id for item in m.resolve_metric_contracts(identity, contracts))
            == expected
        )
    presets = _D["carrier_presets"]
    excluded = c.CarrierIdentity.model_validate(_D["base_carrier"] | presets["excluded"])
    unresolved = c.CarrierIdentity.model_validate(_D["base_carrier"] | presets["unresolved"])
    assert m.resolve_metric_contracts(excluded, _s()) == ()
    _raises(ValueError, "profile unresolved", lambda: m.resolve_metric_contracts(unresolved, _s()))
    lexical, normalized = (
        _c("lexical_tokens", "lexical_token"),
        _c("normalized_bytes", "normalized_byte"),
    )
    digest = m.metric_contracts_digest(_s(contracts=(lexical, normalized)))
    assert digest == m.metric_contracts_digest(_s(contracts=(normalized, lexical)))
    changed = lexical.model_copy(update={"parser_version": "stdlib-3.15"})
    assert digest != m.metric_contracts_digest(_s(contracts=(changed, normalized)))
    schema = m.metric_contracts_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Metric Contracts"
    expected_schema = json.dumps(schema, separators=(",", ":")) + "\n"
    assert (
        Path("system/schemas/kernel/source-budget-metrics.schema.json").read_text()
        == expected_schema
    )


def _constructed_contract(metric_id: str, unit: str, **changes: object) -> m.MetricContract:
    payload = _D["base_contract"] | {"metric_id": metric_id, "unit": unit} | changes
    payload.setdefault("contract_id", f"{payload['metric_profile']}:{metric_id}")
    contract = m.MetricContract.model_construct(
        **{key: value for key, value in payload.items() if key in m.MetricContract.model_fields}
    )
    for field in ("execution_mode", "max_carrier_bytes"):
        object.__setattr__(contract, field, payload[field])
    return contract


def _forged_contracts(method: str, field: str, value: object) -> tuple[m.MetricContract, ...]:
    contracts = _s().contracts
    if method == "model_copy":
        return tuple(item.model_copy(update={field: value}) for item in contracts)
    return tuple(
        m.MetricContract.model_construct(**(item.model_dump() | {field: value}))
        for item in contracts
    )


def test_metric_registry_rejects_forged_float_version_at_trust_boundaries() -> None:
    registry = _s()
    _raises(
        ValueError,
        "contract version",
        lambda: m.MetricContractSet.model_construct(
            schema_id=registry.schema_id,
            contract_version=3.0,
            profiles=registry.profiles,
            contracts=registry.contracts,
        ),
    )
    forged = registry.model_copy(update={"contract_version": 3.0})
    _raises(ValueError, "contract version", lambda: m.MetricContractSetLoad(forged, ()))
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    _raises(ValueError, "contract version", lambda: m.resolve_metric_contracts(identity, forged))


def test_metric_resource_boundaries_replay_homogeneous_forged_atoms() -> None:
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    invalid = (
        ("contract_version", 3.0),
        ("execution_mode", "subprocess"),
        ("max_carrier_bytes", True),
        ("max_carrier_bytes", 1.5),
        ("max_carrier_bytes", 0),
        ("max_carrier_bytes", -1),
    )
    for field, value in invalid:
        for method in ("model_construct", "model_copy"):
            atoms = _forged_contracts(method, field, value)
            registry = _s().model_copy(update={"contracts": atoms})
            _raises(
                ValueError,
                "metric contract",
                lambda atoms=atoms: m.metric_provider_resource_contract(atoms),
            )
            _raises(
                ValueError,
                "metric contract",
                lambda registry=registry: m.MetricContractSetLoad(registry, ()),
            )
            _raises(
                ValueError,
                "metric contract",
                lambda registry=registry: m.resolve_metric_contracts(identity, registry),
            )


def test_metric_contract_v3_resource_boundary_is_required_and_strict() -> None:
    contract = _c("lexical_tokens", "lexical_token")
    assert contract.execution_mode == "bounded_in_process_v1"
    assert contract.max_carrier_bytes == 65536
    for field in ("execution_mode", "max_carrier_bytes"):
        payload = contract.model_dump()
        payload.pop(field)
        _raises(
            ValidationError,
            field,
            lambda payload=payload: m.MetricContract.model_validate(payload),
        )
    for field in ("path_override", "profile_override", "carrier_override"):
        payload = contract.model_dump() | {field: {"scope": 1}}
        _raises(
            ValidationError,
            field,
            lambda payload=payload: m.MetricContract.model_validate(payload),
        )
    old_unbounded = contract.model_dump()
    old_unbounded["contract_version"] = 2
    old_unbounded.pop("execution_mode")
    old_unbounded.pop("max_carrier_bytes")
    _raises(
        ValidationError,
        "contract version",
        lambda: m.MetricContract.model_validate(old_unbounded),
    )
    all_v4 = _s().model_dump(mode="json", by_alias=True)
    all_v4["contract_version"] = 4
    for item in all_v4["contracts"]:
        item["contract_version"] = 4
    _raises(
        ValidationError,
        "contract version",
        lambda: m.MetricContractSet.model_validate(all_v4),
    )


def test_metric_provider_resource_contract_rejects_mixed_provider_or_ceiling() -> None:
    lexical = _constructed_contract("lexical_tokens", "lexical_token")
    normalized = _constructed_contract("normalized_bytes", "normalized_byte")
    assert m.metric_provider_resource_contract((lexical, normalized)) == (
        "bounded_in_process_v1",
        65536,
    )
    drifted = _constructed_contract("normalized_bytes", "normalized_byte", max_carrier_bytes=32768)
    _raises(
        ValueError,
        "resource",
        lambda: m.metric_provider_resource_contract((lexical, drifted)),
    )
    other = _constructed_contract(
        "normalized_bytes",
        "normalized_byte",
        parser_id="json-stdlib",
        parser_version="cpython-3.14+ethos-json-v1",
        grammar_digest="b" * 64,
        normalization_id="structured-scalars",
    )
    _raises(ValueError, "provider", lambda: m.metric_provider_resource_contract((lexical, other)))


def test_metric_registry_rejects_cross_profile_provider_resource_drift() -> None:
    profiles = (
        _p(profile_id="python-a", required_metric_ids=("lexical_tokens",)),
        _p(profile_id="python-b", required_metric_ids=("normalized_bytes",)),
    )
    contracts = (
        _constructed_contract(
            "lexical_tokens", "lexical_token", metric_profile="python-a", contract_id="a"
        ),
        _constructed_contract(
            "normalized_bytes",
            "normalized_byte",
            metric_profile="python-b",
            contract_id="b",
            max_carrier_bytes=32768,
        ),
    )
    _raises(
        ValueError,
        "provider resource",
        lambda: m.MetricContractSet.model_construct(
            schema_id="ethos-source-budget-metrics-v3",
            contract_version=3,
            profiles=profiles,
            contracts=contracts,
        ),
    )


def test_metric_resource_fields_change_digest_and_schema_projection() -> None:
    contracts = (
        _constructed_contract("lexical_tokens", "lexical_token"),
        _constructed_contract("normalized_bytes", "normalized_byte"),
    )
    registry = m.MetricContractSet.model_construct(
        schema_id="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=(_p(),),
        contracts=contracts,
    )
    changed_contracts = tuple(
        item.model_copy(update={"max_carrier_bytes": 131072}) for item in contracts
    )
    changed = m.MetricContractSet.model_construct(
        schema_id="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=registry.profiles,
        contracts=changed_contracts,
    )
    assert m.metric_contracts_digest(registry) != m.metric_contracts_digest(changed)
    schema = m.metric_contracts_json_schema()
    assert schema["properties"]["schema"]["const"] == "ethos-source-budget-metrics-v3"
    contract_schema = schema["$defs"]["MetricContract"]
    assert contract_schema["properties"]["execution_mode"]["const"] == "bounded_in_process_v1"
    assert contract_schema["properties"]["max_carrier_bytes"]["exclusiveMinimum"] == 0


def test_repository_metric_policy_declares_v3_fixed_provider_ceilings() -> None:
    payload = tomllib.loads(Path("system/policies/source-budget-metrics.toml").read_text())
    assert payload["schema"] == "ethos-source-budget-metrics-v3"
    assert payload["contract_version"] == 3
    for contract in payload["contracts"]:
        expected = (
            262144
            if contract["parser_id"] == "utf8-footprint"
            else 65536
            if contract["parser_id"] == "python-tokenize"
            else 32768
        )
        assert contract["contract_version"] == 3
        assert contract["execution_mode"] == "bounded_in_process_v1"
        assert contract["max_carrier_bytes"] == expected


_EXECUTION_MODULE = "ethos_core.contracts.source_budget.measurement.execution"
_BOUNDED_ID = "ethos-source-budget-execution:bounded-in-process-v1"
_ISOLATED_ID = "ethos-source-budget-execution:isolated-worker-v1"
_PROTOCOL_ID = "ethos-source-budget-worker-protocol-v1"
_RESOURCE_ID = "ethos-source-budget-worker-resource-profile-v1"
_PROTOCOL_DESCRIPTOR = {
    "schema": "ethos-source-budget-worker-protocol-descriptor-v1",
    "id": _PROTOCOL_ID,
    "request_magic": "ESBWREQ1",
    "result_magic": "ESBWRES1",
    "length_encoding": "u32be",
    "header_max_bytes": 32768,
    "stdin_max_bytes": 327680,
    "result_max_bytes": 65536,
    "canonical_json": "utf8-sort-keys-compact-no-duplicates-v1",
}
_RESOURCE_DESCRIPTOR = {
    "schema": "ethos-source-budget-worker-resource-profile-descriptor-v1",
    "id": _RESOURCE_ID,
    "cpu_soft_seconds": 5,
    "cpu_hard_seconds": 6,
    "wall_seconds": 8,
    "rss_bytes": 134217728,
    "sample_interval_ms": 10,
    "linux_address_space_bytes": 536870912,
    "darwin_vms_growth_bytes": 536870912,
    "nofile": 32,
    "nproc": 1,
    "core_bytes": 0,
    "regular_file_bytes": 0,
    "term_grace_ms": 100,
    "stderr_bytes": 0,
    "private_home_tmp_cwd": True,
    "isolated_python_flags": ["-I", "-B", "-X", "utf8"],
    "close_file_descriptors": True,
    "start_new_session": True,
}


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _expected_execution_payload(mode: str, ceiling: int) -> dict[str, object]:
    execution_contract_id = _BOUNDED_ID if mode == "bounded_in_process_v1" else _ISOLATED_ID
    payload: dict[str, object] = {
        "schema": "ethos-source-budget-execution-descriptor-v1",
        "execution_contract_id": execution_contract_id,
        "execution_mode": mode,
        "max_carrier_bytes": ceiling,
    }
    if mode == "isolated_worker_v1":
        payload["worker_protocol"] = {
            "id": _PROTOCOL_ID,
            "digest": _canonical_sha256(_PROTOCOL_DESCRIPTOR),
        }
        payload["resource_profile"] = {
            "id": _RESOURCE_ID,
            "digest": _canonical_sha256(_RESOURCE_DESCRIPTOR),
        }
    return payload


def _expected_execution_fields(mode: str, ceiling: int) -> tuple[str, str]:
    payload = _expected_execution_payload(mode, ceiling)
    return str(payload["execution_contract_id"]), _canonical_sha256(payload)


def _v4_contract_payload(
    *,
    parser_id: str,
    parser_version: str,
    execution_mode: str,
    max_carrier_bytes: int,
    metric_id: str = "normalized_bytes",
    unit: str = "normalized_byte",
    metric_profile: str = "control-source-v2",
    carrier_role: str = "authored_declarative_source",
) -> dict[str, object]:
    execution_contract_id, execution_contract_digest = _expected_execution_fields(
        execution_mode,
        max_carrier_bytes,
    )
    return {
        "contract_id": f"{metric_profile}:{metric_id}",
        "contract_version": 4,
        "metric_id": metric_id,
        "unit": unit,
        "carrier_role": carrier_role,
        "metric_profile": metric_profile,
        "parser_id": parser_id,
        "parser_version": parser_version,
        "grammar_digest": "a" * 64,
        "normalization_id": "test-normalization",
        "normalization_version": "1",
        "aggregation": "sum",
        "non_compensable": True,
        "execution_mode": execution_mode,
        "max_carrier_bytes": max_carrier_bytes,
        "execution_contract_id": execution_contract_id,
        "execution_contract_digest": execution_contract_digest,
    }


def _constructed_v4_contract(**changes: object) -> m.MetricContract:
    payload = {
        "contract_id": "python-a:lexical_tokens",
        "contract_version": 4,
        "metric_id": "lexical_tokens",
        "unit": "lexical_token",
        "carrier_role": "authored_behavioral_source",
        "metric_profile": "python-a",
        "parser_id": "python-tokenize",
        "parser_version": "parser-v1",
        "grammar_digest": "a" * 64,
        "normalization_id": "python-source",
        "normalization_version": "1",
        "aggregation": "sum",
        "non_compensable": True,
        "execution_mode": "isolated_worker_v1",
        "max_carrier_bytes": 65536,
        "execution_contract_id": _ISOLATED_ID,
        "execution_contract_digest": "b" * 64,
    } | changes
    contract = m.MetricContract.model_construct(
        **{key: value for key, value in payload.items() if key in m.MetricContract.model_fields}
    )
    for field in ("execution_contract_id", "execution_contract_digest"):
        object.__setattr__(contract, field, payload[field])
    return contract


def test_metric_contract_v4_accepts_bounded_execution_identity() -> None:
    payload = _v4_contract_payload(
        parser_id="utf8-control",
        parser_version="cpython-3.14+ethos-utf8-v1",
        execution_mode="bounded_in_process_v1",
        max_carrier_bytes=32768,
    )
    contract = m.MetricContract.model_validate(payload)

    assert contract.execution_contract_id == _BOUNDED_ID
    assert contract.execution_contract_digest == payload["execution_contract_digest"]
    with pytest.raises(ValidationError, match="execution"):
        m.MetricContract.model_validate(payload | {"execution_contract_digest": "f" * 64})


def test_metric_contract_v4_accepts_isolated_execution_identity() -> None:
    payload = _v4_contract_payload(
        parser_id="python-tokenize",
        parser_version="cpython-3.14+ethos-python-v1",
        execution_mode="isolated_worker_v1",
        max_carrier_bytes=65536,
        metric_id="lexical_tokens",
        unit="lexical_token",
        metric_profile="python-source-v2",
        carrier_role="authored_behavioral_source",
    )
    contract = m.MetricContract.model_validate(payload)

    assert contract.execution_contract_id == _ISOLATED_ID
    assert contract.execution_contract_digest == payload["execution_contract_digest"]
    with pytest.raises(ValidationError, match="execution"):
        m.MetricContract.model_validate(payload | {"execution_contract_id": _BOUNDED_ID})


def test_metric_contract_v4_rejects_complete_legacy_v3_registry() -> None:
    base = _D["base_contract"]
    contracts = [
        base
        | {
            "contract_id": f"python-source-v2:{metric_id}",
            "metric_id": metric_id,
            "unit": unit,
        }
        for metric_id, unit in (
            ("lexical_tokens", "lexical_token"),
            ("normalized_bytes", "normalized_byte"),
        )
    ]
    payload = {
        "schema": "ethos-source-budget-metrics-v3",
        "contract_version": 3,
        "profiles": [_D["base_profile"]],
        "contracts": contracts,
    }

    with pytest.raises(ValidationError, match="version must be 4"):
        m.validate_metric_contracts(payload)


def test_metric_provider_resource_contract_returns_complete_v4_tuple() -> None:
    payloads = (
        _v4_contract_payload(
            parser_id="python-tokenize",
            parser_version="cpython-3.14+ethos-python-v1",
            execution_mode="isolated_worker_v1",
            max_carrier_bytes=65536,
            metric_id="lexical_tokens",
            unit="lexical_token",
            metric_profile="python-source-v2",
            carrier_role="authored_behavioral_source",
        ),
        _v4_contract_payload(
            parser_id="python-tokenize",
            parser_version="cpython-3.14+ethos-python-v1",
            execution_mode="isolated_worker_v1",
            max_carrier_bytes=65536,
            metric_id="normalized_bytes",
            unit="normalized_byte",
            metric_profile="python-source-v2",
            carrier_role="authored_behavioral_source",
        ),
    )
    contracts = tuple(m.MetricContract.model_validate(payload) for payload in payloads)
    expected_id, expected_digest = _expected_execution_fields("isolated_worker_v1", 65536)

    assert m.metric_provider_resource_contract(contracts) == (
        "isolated_worker_v1",
        65536,
        expected_id,
        expected_digest,
    )


def test_metric_registry_rejects_parser_global_execution_drift_across_versions() -> None:
    profiles = (
        m.MetricProfile(
            profile_id="python-a",
            carrier_role="authored_behavioral_source",
            required_metric_ids=("lexical_tokens",),
        ),
        m.MetricProfile(
            profile_id="python-b",
            carrier_role="authored_behavioral_source",
            required_metric_ids=("normalized_bytes",),
        ),
    )
    contracts = (
        _constructed_v4_contract(),
        _constructed_v4_contract(
            contract_id="python-b:normalized_bytes",
            metric_id="normalized_bytes",
            unit="normalized_byte",
            metric_profile="python-b",
            parser_version="parser-v2",
        ),
    )
    registry = m.MetricContractSet.model_construct(
        schema_id="ethos-source-budget-metrics-v4",
        contract_version=4,
        profiles=profiles,
        contracts=contracts,
    )
    assert registry.contracts == contracts

    for field, value in (
        ("execution_mode", "bounded_in_process_v1"),
        ("execution_contract_id", _BOUNDED_ID),
        ("execution_contract_digest", "c" * 64),
    ):
        drifted = _constructed_v4_contract(
            contract_id="python-b:normalized_bytes",
            metric_id="normalized_bytes",
            unit="normalized_byte",
            metric_profile="python-b",
            parser_version="parser-v2",
        )
        object.__setattr__(drifted, field, value)
        with pytest.raises(ValueError, match="provider execution"):
            m.MetricContractSet.model_construct(
                schema_id="ethos-source-budget-metrics-v4",
                contract_version=4,
                profiles=profiles,
                contracts=(contracts[0], drifted),
            )


def test_metric_contract_v4_schema_requires_execution_identity() -> None:
    schema = m.metric_contracts_json_schema()
    contract = schema["$defs"]["MetricContract"]

    assert schema["properties"]["schema"]["const"] == "ethos-source-budget-metrics-v4"
    assert schema["properties"]["contract_version"]["const"] == 4
    assert set(contract["properties"]["execution_mode"]["enum"]) == {
        "bounded_in_process_v1",
        "isolated_worker_v1",
    }
    assert {"execution_contract_id", "execution_contract_digest"} <= set(contract["required"])


def test_repository_metric_policy_declares_v4_static_hybrid_real_digests() -> None:
    payload = tomllib.loads(Path("system/policies/source-budget-metrics.toml").read_text())
    bounded = {"utf8-footprint", "utf8-control", "diagram-contract"}
    isolated = {
        "python-tokenize",
        "json-stdlib",
        "tomllib",
        "pyyaml-safe",
        "configparser",
        "jinja2",
        "shell-lexical",
    }

    assert payload["schema"] == "ethos-source-budget-metrics-v4"
    assert payload["contract_version"] == 4
    assert len(payload["profiles"]) == 16
    assert len(payload["contracts"]) == 28
    execution = importlib.import_module(_EXECUTION_MODULE)
    for contract in payload["contracts"]:
        parser_id = contract["parser_id"]
        expected_mode = "bounded_in_process_v1" if parser_id in bounded else "isolated_worker_v1"
        assert parser_id in bounded | isolated
        expected_id, expected_digest = _expected_execution_fields(
            expected_mode,
            contract["max_carrier_bytes"],
        )
        descriptor = execution.execution_descriptor(
            expected_mode,
            contract["max_carrier_bytes"],
        )
        assert descriptor.model_dump(mode="json") == _expected_execution_payload(
            expected_mode,
            contract["max_carrier_bytes"],
        )
        assert execution.execution_descriptor_digest(descriptor) == expected_digest
        assert contract["contract_version"] == 4
        assert contract["execution_mode"] == expected_mode
        assert contract["execution_contract_id"] == expected_id
        assert contract["execution_contract_digest"] == expected_digest
