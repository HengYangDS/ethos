from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ethos.domain.land import acceptable_parity_product_heads
from ethos.repository.evidence.parity import PARITY_RELEVANT_PATHS
from ethos.repository.evidence.parity import _shadow_evidence_command
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity_validation import semantic_tree_digest
from tests.support.ethos_cli_runner import run_ethos
from tests.unit.product.parity.snapshots import complete_parity_evidence
from tests.unit.product.parity.snapshots import git_head
from tests.unit.product.parity.snapshots import init_git_repo
from tests.unit.product.parity.snapshots import retarget_parity_evidence
from tests.unit.product.parity.snapshots import sha256_text

if TYPE_CHECKING:
    from pathlib import Path


def _set_durable_evidence_root(repo: Path, value: str) -> None:
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(f'[roots]\ndurable_evidence = "{value}"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "configure evidence root",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_shadow_evidence_command_includes_product_root_only_for_external_target(
    tmp_path: Path,
) -> None:
    product = tmp_path / "product"
    product.mkdir()

    assert _shadow_evidence_command(
        adopter="sample-adopter",
        root=product,
        target="/tmp/adopter",
        timeout_seconds=17,
        include_product_root=True,
    ) == (
        "uv run --package ethos ethos parity shadow --adopter sample-adopter "
        f"--root {product.resolve().as_posix()} "
        "--target /tmp/adopter --execute --timeout-seconds 17 --json"
    )
    assert _shadow_evidence_command(
        adopter="generic",
        root=None,
        target=".",
        timeout_seconds=5,
        include_product_root=True,
    ) == (
        "uv run --package ethos ethos parity shadow --adopter generic "
        "--target . --execute --timeout-seconds 5 --json"
    )


def test_parity_gaps_uses_product_evidence_root_for_missing_target(
    tmp_path: Path,
) -> None:
    product = init_git_repo(tmp_path / "product")
    missing_target = tmp_path / "missing-adopter"

    payload = parity_gaps_report(
        adopter="sample-adopter",
        root=product,
        target=missing_target,
    )

    refresh = payload["evidence"]["refresh_package"]
    assert refresh["root"] == product.resolve().as_posix()
    assert refresh["target"] == missing_target.resolve().as_posix()
    assert refresh["command"] == (
        "ethos parity shadow --adopter sample-adopter "
        f"--target {missing_target.resolve().as_posix()} --execute --write-evidence --json"
    )


def test_parity_gaps_reports_shadow_gap_without_tracked_evidence(tmp_path: Path) -> None:
    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["command"] == "parity gaps"
    assert "shadow_parity_pending:sample-adopter" in payload["required_gaps"]
    assert len(payload["data"]["pending_packages"]) == len(payload["required_gaps"])


def test_parity_gaps_recommends_write_evidence_when_tracked_evidence_is_stale(
    tmp_path: Path,
) -> None:
    product = init_git_repo(tmp_path / "product")
    target = init_git_repo(tmp_path / "sample-adopter")
    evidence_dir = target / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(stale, adopter="sample-adopter", target=target)
    stale["freshness"]["product_head"] = "old-product-head"
    stale["freshness"]["target_head"] = git_head(target)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(stale),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        product.as_posix(),
        "--target",
        target.as_posix(),
        "--json",
        cwd=product,
    )

    assert payload["ok"] is False
    assert payload["next_actions"] == [
        (
            "ethos parity shadow --adopter sample-adopter "
            f"--root {product.resolve().as_posix()} "
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        )
    ]
    refresh = payload["data"]["evidence"]["refresh_package"]
    assert refresh == {
        "kind": "parity_evidence_refresh",
        "adopter": "sample-adopter",
        "root": product.resolve().as_posix(),
        "target": target.resolve().as_posix(),
        "blocking": True,
        "required_gaps": [
            "parity_evidence_invalid:sample-adopter",
            "parity_evidence_invalid:sample-adopter:product_head",
        ],
        "command": (
            "ethos parity shadow --adopter sample-adopter "
            f"--root {product.resolve().as_posix()} "
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        ),
        "next_action": "refresh tracked shadow parity evidence",
    }


def test_parity_gaps_ignores_product_root_adopter_evidence_for_distinct_target(
    tmp_path: Path,
) -> None:
    product = init_git_repo(tmp_path / "product")
    target = init_git_repo(tmp_path / "sample-adopter")
    evidence_dir = product / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["product_head"] = git_head(product)
    evidence["freshness"]["target_head"] = git_head(target)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        product.as_posix(),
        "--target",
        target.as_posix(),
        "--json",
        cwd=product,
    )

    assert payload["ok"] is False
    assert (
        "parity_evidence_missing:sample-adopter"
        in (payload["data"]["evidence"]["refresh_package"]["required_gaps"])
    )
    assert payload["data"]["evidence"]["refresh_package"]["root"] == product.resolve().as_posix()
    assert payload["data"]["evidence"]["refresh_package"]["target"] == target.resolve().as_posix()


