from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.adoption.retirement.core import retirement_readiness_report
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_table
from tests.support.ethos_cli_runner import run_ethos
from tests.unit.adoption.retirement.fixtures import STANDARD_ROLLBACK_SCENARIOS
from tests.unit.adoption.retirement.fixtures import git_add_all
from tests.unit.adoption.retirement.fixtures import git_head
from tests.unit.adoption.retirement.fixtures import init_git_repo
from tests.unit.adoption.retirement.fixtures import prepare_terminal_profile
from tests.unit.adoption.retirement.fixtures import terminal_report
from tests.unit.adoption.retirement.fixtures import terminal_rollback
from tests.unit.adoption.retirement.fixtures import write_profile

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _adopter_product(tmp_path: Path) -> tuple[Path, Path]:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    return adopter, product


def test_repository_profile_exposes_generic_tables(tmp_path: Path) -> None:
    write_profile(tmp_path, external_state="adoption_preview", embedded_state="active")

    profile = load_repository_profile(tmp_path)

    assert profile.identity["profile_id"] == "sample"
    assert profile_table(tmp_path, "external_backend")["minimum_version"] == "external>=embedded"
    assert profile_table(tmp_path, "adoption_boundary")["execution_config_root"] == ".config"


def test_retirement_readiness_blocks_until_external_default_and_embedded_frozen(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="adoption_preview", embedded_state="active")
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert "retirement_external_backend_not_default:adoption_preview" in report["required_gaps"]
    assert "retirement_embedded_backend_not_frozen:active" in report["required_gaps"]
    assert "retirement_lifecycle_incomplete:external_not_default" in report["required_gaps"]
    assert report["checks"]["binding"]["ok"] is True
    assert report["checks"]["product_boundary"]["ok"] is True


def test_retirement_readiness_next_actions_follow_current_stage(tmp_path: Path) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="adoption_preview",
        embedded_state="active_until_external_ge_embedded",
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["state"] == "external_not_default"
    assert not any("parity shadow" in action for action in report["next_actions"])
    assert report["next_actions"][:3] == [
        "switch adopter default backend to external under a reversible control",
        "freeze embedded backend as fallback/reference during rollback window",
        (
            f"ethos fleet retirement-readiness --target {adopter.as_posix()} "
            f"--root {product.as_posix()} --json"
        ),
    ]


