from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.measurement.admission as admission
import ethos_core.contracts.source_budget.measurement.canonical as canonical
from ethos_core.contracts.source_budget.carriers import CarrierMatch
from ethos_core.contracts.source_budget.measurements import CarrierMeasurement
from ethos_core.contracts.source_budget.measurements import CarrierMeasurementLoad
from ethos_core.contracts.source_budget.measurements import MeasurementCoordinate
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshot
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshotLoad
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import metric_contracts_digest
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
from tests.unit.kernel.source_budget_measurement_support import _snapshot
from tests.unit.kernel.source_budget_measurement_support import _snapshot_digest
from tests.unit.kernel.source_budget_measurement_support import _value
from tests.unit.kernel.source_budget_measurement_support import _vector_digest

if TYPE_CHECKING:
    from collections.abc import Iterator


def test_nested_model_instances_are_revalidated() -> None:
    forged_value = MetricValue.model_construct(
        contract_id="python-source-v2:lexical_tokens",
        metric_id="lexical_tokens",
        unit="lexical_token",
        value=True,
    )
    with pytest.raises(ValidationError, match="typed metric value"):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=(_contract("lexical_tokens", "lexical_token"),),
            values=(forged_value,),
        )

    native = _native()
    forged_native = NativeMeasurement.model_construct(
        content_sha256=native.content_sha256,
        normalized_digest=native.normalized_digest,
        contracts=native.contracts,
        resolved_contracts_digest=native.resolved_contracts_digest,
        values=native.values,
        measurement_digest=RAW_B,
    )
    with pytest.raises(ValidationError, match="typed native measurement"):
        CarrierMeasurement.create(
            match=_match(),
            contracts=_contract_set(),
            native=forged_native,
        )


def test_snapshot_can_bind_an_all_excluded_inventory_with_empty_vector() -> None:
    excluded = _identity(
        carrier_id="documentation-excluded",
        scope_id="docs",
        disposition="exclude",
        extensions=(".md",),
        include=("docs/**",),
    )
    inventory = _inventory(("docs/a.md", "docs/b.md"), (excluded,))
    snapshot = MeasurementSnapshot.from_inventory(
        inventory=inventory,
        contracts=_contract_set(),
        measurements=(),
    )

    assert snapshot.inventory_digest == inventory.inventory_digest
    assert snapshot.measurements == ()
    assert snapshot.coordinates == ()
    assert snapshot.vector_digest == _vector_digest(())


def test_all_nested_measurement_models_reject_constructed_forgeries() -> None:
    contract_payload = _contract("lexical_tokens", "lexical_token").model_dump()
    contract_payload["contract_version"] = True
    forged_contract = MetricContract.model_construct(**contract_payload)
    with pytest.raises(ValidationError, match="typed metric contract"):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=(forged_contract,),
            values=(_value(),),
        )

    carrier = _carrier()
    forged_carrier = CarrierMeasurement.model_construct(
        relative_path=carrier.relative_path,
        identity=carrier.identity,
        contract_set_digest=carrier.contract_set_digest,
        native=carrier.native,
        measurement_digest=RAW_B,
    )
    with pytest.raises(ValidationError, match="typed carrier measurement"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory((carrier.relative_path,)),
            contracts=_contract_set(),
            measurements=(forged_carrier,),
        )

    snapshot = _snapshot()
    coordinate = snapshot.coordinates[0]
    forged_coordinate_payload = coordinate.model_dump()
    forged_coordinate_payload["value"] = True
    forged_coordinate = MeasurementCoordinate.model_construct(**forged_coordinate_payload)
    payload = snapshot.model_dump()
    payload["coordinates"] = (forged_coordinate,)
    with pytest.raises(ValidationError, match="typed measurement coordinate"):
        MeasurementSnapshot.model_validate(payload)


