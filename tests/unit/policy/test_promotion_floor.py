"""Promotion completeness floor — product vs adopter, and the profile-downgrade guard.

The completeness floor `default_gate_ids` picks the gate set a promotion proof must
cover. A live illegitimate-promotion hole let ANY `.ethos/profile.toml` (0-byte,
invalid, or the product repo's own) downgrade the 19-gate product floor to the 11-gate
adopter floor, dropping every code-correctness gate with no forgery. These tests pin
the hardened rule: the adopter floor activates ONLY for a valid profile on a non-product
root, and an adopter that declares no native code-correctness gates cannot produce a
complete proof.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.proof import promotion_completeness_gaps
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.policy.gates import ADOPTER_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import ADOPTER_MISSING_CODE_CORRECTNESS_GATE
from ethos.repository.policy.gates import PRODUCT_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import _adopter_gate_overlay
from ethos.repository.policy.gates import _code_correctness_axis_vocab
from ethos.repository.policy.gates import _code_correctness_map
from ethos.repository.policy.gates import _command_is_degenerate
from ethos.repository.policy.gates import _product_gate_registry
from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import adopter_gate_descriptor_gaps
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_graph
from ethos.repository.policy.gates import gate_registry
from ethos_core.contracts.gates import GateDescriptor

if TYPE_CHECKING:
    from pathlib import Path

_CODE_CORRECTNESS = ("unit-architecture", "ruff", "python-types", "module-layout")


def _write_profile(root: Path, body: str) -> None:
    (root / ".ethos").mkdir(parents=True, exist_ok=True)
    if "[openspec]" not in body:
        body += '\n[openspec]\nmaterial_paths = [".ethos/profile.toml"]\n'
    (root / ".ethos" / "profile.toml").write_text(body, encoding="utf-8")


def test_no_profile_uses_full_product_code_correctness_floor(tmp_path: Path) -> None:
    gates = default_gate_ids(root=tmp_path)
    assert gates == PRODUCT_DEFAULT_GATE_IDS
    for gate in _CODE_CORRECTNESS:
        assert gate in gates


def test_invalid_profile_does_not_downgrade_the_floor(tmp_path: Path) -> None:
    """An unparseable profile must NOT be treated as an adopter (the downgrade hole)."""
    _write_profile(tmp_path, "%%% not toml %%%")

    gates = default_gate_ids(root=tmp_path)

    assert gates == PRODUCT_DEFAULT_GATE_IDS
    assert "ruff" in gates
    assert "python-types" in gates


def test_product_root_never_downgrades_even_with_a_profile(tmp_path: Path) -> None:
    """The product repo (its two anchor files) keeps the product floor even if it grows
    a profile — it must never be demoted to the adopter floor."""
    (tmp_path / "packages" / "ethos").mkdir(parents=True)
    (tmp_path / "packages" / "ethos" / "README.md").write_text("# ethos", encoding="utf-8")
    (tmp_path / "system" / "schemas" / "kernel").mkdir(parents=True)
    _write_profile(tmp_path, 'profile_id = "whatever"\n')

    assert default_gate_ids(root=tmp_path) == PRODUCT_DEFAULT_GATE_IDS


def test_adopter_without_code_correctness_declaration_gets_completeness_gap(
    tmp_path: Path,
) -> None:
    """A valid adopter profile that declares no native code-correctness gates cannot
    produce a complete proof — the executable floor stays empty until native gates are
    declared, while adopter_code_correctness_gap surfaces the block."""
    _write_profile(tmp_path, 'profile_id = "acme"\n')

    gates = default_gate_ids(root=tmp_path)

    assert gates == ADOPTER_DEFAULT_GATE_IDS  # executable floor: no non-runnable sentinel
    assert ADOPTER_MISSING_CODE_CORRECTNESS_GATE not in gates
    assert adopter_code_correctness_gaps(tmp_path) == (ADOPTER_MISSING_CODE_CORRECTNESS_GATE,)
    # the executable floor is registry-resolvable (no KeyError)
    assert len(gate_graph(root=tmp_path).nodes) == len(ADOPTER_DEFAULT_GATE_IDS)


def test_adopter_with_code_correctness_declaration_extends_floor(
    tmp_path: Path,
) -> None:
    """ID-only native gates cannot silently masquerade as executable descriptors."""
    _write_profile(
        tmp_path,
        'profile_id = "acme"\n[proof]\ncode_correctness_gates = ["acme-tests", "acme-lint"]\n',
    )

    gates = default_gate_ids(root=tmp_path)

    assert gates == (*ADOPTER_DEFAULT_GATE_IDS, "acme-tests", "acme-lint")
    # Declaring gate ids is no longer sufficient: without a [proof.code_correctness_map]
    # attributing gates to the required axes, both axes are unmapped (Tier 1.2).
    assert adopter_code_correctness_gaps(tmp_path) == (
        "adopter_code_correctness_axis_unmapped:behavior",
        "adopter_code_correctness_axis_unmapped:static-analysis",
    )
    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_gate_descriptor_missing:acme-tests",
        "adopter_gate_descriptor_missing:acme-lint",
    )
    graph = gate_graph(root=tmp_path)
    assert graph.validate().gaps == adopter_gate_descriptor_gaps(tmp_path)
    assert [node.id for node in graph.nodes] == list(ADOPTER_DEFAULT_GATE_IDS)


def test_adopter_gate_descriptors_extend_runtime_registry_and_graph(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-tests", "acme-lint"]

[[proof.gates]]
id = "acme-tests"
kind = "quality"
command = ["uv", "run", "pytest"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"

[[proof.gates]]
id = "acme-lint"
kind = "quality"
command = ["uv", "run", "ruff", "check", "."]
depends_on = ["acme-tests"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"
""",
    )

    registry = gate_registry(root=tmp_path)
    graph = gate_graph(root=tmp_path)

    assert adopter_gate_descriptor_gaps(tmp_path) == ()
    assert registry["acme-tests"].command == ("uv", "run", "pytest")
    assert registry["acme-tests"].profile == "adopter"
    assert registry["acme-lint"].depends_on == ("acme-tests",)
    assert graph.validate().ok is True
    ordered = [node.id for node in graph.ordered_nodes()]
    assert {"acme-tests", "acme-lint"} <= set(ordered)
    assert ordered.index("acme-tests") < ordered.index("acme-lint")


