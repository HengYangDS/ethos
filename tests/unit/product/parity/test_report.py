from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.evidence.parity.core import shadow_parity_report
from tests.unit.product.parity.snapshots import SHADOW_COMMANDS
from tests.unit.product.parity.snapshots import complete_parity_evidence
from tests.unit.product.parity.snapshots import git_head
from tests.unit.product.parity.snapshots import init_git_repo
from tests.unit.product.parity.snapshots import retarget_parity_evidence
from tests.unit.product.parity.snapshots import write_parity_evidence

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
    write_parity_evidence(tmp_path, evidence)

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


@pytest.mark.parametrize(
    ("dimension", "freshness_key", "current_key", "accepted_key"),
    [
        ("product", "product_head", "current_product_head", "acceptable_product_heads"),
        ("target", "target_head", "current_target_head", "acceptable_target_heads"),
    ],
    ids=["parent-product-head", "parent-target-head"],
)
def test_shadow_parity_report_accepts_relevant_parent_head(
    tmp_path: Path,
    dimension: str,
    freshness_key: str,
    current_key: str,
    accepted_key: str,
) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    parent_head = f"parent-{dimension}-head"
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    freshness[freshness_key] = parent_head
    write_parity_evidence(tmp_path, evidence)

    payload = shadow_parity_report(
        target=target,
        root=tmp_path,
        adopter="sample-adopter",
        **{current_key: f"current-{dimension}-head", accepted_key: (parent_head,)},
    )

    assert payload["ok"] is True
    assert payload["state"] == "matched"
    assert payload["required_gaps"] == []
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    output_freshness = provenance["freshness"]
    assert isinstance(output_freshness, dict)
    assert output_freshness[freshness_key] == parent_head
    assert output_freshness[current_key] == f"current-{dimension}-head"
    assert output_freshness[f"{dimension}_head_current"] is False
    assert output_freshness[f"{dimension}_head_accepted_by_relevant_tree"] is True


def test_shadow_parity_report_rejects_target_head_mismatch(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "sample-adopter")
    current_target_head = git_head(target)
    evidence = complete_parity_evidence("sample-adopter")
    retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["target_head"] = "stale-target-head"
    write_parity_evidence(target, evidence)

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
        "lifecycle": {
            "stage": "work_lane_before_proof",
            "write_root": target.resolve().as_posix(),
            "write_path": "evidence/parity/sample-adopter-shadow.json",
            "commit_before_proof": True,
            "authority_boundary": (
                "refresh and commit tracked parity evidence from the admitted "
                "Work Lane; candidate and accepted roots remain write-protected"
            ),
        },
        "command": (
            "ethos parity shadow --adopter sample-adopter "
            f"--root {tmp_path.resolve().as_posix()} "
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        ),
        "next_action": "refresh and commit tracked shadow parity evidence before proof",
    }