def test_nested_measurement_models_reject_subclasses() -> None:
    class MetricValueSubclass(MetricValue):
        pass

    class CarrierMatchSubclass(CarrierMatch):
        pass

    class NativeMeasurementSubclass(NativeMeasurement):
        pass

    class CarrierMeasurementSubclass(CarrierMeasurement):
        pass

    subclass_value = MetricValueSubclass.model_validate(_value().model_dump())
    with pytest.raises(ValidationError, match="typed metric value"):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=(_contract("lexical_tokens", "lexical_token"),),
            values=(subclass_value,),
        )

    subclass_match = CarrierMatchSubclass.model_validate(_match().model_dump())
    with pytest.raises(ValidationError, match="typed classified carrier match"):
        CarrierMeasurement.create(
            match=subclass_match,
            contracts=_contract_set(),
            native=_native(),
        )

    subclass_native = NativeMeasurementSubclass.model_validate(_native().model_dump())
    with pytest.raises(ValidationError, match="typed native measurement"):
        CarrierMeasurement.create(
            match=_match(),
            contracts=_contract_set(),
            native=subclass_native,
        )

    subclass_carrier = CarrierMeasurementSubclass.model_validate(_carrier().model_dump())
    with pytest.raises(ValidationError, match="typed carrier measurement"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory((subclass_carrier.relative_path,)),
            contracts=_contract_set(),
            measurements=(subclass_carrier,),
        )


def test_loads_reject_nested_model_subclasses_without_caller_equality() -> None:
    class ExplodingValueSubclass(MetricValue):
        __hash__ = MetricValue.__hash__

        def __eq__(self, other: object) -> bool:
            message = "caller equality must not run"
            raise RuntimeError(message)

    class ExtendedContract(MetricContract):
        extra_marker: str

    native = _native()
    subclass_value = ExplodingValueSubclass.model_validate(native.values[0].model_dump())
    forged_native = NativeMeasurement.model_construct(
        **{
            **native.model_dump(),
            "contracts": native.contracts,
            "values": (subclass_value, *native.values[1:]),
        }
    )
    with pytest.raises(ValueError, match="load requires typed data") as error:
        NativeMeasurementLoad(forged_native, ())
    assert error.value.__cause__ is None

    extended_contract = ExtendedContract.model_validate(
        {**native.contracts[0].model_dump(), "extra_marker": "must-not-disappear"}
    )
    forged_native = NativeMeasurement.model_construct(
        **{
            **native.model_dump(),
            "contracts": (extended_contract, *native.contracts[1:]),
            "values": native.values,
        }
    )
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(forged_native, ())

    registry = _contract_set()
    extended_context_contract = ExtendedContract.model_validate(
        {**registry.contracts[0].model_dump(), "extra_marker": "context"}
    )
    forged_registry = type(registry).model_construct(
        **{
            **registry.model_dump(),
            "profiles": registry.profiles,
            "contracts": (extended_context_contract, *registry.contracts[1:]),
        }
    )
    with pytest.raises(ValueError, match="success load requires typed context"):
        CarrierMeasurementLoad(
            _carrier(contracts=registry),
            (),
            match=_match(),
            contracts=forged_registry,
        )


def test_snapshot_rejects_empty_inventory_and_persisted_count_fields() -> None:
    with pytest.raises(ValidationError, match="gap-free carrier inventory"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory(()),
            contracts=_contract_set(),
            measurements=(),
        )

    payload = _snapshot().model_dump()
    payload["inventory_match_count"] = 1
    with pytest.raises(ValidationError, match="inventory_match_count"):
        MeasurementSnapshot.model_validate(payload)