def test_invalid_gate_descriptor_invalidates_profile(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"
[proof]
code_correctness_gates = ["acme-tests"]
[[proof.gates]]
id = "acme-tests"
kind = "quality"
""",
    )

    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_profile_invalid:.ethos/profile.toml",
    )


def test_adopter_gate_descriptor_cannot_override_product_gate(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"
[proof]
code_correctness_gates = ["claims"]
[[proof.gates]]
id = "claims"
kind = "quality"
command = ["/bin/true"]
""",
    )

    assert adopter_gate_descriptor_gaps(tmp_path) == ("adopter_gate_descriptor_conflict:claims",)
    assert gate_registry(root=tmp_path)["claims"].command != ("/bin/true",)


def test_adopter_gate_overlay_rejects_duplicate_typed_descriptors(tmp_path: Path) -> None:

    first = GateDescriptor(
        id="duplicate",
        kind="quality",
        command=("first",),
        profile="adopter",
    )
    second = first.model_copy(update={"command": ("second",)})
    profile = SimpleNamespace(
        declaration=SimpleNamespace(
            proof=SimpleNamespace(gates=(first, second), code_correctness_gates=())
        )
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "ethos.repository.policy.gates._adopter_profile_active", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        "ethos.repository.policy.gates.load_repository_profile", lambda *_args, **_kwargs: profile
    )
    try:
        _, gaps = _adopter_gate_overlay(tmp_path, _product_gate_registry())
    finally:
        monkeypatch.undo()

    assert gaps == ("adopter_gate_descriptor_duplicate:duplicate",)


def test_profile_contract_rejects_non_adopter_gate_and_duplicates(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"
[proof]
code_correctness_gates = ["acme-tests"]
[[proof.gates]]
id = "acme-tests"
kind = "quality"
command = ["uv", "run", "pytest"]
profile = "product"
[[proof.gates]]
id = "duplicate"
kind = "quality"
command = ["first"]
[[proof.gates]]
id = "duplicate"
kind = "quality"
command = ["second"]
""",
    )

    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_profile_invalid:.ethos/profile.toml",
    )


def test_adopter_gate_descriptors_must_be_an_array(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"
[proof]
code_correctness_gates = ["acme-tests"]
gates = "not-a-list"
""",
    )

    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_profile_invalid:.ethos/profile.toml",
    )


def test_adopter_gate_descriptor_entries_must_be_tables(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        """profile_id = "acme"
[proof]
code_correctness_gates = ["acme-tests"]
gates = ["not-a-table"]
""",
    )

    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_profile_invalid:.ethos/profile.toml",
    )


def test_explicit_unknown_gate_becomes_graph_validation_gap() -> None:
    graph = gate_graph(("not-registered",))

    assert graph.nodes == ()
    assert graph.validate().gaps == ("unknown_gate:not-registered",)


