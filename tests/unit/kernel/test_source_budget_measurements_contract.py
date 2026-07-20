from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.measurement.canonical as canonical
import ethos_core.contracts.source_budget.measurements as measurements_module
from ethos_core.contracts.source_budget.measurements import CarrierMeasurement
from ethos_core.contracts.source_budget.measurements import CarrierMeasurementLoad
from ethos_core.contracts.source_budget.measurements import MeasurementCoordinate
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshot
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshotLoad
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.measure import effective_code_lines
from tests.unit.kernel.source_budget_measurement_support import NORMALIZED
from tests.unit.kernel.source_budget_measurement_support import RAW_A
from tests.unit.kernel.source_budget_measurement_support import RAW_B
from tests.unit.kernel.source_budget_measurement_support import _carrier
from tests.unit.kernel.source_budget_measurement_support import _carrier_digest
from tests.unit.kernel.source_budget_measurement_support import _contract
from tests.unit.kernel.source_budget_measurement_support import _contract_set
from tests.unit.kernel.source_budget_measurement_support import _contracts
from tests.unit.kernel.source_budget_measurement_support import _identity
from tests.unit.kernel.source_budget_measurement_support import _inventory
from tests.unit.kernel.source_budget_measurement_support import _match
from tests.unit.kernel.source_budget_measurement_support import _native
from tests.unit.kernel.source_budget_measurement_support import _native_digest
from tests.unit.kernel.source_budget_measurement_support import _resolved_digest
from tests.unit.kernel.source_budget_measurement_support import _snapshot
from tests.unit.kernel.source_budget_measurement_support import _snapshot_digest
from tests.unit.kernel.source_budget_measurement_support import _value
from tests.unit.kernel.source_budget_measurement_support import _vector_digest


def test_measurement_models_are_frozen_strict_and_extra_forbid() -> None:
    value = _value()

    with pytest.raises(ValidationError):
        value.value = 4  # type: ignore[misc]

    payload = value.model_dump()
    payload["unexpected"] = True
    with pytest.raises(ValidationError, match="unexpected"):
        MetricValue.model_validate(payload)

    for invalid in (-1, True, 1.5, "1"):
        payload = value.model_dump()
        payload["value"] = invalid
        with pytest.raises(ValidationError):
            MetricValue.model_validate(payload)


def test_native_measurement_requires_stable_complete_values_and_exact_digest() -> None:
    lexical = _value()
    normalized = _value("normalized_bytes", "normalized_byte", 17)
    native = _native(values=(normalized, lexical))

    assert tuple(value.metric_id for value in native.values) == (
        "lexical_tokens",
        "normalized_bytes",
    )
    assert native.measurement_digest == _native_digest(
        content_sha256=RAW_A,
        normalized_digest=NORMALIZED,
        resolved_contracts_digest=native.resolved_contracts_digest,
        values=native.values,
    )
    assert native.resolved_contracts_digest == _resolved_digest(native.contracts)

    payload = native.model_dump()
    payload["measurement_digest"] = RAW_B
    with pytest.raises(ValidationError, match="native measurement digest"):
        NativeMeasurement.model_validate(payload)

    payload = native.model_dump()
    payload["values"] = [lexical.model_dump(), lexical.model_dump()]
    payload["measurement_digest"] = _native_digest(
        content_sha256=RAW_A,
        normalized_digest=NORMALIZED,
        resolved_contracts_digest=native.resolved_contracts_digest,
        values=(lexical, lexical),
    )
    with pytest.raises(ValidationError, match="metric coordinates"):
        NativeMeasurement.model_validate(payload)

    payload = native.model_dump()
    payload["values"] = list(reversed(payload["values"]))
    with pytest.raises(ValidationError, match="stably ordered"):
        NativeMeasurement.model_validate(payload)


def test_carrier_measurement_binds_identity_path_contracts_and_native_result() -> None:
    carrier = _carrier()

    assert carrier.measurement_digest == _carrier_digest(
        relative_path=carrier.relative_path,
        identity=carrier.identity,
        contract_set_digest=carrier.contract_set_digest,
        native=carrier.native,
    )

    payload = carrier.model_dump()
    payload["relative_path"] = "../escape.py"
    with pytest.raises(ValidationError, match="canonical relative path"):
        CarrierMeasurement.model_validate(payload)

    payload = carrier.model_dump()
    payload["measurement_digest"] = RAW_B
    with pytest.raises(ValidationError, match="carrier measurement digest"):
        CarrierMeasurement.model_validate(payload)

    excluded = _identity(
        carrier_id="runtime-local",
        scope_id="runtime.local",
        disposition="exclude",
    )
    payload = carrier.model_dump()
    payload["identity"] = excluded.model_dump()
    payload["measurement_digest"] = _carrier_digest(
        relative_path=carrier.relative_path,
        identity=excluded,
        contract_set_digest=carrier.contract_set_digest,
        native=carrier.native,
    )
    with pytest.raises(ValidationError, match="measured carrier identity"):
        CarrierMeasurement.model_validate(payload)