def test_native_measurement_rejects_contract_order_identity_and_digest_forgery() -> None:
    native = _native()

    payload = native.model_dump()
    payload["contracts"] = list(reversed(payload["contracts"]))
    with pytest.raises(ValidationError, match="contracts must be stably ordered"):
        NativeMeasurement.model_validate(payload)

    payload = native.model_dump()
    payload["contracts"][1]["contract_id"] = payload["contracts"][0]["contract_id"]
    with pytest.raises(ValidationError, match="contract ids must be unique"):
        NativeMeasurement.model_validate(payload)

    first_payload = _contract("lexical_tokens", "lexical_token").model_dump()
    first_payload["contract_id"] = "python-source-v2:a-lexical"
    second_payload = dict(first_payload)
    second_payload["contract_id"] = "python-source-v2:z-lexical"
    payload = native.model_dump()
    payload["contracts"] = [first_payload, second_payload]
    with pytest.raises(ValidationError, match="contract coordinates must be unique"):
        NativeMeasurement.model_validate(payload)

    payload = native.model_dump()
    payload["resolved_contracts_digest"] = RAW_B
    with pytest.raises(ValidationError, match="resolved-contracts digest"):
        NativeMeasurement.model_validate(payload)


def test_nested_collection_shape_and_load_forgery_fail_closed() -> None:
    payload = _native().model_dump()
    payload["values"] = 1
    with pytest.raises(ValidationError, match="typed metric value tuple"):
        NativeMeasurement.model_validate(payload)

    native = _native()
    forged_native = NativeMeasurement.model_construct(
        content_sha256=native.content_sha256,
        normalized_digest=native.normalized_digest,
        contracts=native.contracts,
        resolved_contracts_digest=native.resolved_contracts_digest,
        values=native.values,
        measurement_digest=RAW_B,
    )
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(forged_native, ())


def test_loads_require_exact_typed_success_data_and_context() -> None:
    native = _native()
    carrier = _carrier()
    registry = _contract_set()
    match = _match()
    inventory = _inventory((carrier.relative_path,))
    snapshot = _snapshot(inventory=inventory, contracts=registry)

    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(native.model_dump(), ())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="load requires typed data"):
        CarrierMeasurementLoad(  # type: ignore[arg-type]
            carrier.model_dump(),
            (),
            match=match,
            contracts=registry,
        )
    with pytest.raises(ValueError, match="load requires typed data"):
        MeasurementSnapshotLoad(  # type: ignore[arg-type]
            snapshot.model_dump(),
            (),
            inventory=inventory,
            contracts=registry,
        )

    with pytest.raises(ValueError, match="requires typed context"):
        CarrierMeasurementLoad(  # type: ignore[arg-type]
            carrier,
            (),
            match=match.model_dump(),
            contracts=registry,
        )
    with pytest.raises(ValueError, match="requires typed context"):
        CarrierMeasurementLoad(  # type: ignore[arg-type]
            carrier,
            (),
            match=match,
            contracts=registry.model_dump(by_alias=True),
        )
    with pytest.raises(ValueError, match="requires typed context"):
        MeasurementSnapshotLoad(  # type: ignore[arg-type]
            snapshot,
            (),
            inventory=inventory.model_dump(),
            contracts=registry,
        )
    with pytest.raises(ValueError, match="requires typed context"):
        MeasurementSnapshotLoad(  # type: ignore[arg-type]
            snapshot,
            (),
            inventory=inventory,
            contracts=registry.model_dump(by_alias=True),
        )