def test_adopter_declaration_rejects_non_array_gate_ids(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        'profile_id = "acme"\n[proof]\ncode_correctness_gates = "acme-tests"\n',
    )

    assert default_gate_ids(root=tmp_path) == PRODUCT_DEFAULT_GATE_IDS
    assert adopter_gate_descriptor_gaps(tmp_path) == (
        "adopter_profile_invalid:.ethos/profile.toml",
    )


def test_no_root_is_product_floor_and_no_adopter_gap() -> None:
    assert default_gate_ids(root=None) == PRODUCT_DEFAULT_GATE_IDS
    assert adopter_code_correctness_gaps(None) == ()


def test_completeness_gate_blocks_adopter_without_code_correctness(
    tmp_path: Path,
) -> None:
    """End-to-end: an adopter root with no declared code-correctness gates whose proof
    covers the full adopter floor is STILL blocked by promotion_completeness_gaps — a
    contentless adopter proof must never be promotion-worthy."""
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    _write_profile(tmp_path, 'profile_id = "acme"\n')  # valid adopter, NO code-correctness
    head = "d" * 40
    runs = (
        ProofRun(
            action_id="native-check",
            command=("x",),
            exit_code=0,
            stdout="",
            stderr="",
            state="proven",
            evidence_class="test",
            verdict="passed",
            trust_bearing=True,
            diagnostics=(),
        ),
    )
    record_executed_proof(
        tmp_path, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()
    )

    gaps = promotion_completeness_gaps(tmp_path, head)

    assert ADOPTER_MISSING_CODE_CORRECTNESS_GATE in gaps


# ── Tier 1.2: code-correctness EQUIVALENCE (map + per-axis trust/evidence floor) ──

_LEGIT_ADOPTER_PROFILE = """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-behavior", "acme-static"]

[proof.code_correctness_map]
behavior = "acme-behavior"
static-analysis = { gate = "acme-static" }

[[proof.gates]]
id = "acme-behavior"
kind = "test"
command = ["cargo", "test", "--all"]
dimensions = ["test", "coverage"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"

[[proof.gates]]
id = "acme-static"
kind = "typing"
command = ["cargo", "clippy", "--", "-Dwarnings"]
dimensions = ["static-analysis", "lint"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
"""


def test_adopter_with_mapped_equivalent_gates_passes_different_toolchain(tmp_path: Path) -> None:
    """A legitimate adopter on a totally different stack (Rust: cargo test + clippy) that
    maps both axes to qualifying native gates has NO code-correctness gap — no tool name
    is hardcoded; attribution is by declared kind/dimensions."""
    _write_profile(tmp_path, _LEGIT_ADOPTER_PROFILE)

    assert adopter_code_correctness_gaps(tmp_path) == ()


def test_adopter_monolithic_stack_may_waive_static_with_reason(tmp_path: Path) -> None:
    """A monolithic-correctness stack (types enforced by the compiler inside the behavior
    gate) WAIVES static-analysis with an explicit reason — no false-reject."""
    _write_profile(
        tmp_path,
        """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-behavior"]

[proof.code_correctness_map]
behavior = "acme-behavior"
static-analysis = { waived = "types enforced by the compiler inside cargo test" }

[[proof.gates]]
id = "acme-behavior"
kind = "test"
command = ["cargo", "test", "--all"]
dimensions = ["test", "coverage"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"
""",
    )

    assert adopter_code_correctness_gaps(tmp_path) == ()


def test_adopter_extensible_axis_vocabulary_recognizes_native_tokens(tmp_path: Path) -> None:
    """An adopter extends an axis's recognized dimension tokens under
    [proof.code_correctness_axes]; a gate declaring only that token then attributes."""
    _write_profile(
        tmp_path,
        """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-fuzz", "acme-static"]

[proof.code_correctness_map]
behavior = "acme-fuzz"
static-analysis = "acme-static"

[proof.code_correctness_axes]
behavior = ["fuzz"]

[[proof.gates]]
id = "acme-fuzz"
kind = "quality"
command = ["cargo", "fuzz", "run", "target"]
dimensions = ["fuzz"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"

[[proof.gates]]
id = "acme-static"
kind = "typing"
command = ["cargo", "clippy"]
dimensions = ["static-analysis"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
""",
    )

    assert adopter_code_correctness_gaps(tmp_path) == ()


def _wash_profile(behavior_gate: str) -> str:
    """A base profile whose static axis is legit; the behavior gate is the wash variable."""
    return f"""profile_id = "acme"

[proof]
code_correctness_gates = ["acme-behavior", "acme-static"]

[proof.code_correctness_map]
behavior = "acme-behavior"
static-analysis = "acme-static"

[[proof.gates]]
{behavior_gate}

[[proof.gates]]
id = "acme-static"
kind = "typing"
command = ["cargo", "clippy"]
dimensions = ["static-analysis"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
"""


