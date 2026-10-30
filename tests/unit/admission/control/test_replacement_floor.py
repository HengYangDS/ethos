"""Report the quality floor a control replacement changes without implicit providers."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.admission.control.replacement as replacement
import ethos.adapters.admission.evidence.external as evidence
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.proof import seed_executed_proof
from tests.unit.admission.control.support import control_change
from tests.unit.admission.control.support import control_report

if TYPE_CHECKING:
    from pathlib import Path


def test_changed_gate_reports_floor_without_implicit_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed gate needs explicit selection, not an undeclared host provider."""
    candidate, accepted, _head = control_change(tmp_path, mode="disabled")
    registry = candidate / ".ethos/fixture-proof.toml"
    payload = tomllib.loads(registry.read_text())
    old = payload["proof_sets"]["default"][0]
    selected = next(gate for gate in payload["gates"] if gate["id"] == old)
    selected["command"] = ["git", "--version"]
    head = commit_fixture_file(
        candidate, ".ethos/fixture-proof.toml", tomli_w.dumps(payload), "change proof floor"
    )
    seed_executed_proof(candidate, head)
    monkeypatch.setattr(
        evidence,
        "load_independent_verification_provider",
        lambda _path: pytest.fail("disabled policy must not inspect host configuration"),
    )
    report = control_report(candidate, accepted, head)
    assert report["verdict"] == "pass", report
    assert report["required_gaps"] == []
    assert report["independent_verification"]["state"] == "disabled"
    assert report["mints_authority"] is False
    assert old in report["subject"]["verification_floor"]["changed_obligations"]


def test_removed_gate_verifier_cannot_keep_the_same_command_identity(tmp_path: Path) -> None:
    """Removing verification is a control replacement even when argv is unchanged."""
    candidate, _accepted, _head = control_change(tmp_path, mode="disabled")
    path = ".ethos/fixture-proof.toml"
    payload = tomllib.loads((candidate / path).read_text(encoding="utf-8"))
    old = payload["proof_sets"]["default"][0]
    gate = next(item for item in payload["gates"] if item["id"] == old)
    gate["verification_providers"] = ["ethos.adapters.gates.code_quality:behavior_report"]
    prior = commit_fixture_file(candidate, path, tomli_w.dumps(payload), "retain verifier")
    del gate["verification_providers"]
    head = commit_fixture_file(candidate, path, tomli_w.dumps(payload), "remove verifier")
    seed_executed_proof(candidate, head)

    report = control_report(candidate, prior, head)

    assert report["verdict"] == "pass", report
    assert report["required_gaps"] == []
    assert old in report["subject"]["verification_floor"]["changed_obligations"]


def test_axis_remapping_changes_the_floor_without_changing_gate_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed quality mapping needs review; a capacity hint alone does not."""
    gates = (
        Gate(id="first", kind="test", command=("git", "--version")),
        Gate(id="second", kind="test", command=("git", "status")),
        Gate(id="static", kind="lint", command=("git", "diff")),
    )
    names = tuple(gate.id for gate in gates)
    declaration = GateRegistryDeclaration(
        id="quality", proof_sets=GateProofSets(default=names, full=names), gates=gates
    )

    def selected(behavior: str, candidates: tuple[Gate, ...] = gates) -> ResolvedGatePolicy:
        profile = RepositoryProfile(
            root=tmp_path,
            exists=True,
            declaration=RepositoryProfileDeclaration(
                profile_id="quality",
                proof=ProofPolicy(
                    code_correctness_gates=names,
                    code_correctness_map={"behavior": behavior, "static-analysis": "static"},
                    gates=candidates,
                ),
            ),
        )
        return ResolvedGatePolicy(
            declaration=declaration,
            profile=profile,
            gates=candidates,
            repository_paths=("src/app.py",),
        )

    candidate, accepted, head = control_change(tmp_path, mode="disabled")
    seed_executed_proof(candidate, head)
    prior = selected("first")

    def report(after: ResolvedGatePolicy) -> dict[str, object]:
        monkeypatch.setattr(
            replacement,
            "resolve_gate_policy",
            lambda _root, *, tree_ref, full: prior if tree_ref == accepted and full else after,
        )
        return control_report(candidate, accepted, head)

    changed = report(selected("second"))
    assert changed["verdict"] == "pass", changed
    assert changed["required_gaps"] == []
    changed_subject = changed["subject"]
    assert isinstance(changed_subject, dict)
    changed_floor = changed_subject["verification_floor"]
    assert isinstance(changed_floor, dict)
    obligations = changed_floor["changed_obligations"]
    assert isinstance(obligations, list)
    assert "quality-axis:behavior" in obligations
    capacity = tuple(gate.model_copy(update={"cpu_reservation": 2}) for gate in gates)
    unchanged = report(selected("first", capacity))
    assert unchanged["verdict"] == "pass", unchanged
    unchanged_subject = unchanged["subject"]
    assert isinstance(unchanged_subject, dict)
    assert "verification_floor" not in unchanged_subject
    roles = ResolvedGatePolicy(
        declaration=prior.declaration,
        profile=prior.profile,
        gates=prior.gates,
        repository_paths=("src/app.py",),
        carrier_roles=(("src/app.py", "snapshot"),),
    )
    changed_roles = report(roles)
    assert isinstance(changed_roles["subject"], dict)
    assert (
        "quality_carrier_roles:src/app.py"
        in changed_roles["subject"]["verification_floor"]["changed_obligations"]
    )


@pytest.mark.parametrize(
    ("locations", "expected_gap"),
    [
        ((".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",), ""),
        ((".config/checks/markdownlint-cli2/.markdownlint-cli2.jsonc",), "location_invalid"),
        ((".markdownlint-cli2.yaml",), "location_invalid"),
        (
            (
                ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
                ".config/checks/markdownlint-cli2/.markdownlint-cli2.jsonc",
            ),
            "ambiguous",
        ),
    ],
)
def test_predecessor_configuration_is_observed_without_admitting_candidate_drift(
    tmp_path: Path, locations: tuple[str, ...], expected_gap: str
) -> None:
    """Observe the historical carrier gap; only the strictly valid successor is verified."""
    candidate, _accepted, _head = control_change(tmp_path)
    legacy = ".config/checks/markdownlint-cli2/.markdownlint-cli2.jsonc"
    content = "[rules]\nMD013 = false\n"
    accepted = commit_fixture_file(candidate, legacy, content, "historical native configuration")
    (candidate / legacy).unlink()
    for location in locations:
        path = candidate / location
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rules:\n  MD013: false\n", encoding="utf-8")
    git(candidate, "add", "-A")
    head = commit_fixture(candidate, "successor native configuration")
    if not expected_gap:
        seed_executed_proof(candidate, head)
    report = control_report(candidate, accepted, head)
    if expected_gap:
        assert report["verdict"] == "block", report
        assert any(
            f"native_tool_configuration_{expected_gap}:markdownlint-cli2" in gap
            for gap in report["required_gaps"]
        )
        assert report["verification_request"] == report["independent_verification"] == {}
        return
    assert (report["verdict"], report["required_gaps"]) == (
        "unknown",
        ["independent_verification_receipt_required"],
    )
    floor = report["subject"]["verification_floor"]
    prior = floor["accepted_policy"]
    assert canonical_json_digest(prior) == floor["accepted_policy_digest"]
    assert any(
        "native_tool_configuration_location_invalid:markdownlint-cli2" in gap
        for gap in prior["gaps"]
    )
    assert legacy not in {source["path"] for gate in prior["gates"] for source in gate["sources"]}
