# ruff: noqa: ARG005
"""Coverage-closure: generated-artifact topology edge branches (100% no-exemption).

The generated-artifact-topology contract and its repository policy landed with a
few branches the existing tests did not exercise. These close them so the
whole-repo 100% floor holds:

- path_policy_for adopter-specific product-root denial (topology line 159).
- generated_artifact_topology_report review/deny arms where a policy carries no
  required_gap (artifacts.py branches 46->35, 49->35).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy import artifacts as artifacts_mod
from ethos_core.contracts.artifacts import topology

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_path_policy_denies_adopter_specific_product_root() -> None:
    # An adopter-specific root under a product repo is denied (topology line 159).
    policy = topology.path_policy_for("adopters/acme/config.yaml")

    assert policy["decision"] == "deny"
    assert "adopter_specific_product_root" in str(policy["required_gap"])


def test_report_collects_review_and_deny_gaps_across_iterations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A review/deny policy WITH a gap appends and then continues the loop; one
    # WITHOUT a gap takes the guard's false arm. An allow and an ignore policy
    # exercise the remaining decision arms (artifacts.py line 40 and 46->35).
    for name in (
        "allow.txt",
        "review_gap.txt",
        "review_none.txt",
        "deny_gap.txt",
        "deny_none.txt",
        "ignore.txt",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")

    def _fake_policy(rel: str) -> dict[str, object]:
        if rel.endswith("allow.txt"):
            return {"decision": "allow"}
        if rel.endswith("review_gap.txt"):
            return {"decision": "review", "required_gap": "review_gap_here"}
        if rel.endswith("review_none.txt"):
            return {"decision": "review", "required_gap": ""}
        if rel.endswith("deny_gap.txt"):
            return {"decision": "deny", "required_gap": "deny_gap_here"}
        if rel.endswith("deny_none.txt"):
            return {"decision": "deny", "required_gap": ""}
        return {"decision": "ignore"}

    monkeypatch.setattr(artifacts_mod, "path_policy_for", _fake_policy)
    monkeypatch.setattr(
        artifacts_mod,
        "_candidate_paths",
        lambda root: [
            tmp_path / "allow.txt",
            tmp_path / "review_gap.txt",
            tmp_path / "review_none.txt",
            tmp_path / "deny_gap.txt",
            tmp_path / "deny_none.txt",
            tmp_path / "ignore.txt",
        ],
    )

    report = artifacts_mod.generated_artifact_topology_report(tmp_path)

    # Only the gap-carrying policies contribute; the empty ones are tolerated.
    assert report["review_gaps"] == ["review_gap_here"]
    assert report["required_gaps"] == ["deny_gap_here"]
    assert "allow.txt" in report["allowed_paths"]