def test_retirement_readiness_rejects_product_core_adopter_directories(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    git_add_all(adopter)
    (product / "adopters/sample").mkdir(parents=True)
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert "forbidden_external_product_root_present:adopters/sample" in report["required_gaps"]


def test_retirement_readiness_validates_declared_backend_control_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="adoption_preview",
        embedded_state="active_until_external_ge_embedded",
        control={"default_backend": "external", "external_backend": "default"},
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert report["checks"]["backend_control"]["ok"] is False
    assert (
        report["checks"]["backend_control"]["path"]
        == (adopter / ".config/interfaces/external-ethos-backend.toml").as_posix()
    )
    assert (
        "retirement_backend_control_default_mismatch:embedded:external" in report["required_gaps"]
    )
    assert (
        "retirement_backend_control_external_backend_mismatch:preview:default"
        in report["required_gaps"]
    )
    assert any("external-ethos-backend" in action for action in report["next_actions"])


def test_retirement_readiness_rejects_missing_backend_control_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="adoption_preview",
        embedded_state="active_until_external_ge_embedded",
        control={"write": False},
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["checks"]["backend_control"]["ok"] is False
    assert (
        "retirement_backend_control_missing:.config/interfaces/external-ethos-backend.toml"
        in report["required_gaps"]
    )


def test_retirement_readiness_rejects_backend_control_path_and_parse_gaps(
    tmp_path: Path,
) -> None:
    product = tmp_path / "product"
    product.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()
    write_profile(
        outside,
        external_state="default",
        embedded_state="reference_only",
        control={"path": "../external-ethos-backend.toml"},
    )
    outside_report = retirement_readiness_report(target=outside, product_root=product)

    assert (
        "retirement_backend_control_path_outside_repo:../external-ethos-backend.toml"
        in outside_report["required_gaps"]
    )
    assert outside_report["state"] == "backend_control_open"

    invalid = tmp_path / "invalid-control"
    invalid.mkdir()
    write_profile(
        invalid,
        external_state="default",
        embedded_state="reference_only",
        control={},
    )
    (invalid / ".config/interfaces/external-ethos-backend.toml").write_text(
        "[",
        encoding="utf-8",
    )
    invalid_report = retirement_readiness_report(target=invalid, product_root=product)

    assert (
        "retirement_backend_control_invalid:.config/interfaces/external-ethos-backend.toml"
        in invalid_report["required_gaps"]
    )


def test_retirement_readiness_reports_backend_control_contract_and_state_gaps(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="default",
        embedded_state="reference_only",
        control={
            "state": "adoption_preview",
            "default_backend": "embedded",
            "external_backend": "preview",
            "rollback_mode": "direct_flip",
        },
    )
    control_path = adopter / ".config/interfaces/external-ethos-backend.toml"
    control_path.write_text(
        control_path.read_text(encoding="utf-8")
        .replace('asset_kind = "ExternalEthosBackendSwitch"', 'asset_kind = "WrongKind"')
        .replace('profile_binding = ".ethos/profile.toml"', 'profile_binding = "other.toml"')
        .replace("repo_local_execution_wrapper = true", "repo_local_execution_wrapper = false"),
        encoding="utf-8",
    )

    report = retirement_readiness_report(target=adopter, product_root=product)

    gaps = report["required_gaps"]
    assert "retirement_backend_control_asset_kind_invalid:WrongKind" in gaps
    assert "retirement_backend_control_profile_binding_invalid:other.toml" in gaps
    assert "retirement_backend_control_state_mismatch:default:adoption_preview" in gaps
    assert "retirement_backend_control_default_mismatch:external:embedded" in gaps
    assert "retirement_backend_control_external_backend_mismatch:default:preview" in gaps
    assert "retirement_backend_control_rollback_mode_invalid:direct_flip" in gaps
    assert "retirement_backend_control_forbidden_not_true:repo_local_execution_wrapper" in gaps


def test_retirement_readiness_accepts_default_backend_control_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="default",
        embedded_state="reference_only",
        control={
            "state": "default",
            "default_backend": "external",
            "external_backend": "default",
        },
    )
    control_path = adopter / ".config/interfaces/external-ethos-backend.toml"
    control_path.write_text(
        f'{control_path.read_text(encoding="utf-8")}\n[rollback_window]\nstate = "planned"\n',
        encoding="utf-8",
    )

    report = retirement_readiness_report(target=adopter, product_root=product)

    assert report["checks"]["backend_control"]["ok"] is True
    assert not any(gap.startswith("retirement_backend_control_") for gap in report["required_gaps"])