def test_loads_reject_mutable_constructed_data_and_forged_typed_context() -> None:
    native = _native()
    payload = native.model_dump()
    mutable_native = NativeMeasurement.model_construct(
        **{
            **payload,
            "contracts": list(native.contracts),
            "values": list(native.values),
        }
    )
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(mutable_native, ())

    tainted_native = native.model_copy()
    object.__setattr__(
        tainted_native,
        "__pydantic_private__",
        {"hidden": "state"},
    )
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(tainted_native, ())

    missing_internal_state = native.model_copy()
    object.__delattr__(missing_internal_state, "__pydantic_extra__")
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(missing_internal_state, ())

    model_cycle = native.model_copy()
    object.__getattribute__(model_cycle, "__dict__")["contracts"] = (model_cycle,)
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(model_cycle, ())

    tuple_cycle = native.model_copy()
    tuple_cycle_contract = native.contracts[0].model_copy()
    repeated_tuple = (tuple_cycle_contract,)
    object.__getattribute__(tuple_cycle, "__dict__")["contracts"] = repeated_tuple
    object.__getattribute__(tuple_cycle_contract, "__dict__")["contract_id"] = repeated_tuple
    with pytest.raises(ValueError, match="load requires typed data"):
        NativeMeasurementLoad(tuple_cycle, ())

    class SwitchableTuple(tuple[object, ...]):
        __slots__ = ()

        hidden = False

        def __iter__(self) -> Iterator[object]:
            return iter(()) if type(self).hidden else super().__iter__()

    noncanonical_native = NativeMeasurement.model_construct(
        **{
            **payload,
            "contracts": SwitchableTuple(native.contracts),
            "values": SwitchableTuple(native.values),
        }
    )
    loaded = NativeMeasurementLoad(noncanonical_native, ())
    assert loaded.measurement is not noncanonical_native
    assert loaded.measurement is not None
    assert type(loaded.measurement.contracts) is tuple
    assert type(loaded.measurement.values) is tuple
    SwitchableTuple.hidden = True
    assert loaded.measurement.values == native.values

    registry = _contract_set()
    forged_payload = registry.contracts[0].model_dump()
    forged_payload["contract_version"] = 2.0
    forged_contract = MetricContract.model_construct(**forged_payload)
    forged_registry = type(registry).model_construct(
        schema=registry.schema_id,
        contract_version=registry.contract_version,
        profiles=registry.profiles,
        contracts=(forged_contract, *registry.contracts[1:]),
    )
    with pytest.raises(ValueError, match="success load requires typed context"):
        CarrierMeasurementLoad(
            _carrier(contracts=registry),
            (),
            match=_match(),
            contracts=forged_registry,
        )


def test_loads_require_exact_builtin_gaps_and_forbid_subclasses() -> None:
    class SwallowFinality:
        def __init_subclass__(cls, **_kwargs: object) -> None:
            pass

    class FalseyTuple(tuple[str, ...]):
        __slots__ = ()

        def __bool__(self) -> bool:
            return False

    class TruthyTuple(tuple[str, ...]):
        __slots__ = ()

        def __bool__(self) -> bool:
            return True

    class Gap(str):
        __slots__ = ()

    with pytest.raises(ValueError, match="required gaps must be a tuple"):
        NativeMeasurementLoad(_native(), FalseyTuple(("hidden_gap",)))
    with pytest.raises(ValueError, match="required gaps must be a tuple"):
        NativeMeasurementLoad(None, TruthyTuple())
    with pytest.raises(ValueError, match="non-empty strings"):
        NativeMeasurementLoad(None, (Gap("hidden_gap"),))

    for load_type in (
        NativeMeasurementLoad,
        CarrierMeasurementLoad,
        MeasurementSnapshotLoad,
    ):
        with pytest.raises(TypeError, match="forbid subclasses"):
            type("BypassLoad", (load_type,), {"__post_init__": lambda _self: None})

    with pytest.raises(TypeError, match="forbid subclasses"):

        class RedundantBaseBypass(NativeMeasurementLoad, admission.FinalLoad):
            def __post_init__(self) -> None:
                pass

    with pytest.raises(TypeError, match="forbid subclasses"):

        class SwallowedFinalityBypass(SwallowFinality, NativeMeasurementLoad):
            def __post_init__(self) -> None:
                pass


