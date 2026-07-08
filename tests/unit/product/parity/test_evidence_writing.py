from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.shadow.core as shadow_core
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.unit.product.parity.snapshots import MIGRATED_CAPABILITIES
from tests.unit.product.parity.snapshots import SHADOW_COMMANDS
from tests.unit.product.parity.snapshots import git_head
from tests.unit.product.parity.snapshots import init_git_repo
from tests.unit.product.parity.snapshots import sha256_text

if TYPE_CHECKING:
    import pytest


def _checkout_work_lane(repo: Path) -> None:
    subprocess.run(
        ["git", "checkout", "-b", "work/parity-evidence"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_parity_shadow_write_evidence_blocks_protected_root_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = init_git_repo(tmp_path / "product")
    target = init_git_repo(tmp_path / "sample-adopter")

    def fake_shadow(
        *, target: Path, timeout_seconds: int, product_root: Path | None = None
    ) -> dict[str, object]:
        _ = (timeout_seconds, product_root)
        return {
            "ok": True,
            "state": "matched",
            "target": target.resolve().as_posix(),
            "required_gaps": [],
            "comparisons": SHADOW_COMMANDS,
            "semantic_dimensions": ["blocking_vs_advisory", "external_false_negative"],
            "false_negative_count": 0,
            "execution_packages": [],
        }

    monkeypatch.setattr(shadow_core, "run_shadow_parity", fake_shadow)

    completed = run_ethos_raw(
        "parity",
        "shadow",
        "--adopter",
        "sample-adopter",
        "--root",
        product.as_posix(),
        "--target",
        target.as_posix(),
        "--execute",
        "--write-evidence",
        "--json",
        cwd=product,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode != 0
    assert payload["ok"] is False
    assert "protected_lane_prewrite_blocked" in payload["required_gaps"]
    assert payload["data"]["write_admission"]["error"] == "protected_lane_prewrite_blocked"
    assert not (product / "evidence" / "parity" / "sample-adopter-shadow.json").exists()


def test_parity_shadow_write_evidence_records_freshness_and_capability_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = init_git_repo(tmp_path / "product")
    _checkout_work_lane(product)
    target = init_git_repo(tmp_path / "sample-adopter")

    def fake_shadow(
        *, target: Path, timeout_seconds: int, product_root: Path | None = None
    ) -> dict[str, object]:
        return {
            "ok": True,
            "state": "matched",
            "target": target.resolve().as_posix(),
            "required_gaps": [],
            "comparisons": SHADOW_COMMANDS,
            "semantic_dimensions": [
                "branch role",
                "publish readiness",
                "blocking_vs_advisory",
                "external_false_negative",
            ],
            "false_negative_count": 0,
            "accepted_summary": {
                "total_count": 2,
                "kind_counts": {
                    "changed_route_noop": 1,
                    "report_parity_evidence_refresh_bootstrap": 1,
                },
                "command_count": 2,
            },
            "execution_packages": [],
        }

    monkeypatch.setattr(shadow_core, "run_shadow_parity", fake_shadow)

    payload = run_ethos(
        "parity",
        "shadow",
        "--adopter",
        "sample-adopter",
        "--root",
        product.as_posix(),
        "--target",
        target.as_posix(),
        "--execute",
        "--timeout-seconds",
        "60",
        "--write-evidence",
        "--json",
        cwd=product,
    )

    evidence_path = product / "evidence" / "parity" / "sample-adopter-shadow.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_command = (
        "uv run --package ethos ethos parity shadow --adopter sample-adopter "
        f"--target {target.resolve().as_posix()} --execute --timeout-seconds 60 --json"
    )

    assert payload["ok"] is True
    assert payload["state"] == "matched"
    assert payload["data"]["evidence_written"] == evidence_path.relative_to(product).as_posix()
    assert evidence["adopter"] == "sample-adopter"
    assert evidence["target"] == target.resolve().as_posix()
    assert evidence["command"] == expected_command
    assert evidence["freshness"] == {
        "product_head": git_head(product),
        "target_head": git_head(target),
        "product_semantic_sha256": evidence["freshness"]["product_semantic_sha256"],
        "target_semantic_sha256": evidence["freshness"]["target_semantic_sha256"],
        "command_sha256": sha256_text(expected_command),
    }
    assert evidence["freshness"]["product_semantic_sha256"]
    assert evidence["freshness"]["target_semantic_sha256"]
    assert evidence["shadow"]["ok"] is True
    assert evidence["shadow"]["state"] == "matched"
    assert evidence["shadow"]["comparison_count"] == len(SHADOW_COMMANDS)
    assert evidence["shadow"]["commands"] == SHADOW_COMMANDS
    assert evidence["shadow"]["accepted_summary"] == {
        "total_count": 2,
        "kind_counts": {
            "changed_route_noop": 1,
            "report_parity_evidence_refresh_bootstrap": 1,
        },
        "command_count": 2,
    }
    assert evidence["identity"] == {
        "target_root": target.resolve().as_posix(),
        "target_head": git_head(target),
        "product_head": git_head(product),
        "changed_paths": [],
        "commands": SHADOW_COMMANDS,
        "external_commands": [],
        "embedded_commands": [],
        "evidence_inputs": [],
    }
    assert evidence["verified_capabilities"] == MIGRATED_CAPABILITIES
    assert set(evidence["capability_basis"]) == set(MIGRATED_CAPABILITIES)


def test_parity_shadow_write_evidence_defaults_to_generic_adopter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = init_git_repo(tmp_path / "product")
    _checkout_work_lane(product)

    def fake_shadow(
        *, target: Path, timeout_seconds: int, product_root: Path | None = None
    ) -> dict[str, object]:
        return {
            "ok": True,
            "state": "matched",
            "target": target.resolve().as_posix(),
            "required_gaps": [],
            "comparisons": SHADOW_COMMANDS,
            "semantic_dimensions": ["product command parity", "external_false_negative"],
            "false_negative_count": 0,
            "execution_packages": [],
        }

    monkeypatch.setattr(shadow_core, "run_shadow_parity", fake_shadow)

    payload = run_ethos(
        "parity",
        "shadow",
        "--root",
        product.as_posix(),
        "--target",
        product.as_posix(),
        "--execute",
        "--write-evidence",
        "--json",
        cwd=product,
    )

    evidence_path = product / "evidence" / "parity" / "generic-shadow.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_target = "<repo>"
    expected_command = (
        "uv run --package ethos ethos parity shadow --adopter generic "
        "--target . --execute --timeout-seconds 30 --json"
    )

    assert payload["ok"] is True
    assert evidence["adopter"] == "generic"
    assert evidence["target"] == expected_target
    assert evidence["command"] == expected_command
    assert evidence["freshness"]["product_head"] == git_head(product)
    assert evidence["freshness"]["target_head"] == git_head(product)
    assert evidence["freshness"]["command_sha256"] == sha256_text(expected_command)


def test_tracked_parity_evidence_uses_repository_governance_terms() -> None:
    retired_terms = (
        "self_audit",
        "self-audit",
        "self audit",
        "self-governance",
        "self-evolution",
        "self-hosting",
        "single-kernel dual-posture",
        "single_kernel_dual_posture",
        "dual-posture",
        "product_self",
        "adopter_repository",
        "posture",
    )
    findings = [
        f"{path}: {term}"
        for path in Path("evidence/parity").glob("*-shadow.json")
        for term in retired_terms
        if term in path.read_text(encoding="utf-8").lower()
    ]

    assert findings == []
