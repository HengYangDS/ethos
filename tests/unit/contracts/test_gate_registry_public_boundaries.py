from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration

if TYPE_CHECKING:
    from pathlib import Path


def _gate(gate_id: str, *, depends_on: tuple[str, ...] = ()) -> Gate:
    return Gate(id=gate_id, kind="test", command=(gate_id,), depends_on=depends_on)


def _declaration(
    *gates: Gate,
    default: tuple[str, ...] = ("first",),
    full: tuple[str, ...] = ("first",),
) -> GateRegistryDeclaration:
    return GateRegistryDeclaration(
        id="test-registry",
        proof_sets=GateProofSets(default=default, full=full),
        gates=gates,
    )


def test_gate_registry_canonical_projection_and_proof_closure() -> None:
    declaration = _declaration(
        _gate("first"),
        _gate("second", depends_on=("first",)),
        default=("second",),
        full=("first", "second"),
    )

    registry = declaration.registry("runtime", python_executable="python-test")
    assert list(registry) == ["first", "second"]
    assert registry["first"].to_dict()["command"] == ["first"]
    assert [gate.id for gate in declaration.proof_gates(("second",))] == ["first", "second"]
    assert [gate.id for gate in declaration.proof_gates(full=True)] == ["first", "second"]


@pytest.mark.parametrize(
    "gate",
    [
        Gate.model_construct(id="none", kind="test"),
        Gate.model_construct(id="both", kind="test", command=("run",), providers=("x:y",)),
        Gate.model_construct(id="provider", kind="test", providers=("invalid",)),
        Gate.model_construct(id="provider", kind="test", providers=("ethos.owner:call",) * 2),
    ],
)
def test_gate_executor_malformed_shapes_fail_closed(gate: Gate) -> None:
    with pytest.raises(ValidationError, match="gate executor invalid"):
        Gate.model_validate(gate.model_dump())


@pytest.mark.parametrize(
    ("gates", "default", "full", "message"),
    [
        ((_gate("first"), _gate("first")), ("first",), ("first",), "duplicate gate id"),
        (
            (
                Gate(id="first", kind="test", command=("same",)),
                Gate(id="second", kind="test", command=("same",)),
            ),
            ("first",),
            ("first",),
            "duplicate gate command",
        ),
        (
            (_gate("first", depends_on=("missing",)),),
            ("first",),
            ("first",),
            "unavailable gate dependency",
        ),
        ((_gate("first"),), ("missing",), ("first",), "unknown proof gate"),
        ((_gate("first"),), ("first", "first"), ("first",), "duplicate proof gate"),
        (
            (_gate("first"), _gate("second")),
            ("first",),
            ("second",),
            "full proof set missing default",
        ),
    ],
)
def test_gate_registry_malformed_references_fail_closed(
    gates: tuple[Gate, ...], default: tuple[str, ...], full: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _declaration(*gates, default=default, full=full)


def test_gate_registry_missing_or_malformed_source_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    fallback = load_gate_registry_declaration(missing)
    assert fallback.id == "gate-registry"

    malformed = tmp_path / "gates.toml"
    malformed.write_text("gates = [\n", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_gate_registry_declaration(malformed)
