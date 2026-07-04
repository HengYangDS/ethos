from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from ethos.adapters import shadow
from ethos.adapters.shadow import _accepted_semantic_differences
from ethos.adapters.shadow import _run_embedded
from ethos.adapters.shadow import _run_external
from ethos.adapters.shadow import _semantic_diff
from ethos.adapters.shadow import run_shadow_parity
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import shadow_parity_report
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos

MIGRATED_CAPABILITIES = [
    "work-lane-lifecycle",
    "proof-evidence-chronicle",
    "campaign-hypothesis-evolution",
    "assistant-playbooks-skills",
    "quality-determinism-local-state",
    "openspec-claims-trust-review",
]

SHADOW_COMMANDS = [
    "ethos status --json",
    "ethos plan --changed --json",
    "ethos prove --json",
    "ethos report --json",
    "ethos quality command-surface --json",
    "ethos assistants doctor --json",
    "ethos playbooks route --changed --json",
    "ethos land --json",
    "ethos publish --json",
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "dev"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
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
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _complete_parity_evidence(adopter: str) -> dict[str, object]:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target /tmp/{adopter} --execute --timeout-seconds 30 --json"
    )
    return {
        "schema_version": 1,
        "adopter": adopter,
        "target": f"/tmp/{adopter}",
        "generated_on": "2026-07-01",
        "command": command,
        "freshness": {
            "product_head": "product-head",
            "target_head": "target-head",
            "command_sha256": _sha256_text(command),
        },
        "shadow": {
            "ok": True,
            "required_gaps": [],
            "comparison_count": len(SHADOW_COMMANDS),
            "commands": SHADOW_COMMANDS,
        },
        "verified_capabilities": MIGRATED_CAPABILITIES,
        "capability_basis": {
            capability: [f"{capability} shadow parity basis"]
            for capability in MIGRATED_CAPABILITIES
        },
    }


def _retarget_parity_evidence(
    evidence: dict[str, object],
    *,
    adopter: str,
    target: Path,
    timeout_seconds: int = 30,
) -> None:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target {target.resolve().as_posix()} --execute "
        f"--timeout-seconds {timeout_seconds} --json"
    )
    evidence["target"] = target.resolve().as_posix()
    evidence["command"] = command
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    freshness["command_sha256"] = _sha256_text(command)


def test_parity_ledger_has_no_unclassified_capabilities() -> None:
    payload = run_ethos("parity", "ledger", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "parity ledger"
    assert payload["summary"]["unclassified_count"] == 0
    assert {record["capability"] for record in payload["data"]["records"]} >= {
        "work-lane-lifecycle",
        "proof-evidence-chronicle",
        "campaign-hypothesis-evolution",
        "assistant-playbooks-skills",
        "quality-determinism-local-state",
        "openspec-claims-trust-review",
        "reference-adopter-domain-contract-profile",
    }


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
    product = _init_git_repo(tmp_path / "product")
    target = _init_git_repo(tmp_path / "sample-adopter")
    evidence_dir = product / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = _complete_parity_evidence("sample-adopter")
    _retarget_parity_evidence(stale, adopter="sample-adopter", target=target)
    stale["freshness"]["product_head"] = "old-product-head"
    stale["freshness"]["target_head"] = _git_head(target)
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
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        ),
        "next_action": "refresh tracked shadow parity evidence",
    }