def test_loads_hide_instance_serialization_failures_behind_stable_errors() -> None:
    class SwitchableKey(str):
        __slots__ = ()

        fail = False

        def __hash__(self) -> int:
            if type(self).fail:
                message = "caller-owned key detail"
                raise RuntimeError(message)
            return super().__hash__()

    def fail_dump(*_args: object, **_kwargs: object) -> object:
        message = "caller-owned runtime detail"
        raise RuntimeError(message)

    native = _native()
    object.__setattr__(native, "model_dump", fail_dump)
    with pytest.raises(ValueError, match="native measurement load requires typed data") as error:
        NativeMeasurementLoad(native, ())
    assert error.value.__cause__ is None

    keyed = _native()
    storage = object.__getattribute__(keyed, "__dict__")
    content_sha256 = storage.pop("content_sha256")
    storage[SwitchableKey("content_sha256")] = content_sha256
    SwitchableKey.fail = True
    with pytest.raises(ValueError, match="native measurement load requires typed data") as error:
        NativeMeasurementLoad(keyed, ())
    assert error.value.__cause__ is None

    SwitchableKey.fail = False
    nested = _native()
    contract = nested.contracts[0].model_copy()
    contract_storage = object.__getattribute__(contract, "__dict__")
    contract_id = contract_storage.pop("contract_id")
    contract_storage[SwitchableKey("contract_id")] = contract_id
    nested_keyed = NativeMeasurement.model_construct(
        **{
            **nested.model_dump(),
            "contracts": (contract, *nested.contracts[1:]),
        }
    )
    SwitchableKey.fail = True
    with pytest.raises(ValueError, match="native measurement load requires typed data") as error:
        NativeMeasurementLoad(nested_keyed, ())
    assert error.value.__cause__ is None

    match = _match()
    object.__setattr__(match, "model_dump", fail_dump)
    with pytest.raises(
        ValueError,
        match="carrier measurement success load requires typed context",
    ) as error:
        CarrierMeasurementLoad(
            _carrier(),
            (),
            match=match,
            contracts=_contract_set(),
        )
    assert error.value.__cause__ is None


def test_canonical_constructors_close_role_profile_and_inventory_identity() -> None:
    documentation_payload = _contract("normalized_bytes", "normalized_byte").model_dump()
    documentation_payload.update(
        {
            "contract_id": "documentation-v2:normalized_bytes",
            "carrier_role": "documentation",
            "metric_profile": "documentation-v2",
        }
    )
    documentation_contract = MetricContract.model_validate(documentation_payload)
    documentation_value = MetricValue(
        contract_id=documentation_contract.contract_id,
        metric_id=documentation_contract.metric_id,
        unit=documentation_contract.unit,
        value=17,
    )
    with pytest.raises(ValidationError, match="one carrier role and metric profile"):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=(
                _contract("lexical_tokens", "lexical_token"),
                documentation_contract,
            ),
            values=(_value(), documentation_value),
        )

    documentation = _identity(
        carrier_id="documentation",
        scope_id="docs",
        role="documentation",
        metric_profile="documentation-v2",
        extensions=(".md",),
        include=("docs/**",),
    )
    with pytest.raises(ValidationError):
        CarrierMeasurement.create(
            match=_match("docs/sample.md", documentation),
            contracts=_contract_set(),
            native=_native(),
        )

    carrier = _carrier()
    snapshot = MeasurementSnapshot.from_inventory(
        inventory=_inventory((carrier.relative_path,)),
        contracts=_contract_set(),
        measurements=(carrier,),
    )
    assert snapshot.measurements == (carrier,)

    with pytest.raises(ValidationError, match="classified inventory"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory(("packages/other.py",)),
            contracts=_contract_set(),
            measurements=(carrier,),
        )


def test_canonical_constructors_reject_non_strict_and_non_utf8_primitives() -> None:
    with pytest.raises(ValidationError):
        NativeMeasurement.create(
            content_sha256=b"a" * 64,  # type: ignore[arg-type]
            normalized_digest=NORMALIZED,
            contracts=_contracts(),
            values=(_value(), _value("normalized_bytes", "normalized_byte", 17)),
        )

    contract_payload = _contract("lexical_tokens", "lexical_token").model_dump()
    contract_payload["contract_id"] = f"python-source-v2:{chr(0xD800)}"
    contract = MetricContract.model_construct(**contract_payload)
    value = MetricValue.model_construct(
        contract_id=contract.contract_id,
        metric_id=contract.metric_id,
        unit=contract.unit,
        value=1,
    )
    with pytest.raises(ValidationError):
        NativeMeasurement.create(
            content_sha256=RAW_A,
            normalized_digest=NORMALIZED,
            contracts=(contract,),
            values=(value,),
        )
    coordinate = MeasurementCoordinate.model_construct(
        scope_id="product.python",
        metric_id=chr(0xD800),
        unit="lexical_token",
        value=1,
    )
    with pytest.raises(ValueError, match="UTF-8"):
        canonical.vector_model_digest((coordinate,))


