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
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.gates import source_paths_for_gate
from ethos.repository.policy.quality.tool_configuration import native_gate_tools
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.policy.quality.tool_configuration import native_tool_configurations
from ethos.repository.policy.references.commands import canonical_gate_command
from ethos.repository.policy.references.commands import python_module
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration

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
        {"path": "coverage.xml", "format": "coverage-xml", "sessions": ("tests-3.12",)},
        {"path": "ruff.json", "format": "ruff-json", "sessions": ("static",)},
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
    ("provider", "tools"),
    [
        ("ethos.adapters.gates.tool:markdown_lint_report", ("prettier", "markdownlint-cli2")),
        ("ethos.adapters.gates.tool:markdown_links_report", ("lychee",)),
        ("ethos.adapters.gates.tool:external_links_report", ("lychee",)),
        ("ethos.adapters.gates.tool:prose_report", ("codespell",)),
        (
            "ethos.adapters.gates.configuration:configuration_report",
            ("taplo", "prettier", "yamllint", "python-stdlib-json", "format-selection"),
        ),
    ],
)
def test_native_provider_binds_every_consumed_configuration(
    provider: str, tools: tuple[str, ...]
) -> None:
    """Executed native policies participate in freshness and exact source identity."""
    gate = Gate.model_validate({"id": "native-policy", "kind": "test", "providers": (provider,)})
    assert native_gate_tools(gate) == tools
    locations = tuple(
        relative
        for tool in tools
        for relative in native_tool_configurations(
            (
                ".config/checks/prettier/prettier.toml",
                ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
                ".config/checks/lychee/lychee.toml",
                ".config/checks/codespell/codespell.toml",
                ".config/checks/taplo/taplo.toml",
                ".config/checks/yamllint/.yamllint.yaml",
                ".config/checks/config-quality/policy.toml",
                ".config/checks/format-selection/policy.toml",
            ),
            tool,
        )
    )
    assert len(locations) == len(tools)
    selected = source_paths_for_gate(gate, repository_paths=locations)
    assert set(locations) <= set(selected)
    for tool, location in zip(tools, locations, strict=True):
        assert native_tool_configuration(locations, tool) == location
        sources = dict.fromkeys(selected, b"original")
        before = bind_gate_source_digests((gate,), sources, repository_paths=locations)
        sources[location] = b"changed"
        assert bind_gate_source_digests((gate,), sources, repository_paths=locations) != before
        misplaced = "other/" + "/".join(location.split("/")[-2:])
        with pytest.raises(ValueError, match="native_tool_configuration_location_invalid"):
            native_tool_configuration((misplaced,), tool)
        with pytest.raises(ValueError, match="native_tool_configuration_ambiguous"):
            native_tool_configuration((location, misplaced), tool)


@pytest.mark.parametrize("selected", [("schemas", "schemas"), (True,), ("",)])
def test_gate_selection_rejects_invalid_origin_ids(selected: tuple[object, ...]) -> None:
    """Malformed origin inputs cannot normalize into an executable common gate."""
    with pytest.raises(ValueError, match="product_gate_selection_invalid"):
        compile_gate_policy(gate_ids=("schemas",), product_gate_ids=selected)


def test_product_dependency_reuses_the_same_packaged_owner() -> None:
    """One source can share a dependency without inventing a conflicting second gate."""
    policy = compile_gate_policy(gate_ids=("openspec", "schemas"), product_gate_ids=("schemas",))
    assert policy.gate_ids == ("schemas", "openspec")
    assert policy.product_gate_ids == ("schemas",)
    assert policy.gaps == ()


@pytest.mark.parametrize("requested", [("native",), ("schemas",), ("native", "schemas")])
def test_gate_composition_retains_native_owner_and_exact_provider_sources(
    tmp_path: Path, requested: tuple[str, ...]
) -> None:
    """One selection preserves the target floor and binds only requested product providers."""
    native = Gate(
        id="native",
        kind="test",
        command=("tools/check.py",),
        verification_providers=("ethos.adapters.gates.python_quality:behavior_report",),
    )
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="target",
            proof=ProofPolicy(
                code_correctness_gates=("native",),
                code_correctness_map={"behavior": "native", "static-analysis": "native"},
                gates=(native,),
            ),
        ),
    )
    materials = {
        "tools/check.py": b"print('target check')\n",
        "@ethos/adapters/gates/python_quality.py": b"native verification\n",
        "@ethos/repository/policy/schema.py": b"installed schema provider\n",
    }
    baseline = compile_gate_policy(
        profile=profile, source_materials=materials, repository_python="python", full=True
    )
    selected = compile_gate_policy(
        profile=profile,
        source_materials=materials,
        repository_python="python",
        gate_ids=requested,
        product_gate_ids=tuple(name for name in requested if name == "schemas"),
    )
    assert selected.profile is profile
    assert selected.declaration == baseline.declaration
    assert selected.projection["owner"] == baseline.projection["owner"]
    assert set(selected.gate_ids) == set(requested)
    assert set(selected.registry) == {"native"}
    executed = {gate.id: gate for gate in selected.gates}
    sources = dict(selected.sources)
    for name in requested:
        expected = (
            ("tools/check.py", "@ethos/adapters/gates/python_quality.py")
            if name == "native"
            else ("@ethos/repository/policy/schema.py",)
        )
        assert dict(sources[name]) == {
            path: hashlib.sha256(materials[path]).hexdigest() for path in expected
        }
    if "schemas" in requested:
        assert executed["schemas"].profile == "repository"
        assert executed["schemas"].tool_adapter == "ethos"
    if requested == ("schemas",):
        assert "quality_obligation_unproven:behavior" in selected.gaps
    else:
        assert selected.gaps == baseline.gaps