def test_parity_gaps_closes_alphasim_dmgr_from_tracked_evidence() -> None:
    payload = run_ethos("parity", "gaps", "--adopter", "alphasim-dmgr", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == ("evidence/parity/alphasim-dmgr-shadow.json")
    assert payload["data"]["evidence"]["freshness"]["command_sha256"]


def test_parity_gaps_closes_generic_from_tracked_product_evidence() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["pending_packages"] == []
    assert payload["data"]["evidence"]["path"] == "evidence/parity/generic-shadow.json"


def test_parity_shadow_write_evidence_records_freshness_and_capability_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = _init_git_repo(tmp_path / "product")
    target = _init_git_repo(tmp_path / "sample-adopter")

    def fake_shadow(*, target: Path, timeout_seconds: int) -> dict[str, object]:
        return {
            "ok": True,
            "state": "matched",
            "target": target.resolve().as_posix(),
            "required_gaps": [],
            "comparisons": SHADOW_COMMANDS,
            "semantic_dimensions": ["branch role", "publish readiness"],
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

    monkeypatch.setattr(shadow, "run_shadow_parity", fake_shadow)

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
        "product_head": _git_head(product),
        "target_head": _git_head(target),
        "command_sha256": _sha256_text(expected_command),
    }
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
    assert evidence["verified_capabilities"] == MIGRATED_CAPABILITIES
    assert set(evidence["capability_basis"]) == set(MIGRATED_CAPABILITIES)


def test_parity_shadow_write_evidence_defaults_to_generic_adopter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = _init_git_repo(tmp_path / "product")

    def fake_shadow(*, target: Path, timeout_seconds: int) -> dict[str, object]:
        return {
            "ok": True,
            "state": "matched",
            "target": target.resolve().as_posix(),
            "required_gaps": [],
            "comparisons": SHADOW_COMMANDS,
            "semantic_dimensions": ["product command parity"],
            "execution_packages": [],
        }

    monkeypatch.setattr(shadow, "run_shadow_parity", fake_shadow)

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

    assert payload["ok"] is True
    assert evidence["adopter"] == "generic"
    assert evidence["freshness"]["product_head"] == _git_head(product)
    assert evidence["freshness"]["target_head"] == _git_head(product)


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
    findings: list[str] = []

    for path in Path("evidence/parity").glob("*-shadow.json"):
        text = path.read_text(encoding="utf-8").lower()
        for term in retired_terms:
            if term in text:
                findings.append(f"{path}: {term}")

    assert findings == []


def test_parity_gaps_uses_tracked_shadow_evidence_to_close_verified_capabilities(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "sample-adopter-shadow.json").write_text(
        json.dumps(_complete_parity_evidence("sample-adopter")),
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
    assert payload["data"]["evidence"]["path"] == (
        "evidence/parity/sample-adopter-shadow.json"
    )


def test_shadow_parity_report_uses_tracked_matching_evidence(tmp_path: Path) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    evidence = _complete_parity_evidence("sample-adopter")
    _retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["semantic_dimensions"] = ["branch role", "publish readiness"]
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
                    "target_head": "target-head",
                    "current_target_head": "",
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
    evidence = _complete_parity_evidence("sample-adopter")
    _retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
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
    assert payload["provenance"]["freshness"]["product_head"] == "parent-product-head"
    assert payload["provenance"]["freshness"]["current_product_head"] == "current-product-head"


def test_shadow_parity_report_accepts_current_commit_parent_target_head(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample-adopter"
    target.mkdir()
    evidence = _complete_parity_evidence("sample-adopter")
    _retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
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
    assert payload["provenance"]["freshness"]["target_head"] == "parent-target-head"
    assert payload["provenance"]["freshness"]["current_target_head"] == "current-target-head"


def test_parity_gaps_rejects_shadow_evidence_without_freshness_identity(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    stale = _complete_parity_evidence("sample-adopter")
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
    stale = _complete_parity_evidence("sample-adopter")
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
    evidence = _complete_parity_evidence("sample-adopter")
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
    evidence = _complete_parity_evidence("sample-adopter")
    _retarget_parity_evidence(evidence, adopter="sample-adopter", target=target)
    evidence["freshness"]["target_head"] = "stale-target-head"
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
        current_target_head=current_target_head,
    )

    assert payload["ok"] is False
    assert "parity_evidence_invalid:sample-adopter:target_head" in payload["required_gaps"]
    assert payload["provenance"]["mode"] == "tracked_evidence"
    assert payload["provenance"]["freshness"]["ok"] is False
    assert payload["provenance"]["freshness"]["current_target_head"] == current_target_head
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
            f"--target {target.resolve().as_posix()} --execute --write-evidence --json"
        ),
        "next_action": "refresh tracked shadow parity evidence",
    }


def test_parity_gaps_rejects_weak_shadow_evidence_that_lists_capabilities(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    weak = _complete_parity_evidence("sample-adopter")
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


def test_parity_shadow_defaults_to_read_only_plan(tmp_path: Path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path.cwd(),
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert "ethos quality command-surface --json" in payload["data"]["comparisons"]
    assert payload["data"]["execution_packages"] == [
        {
            "gap": f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}",
            "state": "planned",
            "target": tmp_path.resolve().as_posix(),
            "commands": payload["data"]["comparisons"],
            "semantic_dimensions": payload["data"]["semantic_dimensions"],
            "blocking": True,
            "provenance": {
                "mode": "planned_shadow_run",
                "evidence_path": "",
                "freshness": {
                    "ok": False,
                    "required_gaps": [
                        f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}"
                    ],
                    "product_head": "",
                    "current_product_head": current_head,
                    "target_head": "",
                    "current_target_head": "",
                    "command_sha256": "",
                },
            },
            "refresh_package": {
                "kind": "parity_evidence_refresh",
                "adopter": "generic",
                "root": Path.cwd().resolve().as_posix(),
                "target": tmp_path.resolve().as_posix(),
                "blocking": True,
                "required_gaps": [f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}"],
                "command": (
                    "ethos parity shadow --adopter generic "
                    f"--target {tmp_path.resolve().as_posix()} "
                    "--execute --write-evidence --json"
                ),
                "next_action": "refresh tracked shadow parity evidence",
            },
            "next_action": (
                "ethos parity shadow --adopter generic "
                f"--target {tmp_path.resolve().as_posix()} "
                "--execute --write-evidence --json"
            ),
        }
    ]


def test_parity_shadow_execute_reports_missing_embedded_backend(tmp_path: Path) -> None:
    payload = run_ethos(
        "parity",
        "shadow",
        "--target",
        str(tmp_path),
        "--execute",
        "--timeout-seconds",
        "5",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "different"
    embedded = payload["data"]["comparisons"][0]["embedded"]
    assert embedded["backend"] == {
        "kind": "missing",
        "command": "",
        "blocking": True,
        "required_gaps": ["embedded_backend_missing"],
    }
    assert "embedded_backend_missing" in payload["required_gaps"]
    assert any(gap.startswith("embedded_command_failed:") for gap in payload["required_gaps"])
    assert {package["gap"] for package in payload["data"]["execution_packages"]} == set(
        payload["required_gaps"]
    )


def test_embedded_shadow_runner_accepts_pixi_pyproject_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "adopter"
    target.mkdir()
    (target / "pyproject.toml").write_text(
        """
[tool.pixi.workspace]
channels = ["conda-forge"]
platforms = ["osx-arm64"]
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _run_embedded(target, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert result["backend"] == {
        "kind": "pixi",
        "command": "pixi run ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], target.resolve())]


def test_shadow_embedded_runner_accepts_pixi_task_in_pyproject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[tool.pixi.tasks]
ethos = "python -m ethos.cli"
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["backend"] == {
        "kind": "pixi",
        "command": "pixi run ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], repo.resolve())]


def test_shadow_embedded_runner_accepts_uv_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[tool.uv.workspace]
members = ["packages/ethos"]
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert result["backend"] == {
        "kind": "uv-workspace",
        "command": "uv run --package ethos ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [
        (["uv", "run", "--package", "ethos", "ethos", "status", "--json"], repo.resolve())
    ]


def test_external_shadow_runner_uses_cwd_for_commands_without_root_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "assistants doctor"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_external(tmp_path, ("assistants", "doctor"), timeout_seconds=5)

    assert calls[0][0][-3:] == ["assistants", "doctor", "--json"]
    assert "--root" not in calls[0][0]
    assert calls[0][1] == tmp_path.resolve()


def test_external_shadow_runner_uses_root_option_for_rooted_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_external(tmp_path, ("status",), timeout_seconds=5)

    assert calls[0][0][-3:] == ["--root", tmp_path.resolve().as_posix(), "--json"]
    assert calls[0][1] != tmp_path.resolve()


def test_shadow_json_verdict_exit_code_one_is_not_infrastructure_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text("", encoding="utf-8")
    payload = {"ok": False, "command": "status", "state": "blocked", "required_gaps": ["x"]}

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(shadow, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(subprocess, "run", fake_run)

    report = shadow.run_shadow_parity(repo, timeout_seconds=5)

    assert report["ok"] is True
    assert not any(gap.startswith("external_command_failed:") for gap in report["required_gaps"])
    assert not any(gap.startswith("embedded_command_failed:") for gap in report["required_gaps"])


def test_shadow_malformed_json_payload_is_process_failure() -> None:
    assert shadow._process_failed(
        {
            "exit_code": 0,
            "stdout": '{"error": "boom"}',
            "stderr": "",
            "json": {"error": "boom"},
        }
    )


def test_shadow_exit_code_above_one_is_process_failure_even_with_verdict() -> None:
    assert shadow._process_failed(
        {
            "exit_code": 2,
            "stdout": '{"ok": false, "command": "status", "required_gaps": []}',
            "stderr": "",
            "json": {"ok": False, "command": "status", "required_gaps": []},
        }
    )


def test_shadow_semantic_diff_compares_plan_gate_dimension() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 1},
        "data": {"required_gates": [{"id": "unit"}]},
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 0},
        "data": {"required_gates": []},
    }

    diff = shadow._semantic_diff(("plan", "--changed"), external, embedded)

    assert diff == {"required_gate_ids": {"external": ["unit"], "embedded": []}}


def test_shadow_status_projection_accepts_embedded_top_level_fields() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root", "dirty": False, "changed_paths": []},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "required_gaps": [],
        "role": "accepted_root",
        "dirty": False,
        "changed_paths": [],
    }

    assert shadow._semantic_diff(("status",), external, embedded) == {}


def test_shadow_report_projection_normalizes_missing_blocking_gap_count() -> None:
    external = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
    embedded = {
        "ok": True,
        "command": "report",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
        "scorecards": [{"id": "governance", "ok": True, "required_gaps": []}],
    }

    assert shadow._semantic_diff(("report",), external, embedded) == {}


def test_shadow_playbooks_projection_ignores_schema_specific_route_details() -> None:
    external = {
        "ok": True,
        "command": "playbooks route",
        "state": "routed",
        "required_gaps": [],
        "data": {"selected": [{"id": "repo-local-skill"}]},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "required_gaps": [],
        "route_hints": [],
    }

    assert shadow._semantic_diff(("playbooks", "route", "--changed"), external, embedded) == {}


def test_shadow_parse_failure_is_process_failure() -> None:
    result = {
        "exit_code": 0,
        "stdout": "not json",
        "stderr": "",
        "json": {},
    }

    assert shadow._process_failed(result) is True


def test_shadow_timeout_is_process_failure() -> None:
    result = {
        "exit_code": 124,
        "stdout": "",
        "stderr": "timeout",
        "json": {},
    }

    assert shadow._process_failed(result) is True


def test_shadow_semantic_diff_derives_state_for_minimal_status_payload() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root"},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "summary": {"dirty": False},
        "required_gaps": [],
        "role": "accepted_root",
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_plan_payload() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "summary": {"changed_path_count": 0},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_assistants_doctor_payload() -> None:
    external = {
        "ok": True,
        "command": "assistants doctor",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "assistants doctor",
        "summary": {"surface_count": 4},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_normalizes_ready_prove_against_minimal_payload() -> None:
    external = {
        "ok": True,
        "command": "prove",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "state": {},
        "required_gaps": [],
    }

    assert _semantic_diff(("prove",), external, embedded) == {}


@pytest.mark.parametrize(
    ("command", "external_state"),
    [
        ("prove", "gapped"),
        ("report", "gapped"),
        ("land", "dry_run"),
        ("publish", "dry_run"),
    ],
)
def test_shadow_semantic_diff_classifies_external_repository_audit_gaps_for_minimal_payload(
    command: str,
    external_state: str,
) -> None:
    external = {
        "ok": False,
        "command": command,
        "state": external_state,
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "claims_missing",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": [
                    "docs/architecture/product-ontology.md",
                    "claims_missing",
                ],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": command,
        "summary": {"command": command, "role": "accepted_root"},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_preserves_external_non_repository_audit_gaps() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "action_graph_invalid",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": ["docs/architecture/product-ontology.md"],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "summary": {"command": "prove"},
        "required_gaps": [],
    }

    diff = _semantic_diff(external, embedded)

    assert diff["ok"] == {"external": False, "embedded": True}
    assert diff["required_gaps"] == {"external": ["action_graph_invalid"], "embedded": []}


def test_shadow_semantic_diff_classifies_changed_route_noop() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "skill_missing_id",
            "playbook_route_missing:changed-scope",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "skill_missing_id",
                "playbook_route_missing:changed-scope",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_classifies_changed_route_noop_with_strict_activation_gap() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "playbook_activation_unsupported_version:1",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "playbook_activation_unsupported_version:1",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}
    assert _accepted_semantic_differences(external, embedded) == [
        {
            "kind": "changed_route_noop",
            "classification": "accepted",
            "scope": "changed_scope_route",
            "commands": ["ethos playbooks route"],
            "gaps": [
                "playbook_activation_unsupported_version:1",
                "skill_missing_id",
            ],
            "reason": "changed-scope route has no changed paths to route",
        }
    ]


def test_shadow_semantic_diff_classifies_report_parity_evidence_refresh_bootstrap() -> None:
    external = {
        "ok": False,
        "command": "report",
        "state": "gapped",
        "summary": {
            "score": 6,
            "max_score": 7,
            "governance_gap_count": 0,
            "parity_pending_count": 6,
        },
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "report",
        "state": "ready",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}
    accepted = _accepted_semantic_differences(external, embedded)
    assert accepted == [
        {
            "kind": "report_parity_evidence_refresh_bootstrap",
            "classification": "accepted",
            "scope": "parity_evidence_refresh",
            "commands": ["ethos report"],
            "gaps": ["parity_pending_count:6"],
            "reason": "report parity freshness is being refreshed by the current shadow run",
        }
    ]

    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
        },
        "comparisons": [
            {
                "command": "ethos report",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": external},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": embedded},
                "semantic_diff": {},
                "accepted_summary": {
                    "total_count": 1,
                    "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
                },
                "accepted_differences": accepted,
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_semantic_diff_preserves_changed_route_gap_when_paths_changed() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": ["playbook_route_missing:changed-scope"],
        "data": {"subject": "changed-scope"},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 1,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    diff = _semantic_diff(external, embedded)

    assert diff["required_gaps"] == {
        "external": ["playbook_route_missing:changed-scope"],
        "embedded": [],
    }


def test_shadow_accepted_difference_exposes_counts_and_command_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_external(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        if command == ("prove",):
            payload = {
                "ok": False,
                "command": "prove",
                "state": "gapped",
                "required_gaps": ["claims_missing"],
                "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
            }
        else:
            state_by_command = {
                "status": "ready",
                "plan": "planned",
                "report": "ready",
                "quality command-surface": "clean",
                "assistants doctor": "ready",
                "playbooks route": "routed",
                "land": "ready_to_land",
                "publish": "ready_to_publish",
            }
            payload = {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            }
        return {"exit_code": 0, "stdout": "", "stderr": "", "json": payload}

    def fake_embedded(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        state_by_command = {
            "status": "ready",
            "plan": "planned",
            "prove": "proven",
            "report": "ready",
            "quality command-surface": "clean",
            "assistants doctor": "ready",
            "playbooks route": "routed",
            "land": "ready_to_land",
            "publish": "ready_to_publish",
        }
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            },
        }

    monkeypatch.setattr("ethos.adapters.shadow._run_external", fake_external)
    monkeypatch.setattr("ethos.adapters.shadow._run_embedded", fake_embedded)

    payload = run_shadow_parity(tmp_path, timeout_seconds=5)

    assert payload["ok"] is True
    assert payload["accepted_summary"] == {
        "total_count": 1,
        "command_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    comparison = next(item for item in payload["comparisons"] if item["command"] == "ethos prove")
    assert comparison["accepted_summary"] == {
        "total_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    assert comparison["accepted_differences"] == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_accepted_difference_schema_rejects_unknown_kind() -> None:
    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"unknown": 1},
        },
        "comparisons": [
            {
                "command": "ethos prove",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "semantic_diff": {},
                "accepted_summary": {"total_count": 1, "kind_counts": {"unknown": 1}},
                "accepted_differences": [
                    {
                        "kind": "unknown",
                        "classification": "accepted",
                        "scope": "external_product_repository_audit",
                        "commands": ["ethos prove"],
                        "gaps": ["claims_missing"],
                        "reason": "invalid",
                    }
                ],
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_shadow_accepted_difference_has_stable_shape() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": ["claims_missing"],
        "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
    }
    embedded = {"ok": True, "command": "prove", "required_gaps": []}

    accepted = _accepted_semantic_differences(external, embedded)

    assert accepted == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]