def test_snapshot_rejects_registry_incomplete_but_digest_consistent_carrier() -> None:
    registry = _contract_set()
    identity = _identity()
    partial_native = NativeMeasurement.create(
        content_sha256=RAW_A,
        normalized_digest=NORMALIZED,
        contracts=(_contract("lexical_tokens", "lexical_token"),),
        values=(_value(),),
    )
    contract_digest = metric_contracts_digest(registry)
    partial_carrier = CarrierMeasurement.model_validate(
        {
            "relative_path": "packages/sample.py",
            "identity": identity.model_dump(),
            "contract_set_digest": contract_digest,
            "native": partial_native.model_dump(),
            "measurement_digest": _carrier_digest(
                relative_path="packages/sample.py",
                identity=identity,
                contract_set_digest=contract_digest,
                native=partial_native,
            ),
        }
    )

    with pytest.raises(ValidationError, match="classified identity resolution"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory(("packages/sample.py",)),
            contracts=registry,
            measurements=(partial_carrier,),
        )

    with pytest.raises(ValueError, match="success load requires context"):
        CarrierMeasurementLoad(partial_carrier, ())
    with pytest.raises(ValueError, match="success context must reproduce"):
        CarrierMeasurementLoad(
            partial_carrier,
            (),
            match=_match(),
            contracts=registry,
        )

    carrier = _carrier(contracts=registry)
    assert (
        CarrierMeasurementLoad(
            carrier,
            (),
            match=_match(),
            contracts=registry,
        ).measurement
        == carrier
    )
    assert CarrierMeasurementLoad(None, ("carrier_missing",)).measurement is None
    with pytest.raises(ValueError, match="success load requires context"):
        CarrierMeasurementLoad(carrier, (), match=_match())
    with pytest.raises(ValueError, match="requires typed context"):
        CarrierMeasurementLoad(  # type: ignore[arg-type]
            carrier,
            (),
            match=object(),
            contracts=registry,
        )
    expanded_payload = registry.model_dump(by_alias=True)
    expanded_payload["profiles"] = (
        *expanded_payload["profiles"],
        {
            "profile_id": "documentation-v2",
            "carrier_role": "documentation",
            "required_metric_ids": ("normalized_bytes",),
        },
    )
    documentation_contract = _contract("normalized_bytes", "normalized_byte").model_dump()
    documentation_contract.update(
        {
            "contract_id": "documentation-v2:normalized_bytes",
            "carrier_role": "documentation",
            "metric_profile": "documentation-v2",
        }
    )
    expanded_payload["contracts"] = (
        *expanded_payload["contracts"],
        documentation_contract,
    )
    expanded_registry = type(registry).model_validate(expanded_payload)
    with pytest.raises(ValueError, match="success context must reproduce"):
        CarrierMeasurementLoad(
            carrier,
            (),
            match=_match(),
            contracts=expanded_registry,
        )
    with pytest.raises(ValueError, match="failure load forbids context"):
        CarrierMeasurementLoad(
            None,
            ("carrier_missing",),
            match=_match(),
            contracts=registry,
        )


