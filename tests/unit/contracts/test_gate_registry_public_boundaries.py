"""Public declaration validation and source-readiness dependencies."""

from __future__ import annotations

import hashlib
import sys
import tomllib
from operator import setitem
from typing import TYPE_CHECKING
from typing import cast

import pytest
from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import bind_gate_source_digests
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.quality.gate_composition import canonical_gate_command
from ethos.repository.policy.quality.sources import source_paths_for_gate
from ethos.repository.policy.references.commands import python_module

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from pathlib import Path


def _gate(gate_id: str, **attributes: object) -> Gate:
    return Gate.model_validate({"id": gate_id, "kind": "test", "command": (gate_id,), **attributes})


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


def test_gate_cpu_reservation_is_positive_and_only_explicit_values_bind_policy() -> None:
    for invalid in (0, -1, True):
        with pytest.raises(ValidationError):
            _gate("heavy", cpu_reservation=invalid)
    heavy = _gate("heavy", cpu_reservation=2)
    assert heavy.to_dict()["cpu_reservation"] == 2
    assert gate_policy_fields(heavy)["cpu_reservation"] == 2
    assert "cpu_reservation" not in _gate("ordinary").to_dict()
    packaged = load_gate_registry_declaration().registry()
    assert packaged["unit-architecture"].cpu_reservation == 2
    assert packaged["local-install-smoke"].cpu_reservation == 2


def test_gate_deadline_is_finite_positive_and_bound_to_policy() -> None:
    """A native execution budget is an explicit contract, not an adapter constant."""
    for invalid in (0, -1, True, float("inf")):
        with pytest.raises(ValidationError):
            _gate("bounded", timeout_seconds=invalid)
    bounded = _gate("bounded", timeout_seconds=1800)
    assert bounded.to_dict()["timeout_seconds"] == 1800
    assert gate_policy_fields(bounded)["timeout_seconds"] == 1800
    assert "timeout_seconds" not in _gate("default").to_dict()


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
    assert gate.resource_locks is not None
    assert "changed" not in gate.resource_locks
    with pytest.raises(TypeError):
        setitem(cast("MutableMapping[str, str]", gate.resource_locks), "changed", "shared")


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


@pytest.mark.parametrize("options", [("-m",), ("-B", "-I", "-m"), ("-mtools.ci.ci_projection",)])
def test_resolved_python_module_gate_binds_exact_source(options: tuple[str, ...]) -> None:
    """A direct module check cannot certify success without its selected source."""
    gate = load_gate_registry_declaration().registry(python_executable=sys.executable)[
        "github-workflow-syntax"
    ]
    command = (sys.executable, *options)
    if options[-1] == "-m":
        command = (*command, "tools.ci.ci_projection")
    gate = gate.model_copy(update={"command": command})
    path = "tools/ci/ci_projection.py"
    assert source_paths_for_gate(gate) == (path,)
    sources, gaps = bind_gate_source_digests((gate,), {path: b"first"})
    assert sources == ((gate.id, ((path, hashlib.sha256(b"first").hexdigest()),)),)
    assert gaps == ()
    changed, _ = bind_gate_source_digests((gate,), {path: b"second"})
    assert changed != sources
    assert bind_gate_source_digests((gate,), {})[1] == (
        f"gate_policy_source_missing:{gate.id}:{path}",
    )


@pytest.mark.parametrize("interpreter", ["python.exe", r"C:\runtime\python.exe", "/runtime/python"])
def test_python_module_binding_is_portable(interpreter: str) -> None:
    """The executable identity is identical for source binding and runtime admission."""
    gate = Gate(id="portable", kind="test", command=(interpreter, "-B", "-m", "tools.check"))
    assert source_paths_for_gate(gate) == ("tools/check.py",)
    command = canonical_gate_command(gate.command)
    assert python_module(command) == "tools.check"


@pytest.mark.parametrize("options", [("-m", "nox"), ("-B", "-I", "-mnox")])
def test_python_module_options_preserve_native_nox_source_binding(
    options: tuple[str, ...],
) -> None:
    """Interpreter flags do not change the source owner of a native Nox session."""
    gate = Gate(id="nox-check", kind="test", command=(sys.executable, *options, "-s", "lint"))
    assert source_paths_for_gate(gate) == ("noxfile.py", "pyproject.toml", "uv.lock")


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


