"""Falsify source assurance through the immutable-tree projection boundary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ethos.repository.policy.projections import validate_projection_assurance
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.projection.export_terminal_architecture import export_projection_input

ROOT = Path(__file__).resolve().parents[3]
DECLARATION = "system/projections/terminal-architecture/declaration.json"


def _selected_source(tmp_path: Path) -> tuple[Path, dict]:
    """Copy exact projection inputs, not the repository or its runtime."""
    root = init_git_repo(tmp_path / "source")
    declaration = json.loads((ROOT / DECLARATION).read_text())
    paths = [
        DECLARATION,
        "src/ethos/repository/policy/projections.py",
        *declaration["documents"].values(),
        *(row["path"] for row in declaration["sources"]),
    ]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return root, declaration


def _commit(root: Path) -> None:
    """Freeze the candidate bytes before the actual exporter reads them."""
    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture projection input")


def test_public_export_rejects_undefined_quality_check_ids(tmp_path: Path) -> None:
    """Successful hashing cannot make an undefined required criterion valid."""
    root, declaration = _selected_source(tmp_path)
    quality = root / declaration["documents"]["quality_contract"]
    quality.write_text(
        json.dumps(
            {
                "schema": "ethos.terminal-visual-quality.v3",
                "hard_gates": {"semantic": {"required_semantic_check_ids": ["R01"]}},
            }
        )
    )
    _commit(root)
    with pytest.raises(ValueError, match="projection_assurance"):
        export_projection_input(root=root)


@pytest.mark.parametrize("defect", ["empty", "duplicate", "unknown-source", "missing-owner"])
def test_public_export_rejects_unsettled_graph_obligation(tmp_path: Path, defect: str) -> None:
    """The public input cannot carry an orphan, ambiguous or empty proposition."""
    root, declaration = _selected_source(tmp_path)
    path = root / declaration["documents"]["semantic_graph"]
    graph = json.loads(path.read_text())
    invariant = graph["invariants"][0]
    if defect == "empty":
        invariant["statement"] = ""
    elif defect == "duplicate":
        graph["invariants"].append(invariant.copy())
    elif defect == "unknown-source":
        invariant["source_ids"] = ["not-a-source"]
    else:
        graph["invariants"].append(
            {
                "id": "unsettled-obligation",
                "statement": "A required new invariant needs an acceptance owner.",
                "required_visible": False,
                "source_ids": ["product_contract"],
            }
        )
    path.write_text(json.dumps(graph))
    quality = (root / declaration["documents"]["quality_contract"]).read_text()
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(quality, graph, graph["sources"])
    _commit(root)
    with pytest.raises(ValueError, match="projection_assurance"):
        export_projection_input(root=root)


def test_selected_source_remains_stdlib_exportable(tmp_path: Path) -> None:
    """Consumers execute the selected exporter without editable checkout imports."""
    root, _ = _selected_source(tmp_path)
    _commit(root)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-S",
            "-c",
            (ROOT / "tools/projection/export_terminal_architecture.py").read_text(),
            "--root",
            str(root),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    exported = json.loads(result.stdout)
    assert exported == export_projection_input(root=root)
    Draft202012Validator(
        json.loads((ROOT / "system/schemas/projection-input.schema.json").read_text())
    ).validate(exported)
    assert (
        exported["documents"]["copy"]["maturity_notice"]
        == "Target architecture, not a claim of current implementation."
    )
    nodes = exported["semantics"]["nodes"]
    for identity in (
        "problem_observation",
        "research",
        "intent_alignment",
        "repository_norms",
        "capability_contract",
        "collaboration_selection",
        "use_outcome",
        "feedback_learning",
        "adoption_exit",
        "skills",
        "independent_verifier",
        "brownfield_repo",
        "greenfield_repo",
    ):
        assert nodes[identity]["attributes"]["required_visible"]
    assert "transient" in nodes["commitment_n"]["attributes"]["semantics"].lower()
    assert exported["authority"]["effect_authority"] is False
    relation = next(
        row
        for row in exported["semantics"]["relations"]
        if row["id"] == "candidate-state-to-independent"
    )
    assert relation["attributes"]["guard"] == "committed_action_policy_selection"
    assert "independent_verification" in relation["provenance"]


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("assurance", "faithfulness", "media"), {}),
        (("assurance", "faithfulness", "media", "scoped_view"), None),
        (("assurance", "faithfulness", "media", "scoped_view", "states"), []),
        (("assurance", "semantic_families", "semantic_identity", "applicability"), None),
        (("assurance", "evidence_binding", "required"), ["verdict_and_missing_obligations"]),
        (("assurance", "principle_review", "source_sections"), {"product_contract": ["x"]}),
        (("assurance", "faithfulness", "review_boundary"), "author_report"),
        (("assurance", "predecessor", "absent"), "qualified"),
        (("assurance", "predecessor", "unknown"), "absolute_acceptance_without_comparison"),
        (("assurance", "predecessor", "candidate_policy"), "candidate_self_approval"),
        (("assurance", "evidence_binding", "missing"), "PASS"),
        (("assurance", "evidence_binding", "declaration_validation"), "acceptance"),
        (("assurance", "silent_override"), True),
        (("assurance", "semantic_families", "semantic_identity", "invariants"), ["unknown"]),
        (("assurance", "semantic_families", "semantic_identity", "scope"), ""),
        (("assurance", "semantic_families", "semantic_identity", "evidence"), []),
        (("assurance", "semantic_families", "semantic_identity", "reject_when"), []),
        (("assurance", "semantic_families", "semantic_identity", "source_ids"), ["axioms"]),
        (("hard_gates", "semantic", "required_semantic_check_ids"), ["R01"]),
    ],
)
def test_export_rejects_missing_or_amplified_assurance_boundary(
    tmp_path: Path, path: tuple[str, ...], replacement: object
) -> None:
    """Incomplete evidence and unknown prestate cannot be normalized to success."""
    root, declaration = _selected_source(tmp_path)
    file = root / declaration["documents"]["quality_contract"]
    quality = json.loads(file.read_text())
    parent = quality
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    file.write_text(json.dumps(quality))
    graph = json.loads((root / declaration["documents"]["semantic_graph"]).read_text())
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(json.dumps(quality), graph, graph["sources"])
    _commit(root)
    with pytest.raises(ValueError, match="projection_assurance"):
        export_projection_input(root=root)


@pytest.mark.parametrize(
    "encoded",
    ["{", "null", "[]", '{"schema":"ethos.terminal-visual-quality.v99"}'],
)
def test_invalid_contract_is_not_a_valid_observation(encoded: str) -> None:
    """Unknown input language or shape cannot quietly remove required checks."""
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(encoded, {}, {})


def test_duplicate_json_member_does_not_replace_an_obligation() -> None:
    """Last-key-wins decoding cannot erase an earlier contradictory declaration."""
    directory = ROOT / "system/projections/terminal-architecture"
    graph = json.loads((directory / "semantic-graph.json").read_text())
    raw = (directory / "quality-contract.json").read_text()
    duplicate = raw.replace('"assurance": {', '"assurance": null, "assurance": {', 1)
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(duplicate, graph, graph["sources"])


def test_valid_multi_plane_evidence_is_not_a_second_proposition_owner() -> None:
    """One obligation may need multiple explicit evidence planes and view states."""
    directory = ROOT / "system/projections/terminal-architecture"
    graph = json.loads((directory / "semantic-graph.json").read_text())
    quality = json.loads((directory / "quality-contract.json").read_text())
    family = quality["assurance"]["semantic_families"]["semantic_identity"]
    family["evidence"].append("An independent review across an additional declared output medium.")
    validate_projection_assurance(json.dumps(quality), graph, graph["sources"])


@pytest.mark.parametrize("defect", ["second-owner", "repeated-reference", "missing-family"])
def test_proposition_ownership_is_complete_and_singular(defect: str) -> None:
    """Multiple evidence observations never justify multiple obligation definitions."""
    directory = ROOT / "system/projections/terminal-architecture"
    graph = json.loads((directory / "semantic-graph.json").read_text())
    quality = json.loads((directory / "quality-contract.json").read_text())
    families = quality["assurance"]["semantic_families"]
    family = families["semantic_identity"]
    if defect == "second-owner":
        families["second"] = family
    elif defect == "repeated-reference":
        family["invariants"].append(family["invariants"][0])
    else:
        del families["semantic_identity"]
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(json.dumps(quality), graph, graph["sources"])


def test_non_json_constant_cannot_enter_the_quality_contract() -> None:
    """JSON's closed value domain is not extended by Python's permissive decoder."""
    directory = ROOT / "system/projections/terminal-architecture"
    graph = json.loads((directory / "semantic-graph.json").read_text())
    raw = (directory / "quality-contract.json").read_text()
    raw = raw.replace('"width": 1600', '"width": NaN', 1)
    with pytest.raises(ValueError, match="projection_assurance"):
        validate_projection_assurance(raw, graph, graph["sources"])


def test_new_exporter_reports_selected_owner_contract_mismatch(tmp_path: Path) -> None:
    """A newer executable cannot mistake an incompatible selected owner for valid input."""
    root, _ = _selected_source(tmp_path)
    path = root / "src/ethos/repository/policy/projections.py"
    path.write_text(path.read_text() + "\ndel validate_projection_assurance\n")
    _commit(root)
    with pytest.raises(ValueError, match="projection_assurance_owner_missing"):
        export_projection_input(root=root)