def test_snapshot_load_requires_complete_inventory_context_and_exact_replay() -> None:
    registry = _contract_set()
    first = _carrier(relative_path="packages/a.py", contracts=registry)
    second = _carrier(relative_path="packages/b.py", contracts=registry)
    full_inventory = _inventory(("packages/a.py", "packages/b.py"))
    single = _snapshot(
        (first,),
        inventory=_inventory(("packages/a.py",)),
        contracts=registry,
    )
    payload = single.model_dump()
    payload["manifest_digest"] = full_inventory.manifest_digest
    payload["inventory_digest"] = full_inventory.inventory_digest
    payload["snapshot_digest"] = _snapshot_digest(
        manifest_digest=full_inventory.manifest_digest,
        inventory_digest=full_inventory.inventory_digest,
        contract_set_digest=single.contract_set_digest,
        measurements=single.measurements,
        coordinates=single.coordinates,
    )
    partial = MeasurementSnapshot.model_validate(payload)

    with pytest.raises(ValueError, match="success load requires context"):
        MeasurementSnapshotLoad(partial, ())
    with pytest.raises(ValueError, match="success context must reproduce"):
        MeasurementSnapshotLoad(
            partial,
            (),
            inventory=full_inventory,
            contracts=registry,
        )

    complete = _snapshot(
        (first, second),
        inventory=full_inventory,
        contracts=registry,
    )
    assert (
        MeasurementSnapshotLoad(
            complete,
            (),
            inventory=full_inventory,
            contracts=registry,
        ).snapshot
        == complete
    )
    with pytest.raises(ValueError, match="success load requires context"):
        MeasurementSnapshotLoad(complete, (), inventory=full_inventory)
    with pytest.raises(ValueError, match="requires typed context"):
        MeasurementSnapshotLoad(  # type: ignore[arg-type]
            complete,
            (),
            inventory=object(),
            contracts=registry,
        )
    with pytest.raises(ValueError, match="failure load forbids context"):
        MeasurementSnapshotLoad(
            None,
            ("snapshot_missing",),
            inventory=full_inventory,
            contracts=registry,
        )


def test_carrier_and_snapshot_contextual_forgery_branches_fail_closed() -> None:
    carrier = _carrier()
    wrong_path_identity = _identity(
        carrier_id="other-python",
        include=("other/**",),
    )
    payload = carrier.model_dump()
    payload["identity"] = wrong_path_identity.model_dump()
    payload["measurement_digest"] = _carrier_digest(
        relative_path=carrier.relative_path,
        identity=wrong_path_identity,
        contract_set_digest=carrier.contract_set_digest,
        native=carrier.native,
    )
    with pytest.raises(ValidationError, match="complete carrier identity"):
        CarrierMeasurement.model_validate(payload)

    documentation = _identity(
        carrier_id="documentation",
        scope_id="docs",
        role="documentation",
        metric_profile="documentation-v2",
        extensions=(".md",),
        include=("docs/**",),
    )
    payload = carrier.model_dump()
    payload["relative_path"] = "docs/sample.md"
    payload["identity"] = documentation.model_dump()
    payload["measurement_digest"] = _carrier_digest(
        relative_path="docs/sample.md",
        identity=documentation,
        contract_set_digest=carrier.contract_set_digest,
        native=carrier.native,
    )
    with pytest.raises(ValidationError, match="identity must match native contracts"):
        CarrierMeasurement.model_validate(payload)

    excluded = _identity(
        carrier_id="excluded-docs",
        scope_id="docs",
        disposition="exclude",
        extensions=(".md",),
        include=("docs/**",),
    )
    with pytest.raises(ValidationError, match="classified match"):
        CarrierMeasurement.create(
            match=_match("docs/sample.md", excluded),
            contracts=_contract_set(),
            native=_native(),
        )

    forged_payload = carrier.model_dump()
    forged_payload["contract_set_digest"] = RAW_B
    forged_payload["measurement_digest"] = _carrier_digest(
        relative_path=carrier.relative_path,
        identity=carrier.identity,
        contract_set_digest=RAW_B,
        native=carrier.native,
    )
    forged = CarrierMeasurement.model_validate(forged_payload)
    with pytest.raises(ValidationError, match="contract set must match every carrier"):
        MeasurementSnapshot.from_inventory(
            inventory=_inventory((carrier.relative_path,)),
            contracts=_contract_set(),
            measurements=(forged,),
        )


def test_unknown_metric_profile_is_reported_as_stable_validation_error() -> None:
    identity = _identity(metric_profile="missing-profile")
    with pytest.raises(ValidationError, match="classified identity resolution"):
        CarrierMeasurement.create(
            match=_match(identity=identity),
            contracts=_contract_set(),
            native=_native(),
        )