def test_parity_gaps_reads_adopter_profile_durable_evidence_root(
    tmp_path: Path,
) -> None:
    product = init_git_repo(tmp_path / "product")
    target = init_git_repo(tmp_path / "sample-adopter")
    _set_durable_evidence_root(target, "docs/evidence")
    evidence_dir = target / "docs" / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["product_head"] = git_head(product)
    evidence["freshness"]["target_head"] = git_head(target)
    evidence["freshness"]["product_semantic_sha256"] = semantic_tree_digest(
        product, head=git_head(product), relevant_paths=PARITY_RELEVANT_PATHS
    )
    evidence["freshness"]["target_semantic_sha256"] = semantic_tree_digest(
        target, head=git_head(target), relevant_paths=PARITY_RELEVANT_PATHS
    )
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        product.as_posix(),
        "--target",
        target.as_posix(),
        "--json",
        cwd=product,
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["evidence"]["path"] == "docs/evidence/parity/sample-adopter-shadow.json"


def test_parity_gaps_reports_generic_tracked_evidence_state() -> None:
    payload = run_ethos("parity", "gaps", "--adopter", "generic", "--target", ".", "--json")

    assert payload["data"]["evidence"]["path"] == "evidence/parity/generic-shadow.json"
    assert payload["data"]["evidence"]["freshness"]["command_sha256"]
    if payload["ok"] is True:
        assert (payload["required_gaps"], payload["data"]["pending_packages"]) == ([], [])
    else:
        refresh = payload["data"]["evidence"]["refresh_package"]
        assert "parity_evidence_invalid:generic" in payload["required_gaps"]
        assert (refresh["kind"], refresh["blocking"], refresh["adopter"]) == (
            "parity_evidence_refresh",
            True,
            "generic",
        )


def test_parity_gaps_closes_generic_from_tracked_product_evidence() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == "evidence/parity/generic-shadow.json"


def test_parity_gaps_defaults_target_to_repo_for_self_governance() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    freshness = payload["data"]["evidence"]["provenance"]["freshness"]
    assert freshness["current_target_head"]
    assert freshness["current_target_semantic_sha256"]
    assert freshness["target_semantic_current"] is True