def test_retirement_readiness_requires_backend_control_rollback_window_for_ready_state(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        control={"default_backend": "external", "external_backend": "default"},
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": "unknown", "adopter": "sample"}
    shadow = {
        "ok": False,
        "state": "different",
        "required_gaps": [],
        "false_negative_count": "not-a-number",
    }

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    gaps = report["required_gaps"]
    assert "retirement_backend_control_external_backend_mismatch:retirement_ready:default" in gaps
    assert "retirement_backend_control_rollback_window_not_declared" in gaps
    assert "retirement_shadow:retirement_shadow_not_matched" in gaps
    assert report["checks"]["parity"]["summary"]["pending_package_count"] == 0
    assert report["checks"]["shadow"]["summary"]["false_negative_count"] == 0


def test_retirement_readiness_requires_rollback_window_evidence_for_terminal_state(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="retirement_ready", embedded_state="frozen_fallback")
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert report["state"] == "rollback_window_evidence_open"
    assert "retirement_rollback_window_missing" in report["required_gaps"]
    assert "retirement_rollback_window_scenario_missing:proof_report" in report["required_gaps"]
    assert report["checks"]["rollback_window"]["applicable"] is True


def test_retirement_readiness_can_pass_when_profile_and_evidence_are_terminal(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)

    report = terminal_report(adopter, product)

    assert report["ok"] is True
    assert report["state"] == "ready"
    assert report["required_gaps"] == []


def test_retirement_readiness_blocks_generated_artifact_drift(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "report.json").write_text("{}\n", encoding="utf-8")
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert report["state"] == "generated_artifacts_open"
    assert (
        "retirement_generated_artifacts:generated_artifact_repo_root_drift:report.json"
        in report["required_gaps"]
    )
    assert report["checks"]["generated_artifacts"]["ok"] is False
    assert any("ethos quality generated-artifacts" in action for action in report["next_actions"])


def test_retirement_readiness_blocks_missing_docs_topology_kernel(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "docs/decisions/decision-code-links.md").unlink()
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert report["state"] == "docs_topology_open"
    assert (
        "retirement_docs_topology:docs_topology_missing:docs/decisions/decision-code-links.md"
        in report["required_gaps"]
    )
    assert report["checks"]["docs_topology"]["ok"] is False
    assert any("ethos quality docs-topology" in action for action in report["next_actions"])


def test_retirement_readiness_rejects_placeholder_rollback_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback={
            "state": "complete",
            "manifest": "placeholder",
            "completed_scenarios": STANDARD_ROLLBACK_SCENARIOS,
        },
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert any(
        gap.startswith("retirement_rollback_window_evidence_manifest_invalid:")
        for gap in report["required_gaps"]
    )


def test_retirement_readiness_rejects_rollback_manifest_outside_repo(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(
        tmp_path,
        rollback_overrides={"evidence_manifest": "../rollback-window.toml"},
    )

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_evidence_manifest_path_outside_repo:../rollback-window.toml"
    ) in report["required_gaps"]


def test_retirement_readiness_rejects_missing_rollback_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "docs/evidence/rollback-window.toml").unlink()
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_evidence_manifest_path_missing:"
        "docs/evidence/rollback-window.toml"
    ) in report["required_gaps"]


def test_retirement_readiness_rejects_unparseable_rollback_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "docs/evidence/rollback-window.toml").write_text("[", encoding="utf-8")
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_evidence_manifest_invalid:docs/evidence/rollback-window.toml"
    ) in report["required_gaps"]


def test_retirement_readiness_rejects_manifest_without_scenarios(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "docs/evidence/rollback-window.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                f'target_head = "{git_head(adopter)}"',
                f'product_head = "{git_head(product)}"',
            ]
        ),
        encoding="utf-8",
    )
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_evidence_manifest_invalid:docs/evidence/rollback-window.toml"
    ) in report["required_gaps"]
    assert (
        "retirement_rollback_window_manifest_scenario_missing:proof_report"
        in report["required_gaps"]
    )


def test_retirement_readiness_rejects_incomplete_scenario_bindings(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    (adopter / "docs/evidence/rollback-window.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                f'target_head = "{git_head(adopter)}"',
                f'product_head = "{git_head(product)}"',
                "",
                "[scenarios.proof_report]",
                'target_head = "different-target"',
                'product_head = "different-product"',
            ]
        ),
        encoding="utf-8",
    )
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_manifest_scenario_target_head_mismatch:proof_report"
        in report["required_gaps"]
    )
    assert (
        "retirement_rollback_window_manifest_scenario_product_head_mismatch:proof_report"
        in report["required_gaps"]
    )
    assert (
        "retirement_rollback_window_manifest_scenario_command_missing:proof_report"
        in report["required_gaps"]
    )
    assert (
        "retirement_rollback_window_manifest_scenario_digest_missing:proof_report"
        in report["required_gaps"]
    )
    assert (
        "retirement_rollback_window_manifest_scenario_evidence_missing:proof_report"
        in report["required_gaps"]
    )


