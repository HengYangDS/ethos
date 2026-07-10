# ruff: noqa: ARG005, TC003, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.domain.land.core as land_core
import ethos.domain.land.parity.core as land_parity
import ethos.domain.land.publication as land_publication
from ethos.repository.evidence import claims
from ethos.repository.registry import authority

if TYPE_CHECKING:
    import pytest

POLICY = SimpleNamespace(
    accepted_branch="dev",
    candidate_branch="candidate/dev",
    submit_branch_for_source=lambda branch: f"submit/{branch.replace('/', '-')}",
)


def test_claims_trust_envelope_and_report_edges(tmp_path: Path) -> None:
    assert claims.claims_report(tmp_path)["required_gaps"] == ["claims_missing"]
    assert claims._promotion_kind("docs/a.md") == "docs"
    assert claims._promotion_kind("schemas/a.json") == "schema"
    assert claims._promotion_kind("openspec/x") == "openspec"
    assert claims._promotion_kind("tests/a.py") == "tests"
    assert claims._promotion_targets(
        {"targets": ["docs/a.md", {"path": "src/a.py"}, {"path": "", "kind": "source"}]}
    ) == [
        {"kind": "docs", "path": "docs/a.md"},
        {"kind": "source", "path": "src/a.py"},
    ]
    assert claims._has_repository_overclaim("published and verified", "digest") is True
    assert claims._has_repository_overclaim("published and verified", "semantic") is False

    evidence = tmp_path / "evidence" / "proof.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("proof", encoding="utf-8")
    claim_dir = tmp_path / "evidence" / "claims"
    claim_dir.mkdir(parents=True)
    (claim_dir / "c1.toml").write_text(
        """
[claim]
id = "c1"
state = "active"
subject = "subject"
summary = "published and verified"

[evidence]
dated = "evidence/proof.md"
sha256 = "bad"
evidence_ids = []
binding = "adopter-domain storage validates"
verifier = "digest"
head = "old"

[boundary]
owner = ""
scope = ""

[carriers]
openspec = "openspec/changes/missing"

[promotion]
targets = ["docs/missing.md"]
""".strip(),
        encoding="utf-8",
    )
    report = claims.claims_report(tmp_path, current_head="new")
    gaps = set(report["required_gaps"])
    assert "c1:evidence_ids_missing" in gaps
    assert "c1:semantic_overclaim_requires_semantic_verifier" in gaps
    assert "c1:evidence.sha256_mismatch" in gaps
    assert "c1:evidence.head_stale:old!=new" in gaps
    assert "c1:boundary.owner_missing" in gaps
    assert "c1:boundary.scope_missing" in gaps
    assert "c1:fallback_missing" in gaps
    assert "c1:kill_signal_missing" in gaps
    assert "c1:promotion_target_missing:docs/missing.md" in gaps


def test_land_publication_and_parity_head_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert (
        land_publication.local_submit_package(branch="work/x", submit_branch="submit/x")[
            "remote_state"
        ]
        == "deferred"
    )
    assert land_publication.publication_readiness(branch="work/x", local_ok=False, policy=POLICY)[
        "required_gaps"
    ] == ["local_publish_readiness_blocked"]
    monkeypatch.setattr(land_core, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(land_core, "workspace_status", lambda repo: {"candidate": {"head": "c1"}})
    monkeypatch.setattr(land_core.git_adapter, "current_tracked_head", lambda root: "h1")
    package = land_core.closeout_bootstrap_package(
        repo=tmp_path, audit_root=tmp_path / "candidate", required_gaps=("gap",)
    )
    assert package["blocking"] is True and "--expect-head h1" in package["command"]
    assert package["mode"] == "maintainer_break_glass_local"
    assert package["runner_mode"] == "current_runner_with_explicit_accepted_root"
    assert package["remote_state"] == "deferred"
    assert package["uses_current_runner"] is True
    assert package["runner_binding"]["kind"] == "closeout_runner_binding"
    assert package["runner_module_path"] == package["runner_binding"]["runner_module_path"]
    assert package["runner_source_root"] == package["runner_binding"]["runner_source_root"]
    assert isinstance(package["runner_matches_accepted_root"], bool)
    assert isinstance(package["runner_matches_audit_root"], bool)
    assert isinstance(package["runner_advisories"], list)
    assert (
        package["required_order"][-1] == "defer remote push until remote publication is available"
    )

    # Parity currency now derives from the parity-relevant tree via
    # commits_equivalent_over_paths: the boundary (last relevant-path commit) plus every
    # commit up to head. Mock that helper's git calls: rev-list -1 <head> -- <paths>
    # returns the boundary "b0"; rev-list b0..h1 returns the intervening commits.
    def _stub_git_stdout(root: object, *args: str) -> str:
        if args[:2] == ("rev-list", "-1"):
            return "b0"  # boundary commit for the relevant pathspec
        if len(args) == 2 and args[0] == "rev-list" and args[1] == "b0..h1":
            return "h1\np1"  # commits after the boundary, up to head
        if args[:1] == ("rev-list",):
            return "h1\np1\nb0"
        return "h1"

    monkeypatch.setattr(land_core.git_adapter, "current_tracked_head", lambda root: "h1")
    monkeypatch.setattr(land_parity.git_adapter, "current_tracked_head", lambda root: "h1")
    monkeypatch.setattr(land_parity.git_adapter, "git_stdout", _stub_git_stdout)
    assert land_parity.acceptable_parity_product_heads(tmp_path, "generic") == (
        "h1",
        "p1",
        "b0",
    )
    monkeypatch.setattr(land_parity.git_adapter, "same_git_repository", lambda left, right: True)
    assert land_parity.acceptable_parity_target_heads(tmp_path, tmp_path, "generic") == (
        "h1",
        "p1",
        "b0",
    )
    monkeypatch.setattr(land_parity.git_adapter, "current_tracked_head", lambda root: "")
    assert land_parity.acceptable_parity_product_heads(tmp_path, "generic") == ()
    assert land_parity.acceptable_parity_target_heads(tmp_path, tmp_path, "generic") == ()


def test_authority_graph_empty_entries_are_valid(tmp_path: Path) -> None:
    graph = tmp_path / "docs" / "_meta" / "authority_graph.toml"
    graph.parent.mkdir(parents=True)
    graph.write_text("", encoding="utf-8")

    report = authority.authority_graph_report(tmp_path)

    assert report["ok"] is True
    assert report["entries"] == []
    assert report["required_gaps"] == []