@pytest.mark.parametrize(
    "behavior_gate",
    [
        'id = "acme-behavior"\nkind = "test"\ncommand = ["echo", "ok"]\n'
        'dimensions = ["test"]\nexecution_mode = "subprocess"\n'
        'evidence_class = "proof"\ntrust_bearing = true\ntool_adapter = "repository-native"',
        'id = "acme-behavior"\nkind = "test"\ncommand = ["cargo", "test"]\n'
        'dimensions = ["test"]\nexecution_mode = "subprocess"\n'
        'evidence_class = "proof"\ntrust_bearing = false\ntool_adapter = "repository-native"',
        'id = "acme-behavior"\nkind = "test"\ncommand = ["cargo", "test"]\n'
        'dimensions = ["test"]\nexecution_mode = "subprocess"\n'
        'evidence_class = "diagnostic"\ntrust_bearing = true\ntool_adapter = "repository-native"',
        'id = "acme-behavior"\nkind = "lint"\ncommand = ["cargo", "clippy"]\n'
        'dimensions = ["lint"]\nexecution_mode = "subprocess"\n'
        'evidence_class = "proof"\ntrust_bearing = true\ntool_adapter = "repository-native"',
    ],
    ids=["noop-command", "non-trust-bearing", "diagnostic-evidence", "wrong-axis-attribution"],
)
def test_wash_behavior_gate_is_rejected(tmp_path: Path, behavior_gate: str) -> None:
    """Behavior gates must be executable, trust-bearing proof for the behavior axis."""
    _write_profile(
        tmp_path,
        _wash_profile(behavior_gate),
    )
    assert "adopter_code_correctness_axis_unbacked:behavior:acme-behavior" in (
        adopter_code_correctness_gaps(tmp_path)
    )


def test_wash_single_gate_reused_across_axes_is_rejected(tmp_path: Path) -> None:
    """One gate claiming both axes (dimensions=[test,static-analysis]) is rejected: axes
    must be backed by DISTINCT gates."""
    _write_profile(
        tmp_path,
        """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-all"]

[proof.code_correctness_map]
behavior = "acme-all"
static-analysis = "acme-all"

[[proof.gates]]
id = "acme-all"
kind = "test"
command = ["make", "verify"]
dimensions = ["test", "static-analysis"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"
""",
    )
    gaps = adopter_code_correctness_gaps(tmp_path)
    assert "adopter_code_correctness_axis_gate_reused:static-analysis:acme-all" in gaps


def test_wash_borrowed_product_gate_is_rejected(tmp_path: Path) -> None:
    """Mapping an axis to a PRODUCT gate id (not adopter-authored) does not satisfy it —
    the adopter must author its own gate."""
    _write_profile(
        tmp_path,
        """profile_id = "acme"

[proof]
code_correctness_gates = ["acme-static"]

[proof.code_correctness_map]
behavior = "unit-architecture"
static-analysis = "acme-static"

[[proof.gates]]
id = "acme-static"
kind = "typing"
command = ["cargo", "clippy"]
dimensions = ["static-analysis"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
""",
    )
    gaps = adopter_code_correctness_gaps(tmp_path)
    assert "adopter_code_correctness_axis_gate_missing:behavior:unit-architecture" in gaps


def test_command_is_degenerate_edge_cases() -> None:
    assert _command_is_degenerate(()) is True  # empty command
    assert _command_is_degenerate(("/bin/echo",)) is True  # no-op head by basename
    assert _command_is_degenerate(("cargo", "test")) is False


def test_axis_vocab_extends_known_axes() -> None:
    profile = SimpleNamespace(
        declaration=SimpleNamespace(
            proof=SimpleNamespace(
                code_correctness_axes={"behavior": ("fuzz",), "not-an-axis": ("x",)}
            )
        )
    )
    vocab = _code_correctness_axis_vocab(profile)
    assert "fuzz" in vocab["behavior"]
    assert "not-an-axis" not in vocab


def test_code_correctness_map_ignores_unusable_entries() -> None:
    profile = SimpleNamespace(
        declaration=SimpleNamespace(
            proof=SimpleNamespace(
                code_correctness_map={
                    "behavior": 123,
                    "static-analysis": {"waived": "   "},
                }
            )
        )
    )
    assert _code_correctness_map(profile) == {}

    assert _code_correctness_map(SimpleNamespace(declaration=None)) == {}