def test_snapshot_recomputes_coordinates_vector_and_snapshot_digests() -> None:
    first = _carrier()
    second = _carrier(
        relative_path="packages/other.py",
        native=_native(
            content_sha256=RAW_B,
            values=(
                _value("lexical_tokens", "lexical_token", 5),
                _value("normalized_bytes", "normalized_byte", 23),
            ),
        ),
    )

    forward = _snapshot((first, second))
    reverse = _snapshot((second, first))

    assert forward == reverse
    assert forward.coordinates == (
        MeasurementCoordinate(
            scope_id="product.python",
            metric_id="lexical_tokens",
            unit="lexical_token",
            value=8,
        ),
        MeasurementCoordinate(
            scope_id="product.python",
            metric_id="normalized_bytes",
            unit="normalized_byte",
            value=40,
        ),
    )
    assert forward.vector_digest == _vector_digest(forward.coordinates)
    assert forward.snapshot_digest == _snapshot_digest(
        manifest_digest=forward.manifest_digest,
        inventory_digest=forward.inventory_digest,
        contract_set_digest=forward.contract_set_digest,
        measurements=forward.measurements,
        coordinates=forward.coordinates,
    )

    payload = forward.model_dump()
    payload["coordinates"][0]["value"] = 7
    payload["vector_digest"] = _vector_digest(
        tuple(MeasurementCoordinate.model_validate(item) for item in payload["coordinates"])
    )
    payload["snapshot_digest"] = _snapshot_digest(
        manifest_digest=forward.manifest_digest,
        inventory_digest=forward.inventory_digest,
        contract_set_digest=forward.contract_set_digest,
        measurements=forward.measurements,
        coordinates=tuple(
            MeasurementCoordinate.model_validate(item) for item in payload["coordinates"]
        ),
    )
    with pytest.raises(ValidationError, match="aggregated coordinates"):
        MeasurementSnapshot.model_validate(payload)

    payload = forward.model_dump()
    payload["measurements"] = list(reversed(payload["measurements"]))
    with pytest.raises(ValidationError, match="stably ordered"):
        MeasurementSnapshot.model_validate(payload)


def test_raw_content_identity_is_separate_from_normalized_vector_identity() -> None:
    first = _carrier(native=_native(content_sha256=RAW_A))
    second = _carrier(native=_native(content_sha256=RAW_B))

    assert first.native.normalized_digest == second.native.normalized_digest
    assert first.native.values == second.native.values
    assert first.native.measurement_digest != second.native.measurement_digest
    assert first.measurement_digest != second.measurement_digest

    first_snapshot = _snapshot((first,))
    second_snapshot = _snapshot((second,))
    assert first_snapshot.coordinates == second_snapshot.coordinates
    assert first_snapshot.vector_digest == second_snapshot.vector_digest
    assert first_snapshot.snapshot_digest != second_snapshot.snapshot_digest


def test_domain_movement_changes_identity_and_coordinate_domain() -> None:
    product = _carrier()
    moved = _carrier(
        identity=_identity(
            carrier_id="python-source-moved",
            scope_id="product.python.moved",
        ),
    )

    assert product.native == moved.native
    assert product.measurement_digest != moved.measurement_digest
    assert _snapshot((product,)).coordinates[0].scope_id == "product.python"
    assert _snapshot((moved,)).coordinates[0].scope_id == "product.python.moved"
    assert _snapshot((product,)).snapshot_digest != _snapshot((moved,)).snapshot_digest


@pytest.mark.parametrize(
    ("load_type", "field", "typed", "context"),
    [
        (NativeMeasurementLoad, "measurement", _native(), {}),
        (
            CarrierMeasurementLoad,
            "measurement",
            _carrier(),
            {"match": _match(), "contracts": _contract_set()},
        ),
        (
            MeasurementSnapshotLoad,
            "snapshot",
            _snapshot(),
            {
                "inventory": _inventory(("packages/sample.py",)),
                "contracts": _contract_set(),
            },
        ),
    ],
)
def test_measurement_load_envelopes_require_exact_success_gap_xor(
    load_type: type[object],
    field: str,
    typed: object,
    context: dict[str, object],
) -> None:
    assert load_type(**{field: typed, "required_gaps": ()}, **context)

    with pytest.raises(ValueError, match="non-empty required gaps"):
        load_type(**{field: None, "required_gaps": ()})

    with pytest.raises(ValueError, match="forbids required gaps"):
        load_type(**{field: typed, "required_gaps": ("gap",)})

    with pytest.raises(ValueError, match="tuple"):
        load_type(**{field: None, "required_gaps": ["gap"]})

    with pytest.raises(ValueError, match="unique and stably ordered"):
        load_type(**{field: None, "required_gaps": ("z", "a", "z")})

    with pytest.raises(ValueError, match="typed"):
        load_type(**{field: object(), "required_gaps": ()})


