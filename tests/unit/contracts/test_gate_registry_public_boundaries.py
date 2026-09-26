"""Public declaration validation and source-readiness dependencies."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.gates import source_paths_for_gate

if TYPE_CHECKING:
    from pathlib import Path


def _gate(gate_id: str, **attributes: object) -> Gate:
    return Gate(id=gate_id, kind="test", command=(gate_id,), **attributes)


def _declaration(
    *gates: Gate,
    default: tuple[str, ...] = ("first",),
    full: tuple[str, ...] = ("first",),
) -> GateRegistryDeclaration:
    proof_sets = GateProofSets(default=default, full=full)
    return GateRegistryDeclaration(id="test-registry", proof_sets=proof_sets, gates=gates)


def test_gate_registry_canonical_projection_and_proof_closure() -> None:
    declaration = _declaration(
        _gate("first"),
        _gate("second", depends_on=("first",)),
        default=("second",),
        full=("first", "second"),
    )

    registry = declaration.registry(python_executable="python-test")
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
        Gate.model_construct(
            id="orphan-verifier",
            kind="test",
            providers=("ethos.owner:call",),
            verification_providers=("ethos.owner:check",),
        ),
        Gate.model_construct(
            id="invalid-verifier",
            kind="test",
            command=("run",),
            verification_providers=("invalid",),
        ),
    ],
)
def test_gate_executor_malformed_shapes_fail_closed(gate: Gate) -> None:
    with pytest.raises(ValidationError, match="gate executor invalid"):
        Gate.model_validate(gate.model_dump())


def test_verified_command_keeps_one_gate_and_binds_product_source() -> None:
    """The verifier is part of one command gate's policy, not another gate."""
    reference = "ethos.adapters.gates.code_quality:behavior_report"
    gate = Gate(
        id="docs-integrity",
        kind="test",
        command=("node", "tools/docs/cli.mjs", "check"),
        verification_providers=(reference,),
        profile="repository",
        tool_adapter="ethos",
    )

    assert gate.to_dict()["command"] == ["node", "tools/docs/cli.mjs", "check"]
    assert gate.to_dict()["verification_providers"] == [reference]
    assert gate_policy_fields(gate)["verification_providers"] == [reference]
    assert gate_policy_fields(gate) != gate_policy_fields(
        gate.model_copy(update={"verification_providers": ()})
    )
    assert "@ethos/adapters/gates/code_quality.py" in source_paths_for_gate(gate)


@pytest.mark.parametrize(
    ("locks", "writer", "valid"),
    [
        ({"source": "shared"}, False, True),
        ({"source": "exclusive"}, True, True),
        ({"*": "exclusive"}, True, True),
        ({}, False, True),
        ({}, True, False),
        ({"source": "shared"}, True, False),
        ({"source": "invalid"}, False, False),
        ({"source/../other": "exclusive"}, True, False),
        ({"/source": "exclusive"}, True, False),
    ],
)
def test_resource_claims_are_validated_frozen_and_symmetric(locks, writer, valid):
    if not valid:
        with pytest.raises(ValidationError):
            _gate("resource", writes_files=writer, resource_locks=locks)
        return
    gate = _gate("resource", writes_files=writer, resource_locks=locks)
    reader = _gate("reader", resource_locks={"source/child": "shared"})
    assert gate.conflicts_with(reader) == reader.conflicts_with(gate) == writer
    assert gate_policy_fields(gate)["resource_locks"] == locks
    if locks == {"source": "shared"}:
        registry = load_gate_registry_declaration().registry()
        javascript = registry["javascript-tests"]
        assert not any(
            javascript.conflicts_with(registry[name]) for name in ("unit-architecture", "build")
        )
        assert registry["javascript-tests"].conflicts_with(
            _gate("supply-writer", writes_files=True, resource_locks={"supply": "exclusive"})
        )
    locks["changed"] = "shared"
    assert "changed" not in gate.resource_locks
    with pytest.raises(TypeError):
        gate.resource_locks["changed"] = "shared"


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
    with pytest.raises(FileNotFoundError):
        load_gate_registry_declaration(tmp_path / "missing.toml")

    malformed = tmp_path / "gates.toml"
    malformed.write_text("gates = [\n", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_gate_registry_declaration(malformed)


def test_native_nox_gates_share_the_bound_interpreter() -> None:
    """Quality execution must not bootstrap or mutate its own prepared environment."""
    python = "/bound/runtime/bin/python"
    gates = load_gate_registry_declaration().registry(python_executable=python)
    nox_gates = [gate for gate in gates.values() if "nox" in gate.command]
    assert {gate.command[:3] for gate in nox_gates} == {(python, "-m", "nox")}


@pytest.mark.parametrize("version", ["0", "2", "999", "true", "1.0", '"1"'])
def test_native_gate_loader_rejects_unsupported_format(tmp_path: Path, version: str) -> None:
    """Independent native declarations reject formats before deriving a gate graph."""
    source = tmp_path / "gates.toml"
    source.write_text(
        'schema_version = 1\nid = "independent"\n'
        '[proof_sets]\ndefault = ["check"]\nfull = ["check"]\n'
        '[[gates]]\nid = "check"\nkind = "test"\ncommand = ["check"]\n',
        encoding="utf-8",
    )
    assert tuple(load_gate_registry_declaration(source).registry()) == ("check",)
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "schema_version = 1", f"schema_version = {version}"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_gate_registry_declaration(source)


def test_skill_gate_identity_names_its_responsibility() -> None:
    """Gate selection and provider ownership do not expose development generations."""
    registry = load_gate_registry_declaration().registry()
    assert registry["skills"].providers == (
        "ethos.assistants.skills.portfolio:skill_portfolio_report",
    )


def test_default_gate_declaration_ignores_caller_checkout(tmp_path: Path, monkeypatch) -> None:
    """Default interpretation belongs to the loaded source/package, never ambient CWD."""
    expected = load_gate_registry_declaration()
    candidate = tmp_path / "system" / "gates.toml"
    candidate.parent.mkdir()
    candidate.write_text('schema_version = 999\nid = "ambient"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_gate_registry_declaration() == expected