@pytest.mark.parametrize(
    "binding",
    [
        "valid",
        "shared-runtime",
        "report-routing",
        "outside-session",
        "duplicate-producer",
        "missing-selection",
        "duplicate-group",
    ],
)
def test_native_output_contract_preserves_exact_producer_selection(binding: str) -> None:
    """A single Nox attempt selects concrete producers and their portable output paths."""
    command = (
        "python",
        "-m",
        "nox",
        "-s",
        "tests-3.12",
        "static",
        "--report",
        "{native_output}/nox.json",
    )
    static_sessions: tuple[str, ...] = ("static",)
    if binding == "shared-runtime":
        static_sessions = ("tests-3.12", "static")
    elif binding == "outside-session":
        static_sessions = ("unexpected",)
    elif binding == "report-routing":
        command = (*command[:-1], "{native_output}/other.json")
    outputs: list[dict[str, object]] = [
        {"path": "nox.json", "format": "nox-json", "sessions": ("tests-3.12", "static")},
        {"path": "tests.xml", "format": "junit-xml", "sessions": ("tests-3.12",)},
        {"path": "events.jsonl", "format": "pytest-jsonl", "sessions": ("tests-3.12",)},
        {"path": "coverage.xml", "format": "cobertura-xml", "sessions": ("tests-3.12",)},
        {"path": "ruff.sarif", "format": "sarif", "sessions": ("static",)},
        {
            "path": "tests-runtime.json",
            "format": "python-runtime-json",
            "configuration": ".config/quality.toml",
            "sessions": ("tests-3.12",),
            "python": "3.12",
            "dependency_groups": ("quality",),
        },
        {
            "path": "static-runtime.json",
            "format": "python-runtime-json",
            "configuration": ".config/quality.toml",
            "sessions": static_sessions,
            "python": "3.12",
            "dependency_groups": ("quality",),
        },
    ]
    if binding == "duplicate-producer":
        outputs.append(
            {
                "path": "other-static-runtime.json",
                "format": "python-runtime-json",
                "configuration": ".config/quality.toml",
                "sessions": ("static",),
                "python": "3.12",
                "dependency_groups": ("quality",),
            }
        )
    if binding == "missing-selection":
        outputs[-1].pop("dependency_groups")
    elif binding == "duplicate-group":
        outputs[-1]["dependency_groups"] = ("quality", "quality")
    payload = {
        "id": "native",
        "kind": "test",
        "command": command,
        "verification_providers": ("ethos.adapters.gates.python_quality:behavior_report",),
        "native_outputs": tuple(outputs),
    }
    if binding == "valid":
        gate = Gate.model_validate(payload)
        assert gate.native_outputs[0].sessions == ("tests-3.12", "static")
        assert ".config/quality.toml" in source_paths_for_gate(gate)
    else:
        with pytest.raises(ValidationError):
            Gate.model_validate(payload)


@pytest.mark.parametrize(
    "binding",
    [
        "valid",
        "unplaced",
        "removed-coverage",
        "removed-ruff",
        "second-report",
        "nested",
        "unsessioned",
    ],
)
def test_native_output_contract_accepts_tool_neutral_reports_without_nox(binding: str) -> None:
    """Standard reports bind to one attempt without a Nox report or a per-session bundle."""
    command: tuple[str, ...] = ("kcov", "{native_output}/kcov", "python", "-m", "pytest")
    outputs: list[dict[str, object]] = [
        {"path": "tests.xml", "format": "junit-xml", "sessions": ("scripts",)},
        {"path": "kcov/cobertura.xml", "format": "cobertura-xml", "sessions": ("scripts",)},
        {"path": "node.lcov", "format": "lcov", "sessions": ("scripts",)},
        {"path": "lint.sarif", "format": "sarif", "sessions": ("lint",)},
    ]
    if binding == "unplaced":
        command = ("python", "-m", "pytest")
    elif binding == "removed-coverage":
        outputs[1]["format"] = "coverage-xml"
    elif binding == "removed-ruff":
        outputs[3]["format"] = "ruff-json"
    elif binding == "second-report":
        outputs.extend(
            {"path": name, "format": "nox-json", "sessions": ("scripts", "lint")}
            for name in ("first.json", "second.json")
        )
    elif binding == "nested":
        outputs[2]["path"] = "kcov/cobertura.xml/node.lcov"
    elif binding == "unsessioned":
        outputs[0]["sessions"] = ()
    payload = {
        "id": "native",
        "kind": "test",
        "command": command,
        "verification_providers": ("ethos.adapters.gates.code_quality:behavior_report",),
        "native_outputs": tuple(outputs),
    }
    if binding in {"valid", "unplaced"}:
        gate = Gate.model_validate(payload)
        assert [output.format for output in gate.native_outputs] == [
            "junit-xml",
            "cobertura-xml",
            "lcov",
            "sarif",
        ]
    else:
        with pytest.raises(ValidationError):
            Gate.model_validate(payload)


_PRETTIER = (".config/checks/prettier/prettier.toml", ".config/checks/prettier/prettierignore")
_TAPLO = ".config/checks/taplo/taplo.toml"
_VALE = (
    ".config/checks/vale/vale.ini",
    ".config/checks/vale/styles/plain/concise.yml",
    ".config/checks/vale/styles/config/vocabularies/common/accept.txt",
)


@pytest.mark.parametrize(
    ("gate_id", "carriers"),
    [
        ("source-format", (*_PRETTIER, _TAPLO, ".config/checks/ruff/ruff.toml")),
        ("markdown-lint", (*_PRETTIER, ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml")),
        ("markdown-links", (".config/checks/lychee/lychee.toml",)),
        ("external-links", (".config/checks/lychee/lychee.toml",)),
        ("prose", (".config/checks/codespell/codespell.toml", *_VALE)),
        ("config-quality", (*_PRETTIER, _TAPLO, ".config/checks/yamllint/.yamllint.yaml")),
    ],
)
def test_shipped_provider_gates_bind_their_native_policy_carriers(
    gate_id: str, carriers: tuple[str, ...]
) -> None:
    """A consumed policy carrier, a Vale style or vocabulary included, binds into gate sources.

    Changing only that carrier changes the bound digests, so a proof made before it is not reused.
    """
    gate = load_gate_registry_declaration().registry()[gate_id]
    selected = source_paths_for_gate(gate, repository_paths=carriers)
    assert set(carriers) <= set(selected)
    sources = dict.fromkeys(selected, b"original")
    before = bind_gate_source_digests((gate,), sources, repository_paths=carriers)
    assert not before[1], before
    for carrier in carriers:
        changed = {**sources, carrier: b"changed"}
        assert bind_gate_source_digests((gate,), changed, repository_paths=carriers) != before