def test_retirement_readiness_rejects_bad_scenario_evidence_paths(
    tmp_path: Path,
) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    manifest = adopter / "docs/evidence/rollback-window.toml"
    manifest.write_text(
        "\n".join(
            [
                "schema_version = 1",
                f'target_head = "{git_head(adopter)}"',
                f'product_head = "{git_head(product)}"',
                "",
                "[scenarios.proof_report]",
                f'target_head = "{git_head(adopter)}"',
                f'product_head = "{git_head(product)}"',
                'evidence = "../outside.json"',
                'command = "ethos prove"',
                'digest = "sha256:proof"',
                "",
                "[scenarios.work_lane_closeout]",
                f'target_head = "{git_head(adopter)}"',
                f'product_head = "{git_head(product)}"',
                'evidence = "docs/evidence/missing.json"',
                'command = "ethos land"',
                'digest = "sha256:land"',
            ]
        ),
        encoding="utf-8",
    )
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_manifest_scenario_evidence_outside_repo:proof_report"
        in report["required_gaps"]
    )
    assert (
        "retirement_rollback_window_manifest_scenario_evidence_path_missing:"
        "work_lane_closeout:docs/evidence/missing.json"
    ) in report["required_gaps"]


def test_retirement_readiness_requires_tracked_rollback_manifest(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert (
        "retirement_rollback_window_evidence_manifest_not_tracked:"
        "docs/evidence/rollback-window.toml"
    ) in report["required_gaps"]
    assert any(
        gap.startswith("retirement_rollback_window_manifest_scenario_evidence_not_tracked:")
        for gap in report["required_gaps"]
    )


def test_retirement_readiness_rejects_unreachable_rollback_heads(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    rollback = terminal_rollback(adopter, product)
    rollback["target_head"] = "0" * 40
    rollback["product_head"] = "1" * 40
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=rollback,
    )
    git_add_all(adopter)
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["ok"] is False
    assert (
        f"retirement_rollback_window_evidence_manifest_target_head_unreachable:{'0' * 40}"
    ) in report["required_gaps"]
    assert (
        f"retirement_rollback_window_evidence_manifest_product_head_unreachable:{'1' * 40}"
    ) in report["required_gaps"]


def test_fleet_retirement_readiness_cli_reports_profile_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    git_add_all(adopter)

    def fake_parity_gaps_report(**kwargs):
        assert kwargs["adopter"] == "sample"
        return {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}

    def fake_shadow_parity_report(**kwargs):
        assert kwargs["adopter"] == "sample"
        return {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    monkeypatch.setattr(
        "ethos.surface.cli.fleet.parity_gaps_report",
        fake_parity_gaps_report,
    )
    monkeypatch.setattr(
        "ethos.surface.cli.fleet.shadow_parity_report",
        fake_shadow_parity_report,
    )

    payload = run_ethos(
        "fleet",
        "retirement-readiness",
        "--target",
        adopter.as_posix(),
        "--root",
        product.as_posix(),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["summary"] == {"adopter": "sample", "gap_count": 0}
    assert payload["data"]["checks"]["product_boundary"]["ok"] is True


def test_retirement_readiness_reports_missing_and_invalid_profiles(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    product = tmp_path / "product"
    missing.mkdir()
    product.mkdir()

    missing_report = retirement_readiness_report(target=missing, product_root=product)

    assert "retirement_profile_missing:.ethos/profile.toml" in missing_report["required_gaps"]
    assert (
        "retirement_binding_manifest_missing:.ethos/profile.toml" in missing_report["required_gaps"]
    )
    assert "retirement_execution_config_root_missing:.config" in missing_report["required_gaps"]

    invalid = tmp_path / "invalid"
    (invalid / ".ethos").mkdir(parents=True)
    (invalid / ".ethos/profile.toml").write_text("[", encoding="utf-8")

    invalid_report = retirement_readiness_report(target=invalid, product_root=product)

    assert "retirement_profile_invalid:.ethos/profile.toml" in invalid_report["required_gaps"]


def test_retirement_readiness_reports_binding_and_backend_contract_gaps(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="default", embedded_state="reference_only")
    (adopter / ".config").rmdir()
    profile_path = adopter / ".ethos/profile.toml"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8")
        .replace('binding_manifest = ".ethos/profile.toml"', 'binding_manifest = "profile.toml"')
        .replace('execution_config_root = ".config"', 'execution_config_root = "tooling"')
        .replace('minimum_version = "external>=embedded"', 'minimum_version = "external<embedded"')
        .replace("shadow_required = true", "shadow_required = false")
        .replace(
            'retirement_policy = "docs/governance/external-ethos-adoption.md"',
            'retirement_policy = "docs/missing.md"',
        ),
        encoding="utf-8",
    )
    parity = {"ok": False, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {
        "ok": False,
        "state": "different",
        "required_gaps": [],
        "false_negative_count": "2",
    }

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    gaps = report["required_gaps"]
    assert "retirement_binding_manifest_not_generic:profile.toml" in gaps
    assert "retirement_binding_manifest_missing:profile.toml" in gaps
    assert "retirement_execution_config_root_not_config:tooling" in gaps
    assert "retirement_execution_config_root_missing:tooling" in gaps
    assert "retirement_external_minimum_version_not_ge_embedded" in gaps
    assert "retirement_shadow_not_required" in gaps
    assert "retirement_policy_path_missing:docs/missing.md" in gaps
    assert "retirement_parity:retirement_parity_not_clean" in gaps
    assert "retirement_shadow:retirement_shadow_not_matched" in gaps
    assert "retirement_shadow:retirement_shadow_false_negative_count:2" in gaps


def test_retirement_readiness_reports_embedded_not_frozen_stage(tmp_path: Path) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="default", embedded_state="active")
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    report = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )

    assert report["state"] == "embedded_not_frozen"
    assert "retirement_lifecycle_incomplete:embedded_not_frozen" in report["required_gaps"]


def test_retirement_readiness_distinguishes_shadow_and_rollback_stages(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="rollback_window", embedded_state="frozen_fallback")
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}

    shadow_open = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow={"ok": False, "state": "different", "required_gaps": ["x"]},
    )
    rollback = retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow={"ok": True, "state": "matched", "required_gaps": []},
    )

    assert shadow_open["state"] == "shadow_open"
    assert "retirement_lifecycle_incomplete:shadow_open" in shadow_open["required_gaps"]
    assert rollback["state"] == "rollback_window_evidence_open"
    assert "retirement_lifecycle_incomplete:rollback_window" in rollback["required_gaps"]
    assert any("[rollback_window]" in item for item in rollback["next_actions"])


def test_fleet_retirement_readiness_execute_shadow_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    git_add_all(adopter)

    def fake_parity_gaps_report(**kwargs):
        return {
            "ok": True,
            "required_gaps": [],
            "pending_packages": [],
            "adopter": kwargs["adopter"],
        }

    def fake_run_shadow_parity(**kwargs):
        assert kwargs["target"] == adopter
        assert kwargs["product_root"] == product
        return {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}

    monkeypatch.setattr("ethos.surface.cli.fleet.parity_gaps_report", fake_parity_gaps_report)
    monkeypatch.setattr("ethos.adapters.shadow.core.run_shadow_parity", fake_run_shadow_parity)

    payload = run_ethos(
        "fleet",
        "retirement-readiness",
        "--target",
        adopter.as_posix(),
        "--root",
        product.as_posix(),
        "--execute-shadow",
        "--json",
    )

    assert payload["ok"] is True