def test_native_measurement_rejects_duplicate_contract_ids() -> None:
    lexical = _value()
    duplicate_contract = MetricValue(
        contract_id=lexical.contract_id,
        metric_id="normalized_bytes",
        unit="normalized_byte",
        value=17,
    )
    values = (lexical, duplicate_contract)
    contracts = _contracts()
    resolved_contracts_digest = _resolved_digest(contracts)
    payload = {
        "content_sha256": RAW_A,
        "normalized_digest": NORMALIZED,
        "contracts": [contract.model_dump() for contract in contracts],
        "resolved_contracts_digest": resolved_contracts_digest,
        "values": [value.model_dump() for value in values],
        "measurement_digest": _native_digest(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            resolved_contracts_digest=resolved_contracts_digest,
            values=values,
        ),
    }

    with pytest.raises(ValidationError, match="contract ids"):
        NativeMeasurement.model_validate(payload)


def test_snapshot_rejects_contract_set_vector_and_snapshot_forgery() -> None:
    snapshot = _snapshot()
    carrier = snapshot.measurements[0]
    mismatched_payload = carrier.model_dump()
    mismatched_payload["contract_set_digest"] = RAW_B
    mismatched_payload["measurement_digest"] = _carrier_digest(
        relative_path=carrier.relative_path,
        identity=carrier.identity,
        contract_set_digest=RAW_B,
        native=carrier.native,
    )
    mismatched = CarrierMeasurement.model_validate(mismatched_payload)
    coordinates = snapshot.coordinates
    payload = snapshot.model_dump()
    payload["measurements"] = [mismatched.model_dump()]
    payload["snapshot_digest"] = _snapshot_digest(
        manifest_digest=snapshot.manifest_digest,
        inventory_digest=snapshot.inventory_digest,
        contract_set_digest=snapshot.contract_set_digest,
        measurements=(mismatched,),
        coordinates=coordinates,
    )
    with pytest.raises(ValidationError, match="contract-set digest"):
        MeasurementSnapshot.model_validate(payload)

    payload = snapshot.model_dump()
    payload["vector_digest"] = RAW_B
    with pytest.raises(ValidationError, match="vector digest"):
        MeasurementSnapshot.model_validate(payload)

    payload = snapshot.model_dump()
    payload["snapshot_digest"] = RAW_B
    with pytest.raises(ValidationError, match="snapshot digest"):
        MeasurementSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    "relative_path",
    [
        "/absolute.py",
        "./prefixed.py",
        f"dir{chr(92)}file.py",
        f"dir{chr(0)}file.py",
    ],
)
def test_carrier_measurement_rejects_noncanonical_path_forms(
    relative_path: str,
) -> None:
    carrier = _carrier()
    payload = carrier.model_dump()
    payload["relative_path"] = relative_path

    with pytest.raises(ValidationError, match="canonical relative path"):
        CarrierMeasurement.model_validate(payload)


def test_carrier_measurement_rejects_non_unicode_string_input() -> None:
    carrier = _carrier()
    payload = carrier.model_dump()
    payload["relative_path"] = chr(0xD800) + ".py"

    with pytest.raises(ValidationError, match="valid string"):
        CarrierMeasurement.model_validate(payload)


@pytest.mark.parametrize("gap", ["", 1])
def test_measurement_load_rejects_invalid_gap_items(gap: object) -> None:
    with pytest.raises(ValueError, match="non-empty strings"):
        NativeMeasurementLoad(None, (gap,))  # type: ignore[arg-type]


def test_native_constructor_requires_complete_resolved_contract_vector() -> None:
    with pytest.raises(ValidationError, match="complete declared contract vector"):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=_contracts(),
            values=(_value(),),
        )


def test_canonical_digest_has_reviewed_golden_and_domain_separation() -> None:
    contract = _contract("lexical_tokens", "lexical_token")
    coordinate = MeasurementCoordinate(
        scope_id="product.python",
        metric_id="lexical_tokens",
        unit="lexical_token",
        value=3,
    )
    resolved_digest = canonical.resolved_model_digest((contract,))
    vector_digest = canonical.vector_model_digest((coordinate,))

    assert resolved_digest == ("f356f9dedc12a615f9594fef9aac0f6c527f50416ba49ae787984fcaa80c739c")
    assert vector_digest == "a6ac56136eed38a95f73e6825ce8107f58ac1cbdf175e9ebddd75b76175c3f24"
    assert resolved_digest != vector_digest
    assert not canonical.is_valid_relative_path(chr(0xD800))


def test_contract_module_surface_and_effective_size_are_bounded() -> None:
    for removed in (
        "build_native_measurement",
        "build_carrier_measurement",
        "build_measurement_snapshot",
        "native_measurement_digest",
        "resolved_metric_contracts_digest",
        "carrier_measurement_digest",
        "measurement_vector_digest",
        "measurement_snapshot_digest",
        "_native_digest",
        "_resolved_contracts_digest",
        "_carrier_digest",
        "_vector_digest",
        "_snapshot_digest",
    ):
        assert not hasattr(measurements_module, removed)

    assert not hasattr(canonical, "__all__")
    assert measurements_module.__file__ is not None
    assert effective_code_lines(Path(measurements_module.__file__)) <= 500
