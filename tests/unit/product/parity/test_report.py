from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ethos.repository.evidence.parity import shadow_parity_report
from tests.unit.product.parity.snapshots import SHADOW_COMMANDS
from tests.unit.product.parity.snapshots import complete_parity_evidence
from tests.unit.product.parity.snapshots import retarget_parity_evidence

if TYPE_CHECKING:
    from pathlib import Path


def test_shadow_parity_report_uses_tracked_matching_evidence(tmp_path: Path) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["semantic_dimensions"] = [
        "branch role",
        "publish readiness",
        "blocking_vs_advisory",
        "external_false_negative",
    ]
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = shadow_parity_report(
        target=target,
        root=tmp_path,
        adopter="sample-adopter",
    )

    assert payload["ok"] is True
    assert payload["state"] == "matched"
    assert payload["required_gaps"] == []
    assert payload["execution_packages"] == [
        {
            "kind": "shadow_parity_evidence",
            "state": "matched",
            "target": target.resolve().as_posix(),
            "evidence_path": "evidence/parity/sample-adopter-shadow.json",
            "comparison_count": len(SHADOW_COMMANDS),
            "commands": SHADOW_COMMANDS,
            "semantic_dimensions": evidence["semantic_dimensions"],
            "blocking": False,
            "required_gaps": [],
            "provenance": {
                "mode": "tracked_evidence",
                "evidence_path": "evidence/parity/sample-adopter-shadow.json",
                "freshness": {
                    "ok": True,
                    "required_gaps": [],
                    "product_head": "product-head",
                    "current_product_head": "",
                    "product_head_current": False,
                    "product_head_accepted_by_relevant_tree": False,
                    "product_semantic_sha256": "",
                    "current_product_semantic_sha256": "",
                    "product_semantic_current": False,
                    "target_head": "target-head",
                    "current_target_head": "",
                    "target_head_current": False,
                    "target_head_accepted_by_relevant_tree": False,
                    "target_semantic_sha256": "",
                    "current_target_semantic_sha256": "",
                    "target_semantic_current": False,
                    "command_sha256": evidence["freshness"]["command_sha256"],
                },
            },
            "next_action": "use tracked shadow parity evidence for local closeout",
        }
    ]
    assert payload["provenance"] == payload["execution_packages"][0]["provenance"]


def test_shadow_parity_report_accepts_current_commit_parent_product_head(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["product_head"] = "parent-product-head"
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = shadow_parity_report(
        target=target,
        root=tmp_path,
        adopter="sample-adopter",
        current_product_head="current-product-head",
        acceptable_product_heads=("parent-product-head",),
    )

    assert payload["ok"] is True
    assert payload["state"] == "matched"
    assert payload["required_gaps"] == []
    freshness = payload["provenance"]["freshness"]
    assert freshness["product_head"] == "parent-product-head"
    assert freshness["current_product_head"] == "current-product-head"
    assert freshness["product_head_current"] is False
    assert freshness["product_head_accepted_by_relevant_tree"] is True


def test_shadow_parity_report_accepts_current_commit_parent_target_head(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["target_head"] = "parent-target-head"
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = shadow_parity_report(
        target=target,
        root=tmp_path,
        adopter="sample-adopter",
        current_target_head="current-target-head",
        acceptable_target_heads=("parent-target-head",),
    )

    assert payload["ok"] is True
    assert payload["state"] == "matched"
    assert payload["required_gaps"] == []
    freshness = payload["provenance"]["freshness"]
    assert freshness["target_head"] == "parent-target-head"
    assert freshness["current_target_head"] == "current-target-head"
    assert freshness["target_head_current"] is False
    assert freshness["target_head_accepted_by_relevant_tree"] is True


def test_shadow_parity_report_rejects_target_head_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    subprocess.run(["git", "init", "-b", "dev"], cwd=target, check=True, capture_output=True)
    (target / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=target,
        check=True,
        capture_output=True,
    )
    current_target_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["target_head"] = "stale-target-head"
    evidence_dir = target / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )

    payload = shadow_parity_report(
        target=target,
        root=tmp_path,
        adopter="sample-adopter",
        current_target_head=current_target_head,
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter:target_head" in payload["required_gaps"]
    assert payload["provenance"]["mode"] == "tracked_evidence"
    freshness = payload["provenance"]["freshness"]
    assert freshness["ok"] is False
    assert freshness["current_target_head"] == current_target_head
    assert freshness["target_head_current"] is False
    assert freshness["target_head_accepted_by_relevant_tree"] is False
    refresh = payload["execution_packages"][0]["refresh_package"]
    assert refresh == {
        "kind": "parity_evidence_refresh",
        "adopter": "sample-adopter",
        "root": tmp_path.resolve().as_posix(),
        "target": target.resolve().as_posix(),
        "blocking": True,
        "required_gaps": [
            "parity_evidence_invalid:sample-adopter",
            "parity_evidence_invalid:sample-adopter:target_head",
        ],
        "command": (
            "ethos parity shadow --adopter sample-adopter "
            f"--root {tmp_path.resolve().as_posix()} "
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        ),
        "next_action": "refresh tracked shadow parity evidence",
    }