def test_parity_gaps_rejects_shadow_evidence_without_false_negative_gate(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = complete_parity_evidence("sample-adopter")
    stale["shadow"].pop("false_negative_count")
    stale["semantic_dimensions"] = ["blocking_vs_advisory"]
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(stale),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter:false_negative_count" in payload["required_gaps"]
    assert (
        "parity_evidence_invalid:sample-adopter:semantic_dimension:external_false_negative"
        in payload["required_gaps"]
    )


def test_parity_gaps_uses_tracked_shadow_evidence_to_close_verified_capabilities(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(complete_parity_evidence("sample-adopter")),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == ("evidence/parity/sample-adopter-shadow.json")


def test_parity_gaps_rejects_release_visible_local_paths_in_shadow_evidence(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    evidence = complete_parity_evidence("sample-adopter")
    evidence["shadow"]["release_note"] = "/" + "Users" + "/person/private-checkout"
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert (
        "parity_evidence_invalid:sample-adopter:release_visible_local_path"
        in payload["required_gaps"]
    )


def test_parity_gaps_rejects_shadow_evidence_without_freshness_identity(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = complete_parity_evidence("sample-adopter")
    stale.pop("freshness")
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(stale),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter:freshness" in payload["required_gaps"]


def test_parity_gaps_rejects_product_head_mismatch(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = complete_parity_evidence("sample-adopter")
    stale["freshness"]["product_head"] = "old-product-head"
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(stale),
        encoding="utf-8",
    )

    payload = parity_gaps_report(
        adopter="sample-adopter",
        root=tmp_path,
        current_product_head="current-product-head",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter:product_head" in payload["required_gaps"]
    freshness = payload["evidence"]["provenance"]["freshness"]
    assert freshness["product_head_current"] is False
    assert freshness["product_head_accepted_by_relevant_tree"] is False


def test_parity_gaps_accepts_evidence_updated_in_current_commit(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "dev"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "base",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    parent_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()

    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    evidence = complete_parity_evidence("sample-adopter")
    evidence["freshness"]["product_head"] = parent_head
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "refresh parity evidence",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert parent_head != current_head


def test_parity_gaps_rejects_weak_shadow_evidence_that_lists_capabilities(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    weak = complete_parity_evidence("sample-adopter")
    weak["shadow"] = {"ok": True, "required_gaps": [], "comparison_count": 1}
    weak.pop("capability_basis")
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(weak),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter" in payload["required_gaps"]
    assert payload["data"]["pending_packages"]


def test_parity_gaps_rejects_incomplete_shadow_evidence(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(
            {
                "shadow": {"ok": True, "required_gaps": []},
                "verified_capabilities": [
                    "work-lane-lifecycle",
                    "proof-evidence-chronicle",
                    "campaign-hypothesis-evolution",
                    "assistant-playbooks-skills",
                    "quality-determinism-local-state",
                    "openspec-claims-trust-review",
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = run_ethos(
        "parity",
        "gaps",
        "--adopter",
        "sample-adopter",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter" in payload["required_gaps"]
    assert payload["data"]["pending_packages"]


def test_parity_gaps_exposes_concrete_backlog_packages_without_evidence(
    tmp_path: Path,
) -> None:
    payload = run_ethos(
        "parity",
        "gaps",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    package = payload["data"]["pending_packages"][0]
    assert package["gap"] == "parity_pending:work-lane-lifecycle"
    assert package["capability"] == "work-lane-lifecycle"
    assert package["target_home"] == "ethos-repository + ethos-adapters + ethos-test"
    assert package["required_tests"] == [
        "status/lane/prewrite golden JSON",
        "start lease and execution registry",
        "handoff and closeout dry-run/apply admission",
        "candidate lock and stale-base rejection",
        "foreign lane observe-only protection",
    ]
    assert package["parity_criterion"]
    assert package["rollback_impact"]


def test_parity_freshness_tracks_relevant_tree_not_evidence_touch(tmp_path: Path) -> None:
    """Parity currency follows the parity-relevant source tree, not a proxy touch of the
    evidence file. A commit that changes only parity-irrelevant paths (tests, prose)
    does NOT stale the evidence; a commit under packages/** does. This removes the
    shared-evidence-file serialization bottleneck between concurrent lanes."""

    def g(*a: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@e.x", *a],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    g("init", "-b", "dev")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "x.py").write_text("1\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "product source")
    src_head = g("rev-parse", "HEAD").stdout.strip()

    # a commit touching ONLY parity-irrelevant paths must NOT stale the src head
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("t\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("prose\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "tests + prose (parity-irrelevant)")
    assert src_head in acceptable_parity_product_heads(tmp_path, "generic")

    # a commit under packages/** DOES stale it (verdict could change)
    (tmp_path / "packages" / "y.py").write_text("2\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "product source change")
    assert src_head not in acceptable_parity_product_heads(tmp_path, "generic")

    # a foreign / unrelated head is never accepted
    assert ("f" * 40) not in acceptable_parity_product_heads(tmp_path, "generic")


def test_parity_evidence_semantic_digest_allows_self_evidence_commit(
    tmp_path: Path,
) -> None:
    product = init_git_repo(tmp_path / "product")
    target = product
    (product / "packages").mkdir()
    (product / "packages" / "core.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=product, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "add product source",
        ],
        cwd=product,
        check=True,
        capture_output=True,
    )
    semantic_head = git_head(product)
    evidence = complete_parity_evidence("generic")
    command = (
        "uv run --package ethos ethos parity shadow --adopter generic "
        "--target . --execute --timeout-seconds 30 --json"
    )
    evidence["target"] = "<repo>"
    evidence["command"] = command
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    freshness["product_head"] = semantic_head
    freshness["target_head"] = semantic_head
    freshness["command_sha256"] = sha256_text(command)
    digest = semantic_tree_digest(product, head=semantic_head, relevant_paths=PARITY_RELEVANT_PATHS)
    freshness["product_semantic_sha256"] = digest
    freshness["target_semantic_sha256"] = digest
    evidence_dir = product / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "generic-shadow.json").write_text(json.dumps(evidence), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=product, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "record parity evidence",
        ],
        cwd=product,
        check=True,
        capture_output=True,
    )
    evidence_commit = git_head(product)

    payload = parity_gaps_report(
        adopter="generic",
        root=product,
        target=target,
        current_product_head=evidence_commit,
        current_target_head=evidence_commit,
    )

    assert payload["ok"] is True
    freshness_report = payload["evidence"]["provenance"]["freshness"]
    assert freshness_report["product_head_current"] is False
    assert freshness_report["target_head_current"] is False
    assert freshness_report["product_semantic_current"] is True
    assert freshness_report["target_semantic_current"] is True

    (product / "packages" / "core.py").write_text("value = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=product, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "change product source",
        ],
        cwd=product,
        check=True,
        capture_output=True,
    )
    changed_head = git_head(product)
    stale_payload = parity_gaps_report(
        adopter="generic",
        root=product,
        target=target,
        current_product_head=changed_head,
        current_target_head=changed_head,
    )

    assert stale_payload["ok"] is False
    assert "parity_evidence_invalid:generic:product_head" in stale_payload["required_gaps"]
    assert "parity_evidence_invalid:generic:target_head" in stale_payload["required_gaps"]
