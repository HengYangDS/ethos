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
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.adapters.mutation.proof import promotion_completeness_gaps
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.policy.gates import ADOPTER_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import ADOPTER_MISSING_CODE_CORRECTNESS_GATE
from ethos.repository.policy.gates import PRODUCT_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import adopter_code_correctness_gap
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_graph

if TYPE_CHECKING:
    from pathlib import Path

_CODE_CORRECTNESS = ("unit-architecture", "ruff", "python-types", "module-layout")


def _write_profile(root: Path, body: str) -> None:
    (root / ".ethos").mkdir(parents=True, exist_ok=True)
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


def test_adopter_without_code_correctness_declaration_gets_completeness_gap(tmp_path: Path) -> None:
    """A valid adopter profile that declares no native code-correctness gates cannot
    produce a complete proof — the executable floor stays the 11 adopter gates (so
    gate_graph does not KeyError), but adopter_code_correctness_gap surfaces the block."""
    _write_profile(tmp_path, 'profile_id = "acme"\n')

    gates = default_gate_ids(root=tmp_path)

    assert gates == ADOPTER_DEFAULT_GATE_IDS  # executable floor: no non-runnable sentinel
    assert ADOPTER_MISSING_CODE_CORRECTNESS_GATE not in gates
    assert adopter_code_correctness_gap(tmp_path) == ADOPTER_MISSING_CODE_CORRECTNESS_GATE
    # the executable floor is registry-resolvable (no KeyError)
    assert len(gate_graph(root=tmp_path).nodes) == len(ADOPTER_DEFAULT_GATE_IDS)


def test_adopter_with_code_correctness_declaration_extends_floor(tmp_path: Path) -> None:
    """Declared native gates join the executable floor (so promotion completeness
    requires them) and clear the missing-code-correctness gap."""
    _write_profile(
        tmp_path,
        'profile_id = "acme"\n[proof]\ncode_correctness_gates = ["acme-tests", "acme-lint"]\n',
    )

    gates = default_gate_ids(root=tmp_path)

    assert gates == (*ADOPTER_DEFAULT_GATE_IDS, "acme-tests", "acme-lint")
    assert adopter_code_correctness_gap(tmp_path) == ""


def test_adopter_declaration_ignores_non_list_and_empty_entries(tmp_path: Path) -> None:
    """A malformed `code_correctness_gates` (not a list) is treated as no declaration."""
    _write_profile(
        tmp_path, 'profile_id = "acme"\n[proof]\ncode_correctness_gates = "acme-tests"\n'
    )

    assert default_gate_ids(root=tmp_path) == ADOPTER_DEFAULT_GATE_IDS
    assert adopter_code_correctness_gap(tmp_path) == ADOPTER_MISSING_CODE_CORRECTNESS_GATE


def test_no_root_is_product_floor_and_no_adopter_gap() -> None:
    assert default_gate_ids(root=None) == PRODUCT_DEFAULT_GATE_IDS
    assert adopter_code_correctness_gap(None) == ""


def test_completeness_gate_blocks_adopter_without_code_correctness(tmp_path: Path) -> None:
    """End-to-end: an adopter root with no declared code-correctness gates whose proof
    covers the full adopter floor is STILL blocked by promotion_completeness_gaps — a
    contentless adopter proof must never be promotion-worthy."""
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    _write_profile(tmp_path, 'profile_id = "acme"\n')  # valid adopter, NO code-correctness
    head = "d" * 40
    runs = tuple(
        ProofRun(
            action_id=gate_id,
            command=("x",),
            exit_code=0,
            stdout="",
            stderr="",
            state="proven",
            evidence_class="test",
            verdict="passed",
            trust_bearing=True,
            diagnostics=(),
        )
        for gate_id in _promotion_required_gate_ids(tmp_path)
    )
    record_executed_proof(
        tmp_path, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()
    )

    gaps = promotion_completeness_gaps(tmp_path, head)

    assert ADOPTER_MISSING_CODE_CORRECTNESS_GATE in gaps
