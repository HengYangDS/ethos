from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.adoption.retirement import retirement_readiness_report
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_table
from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_profile(
    root: Path,
    *,
    external_state: str,
    embedded_state: str,
    rollback: dict[str, object] | None = None,
) -> None:
    (root / ".ethos").mkdir(parents=True)
    (root / ".config").mkdir()
    (root / "docs/current/development/workflow").mkdir(parents=True)
    (root / "docs/evidence").mkdir(parents=True)
    (root / "claims").mkdir()
    (root / "rules").mkdir()
    (root / "openspec").mkdir()
    (root / ".agents/skills").mkdir(parents=True)
    (root / "docs/current/development/workflow/external-ethos-adoption.md").write_text(
        "# policy\n",
        encoding="utf-8",
    )
    rollback_table = ""
    if rollback is not None:
        (root / "docs/evidence/rollback-window.md").write_text(
            "# rollback window\n",
            encoding="utf-8",
        )
        completed_items = rollback.get("completed_scenarios", ())
        required_items = rollback.get("required_scenarios", ())
        completed = "\n".join(f'  "{item}",' for item in completed_items)
        required = "\n".join(f'  "{item}",' for item in required_items)
        rollback_table = (
            "\n[rollback_window]\n"
            f'state = "{rollback.get("state", "")}"\n'
            'evidence_manifest = "docs/evidence/rollback-window.md"\n'
            "completed_scenarios = [\n"
            f"{completed}\n"
            "]\n"
            "required_scenarios = [\n"
            f"{required}\n"
            "]\n"
        )
    (root / ".ethos/profile.toml").write_text(
        f'''schema_version = 1
profile_id = "sample"
profile_version = "1"
ethos_contract_version = "1"

[roots]
tool_config = ".config"
rules = "rules"
docs = "docs"
durable_evidence = "docs/evidence"
openspec = "openspec"
claims = "claims"
agent_skills = ".agents/skills"

[embedded_backend]
state = "{embedded_state}"
retirement_policy = "docs/current/development/workflow/external-ethos-adoption.md"

[external_backend]
state = "{external_state}"
minimum_version = "external>=embedded"
shadow_required = true
{rollback_table}
[adoption_boundary]
binding_manifest = ".ethos/profile.toml"
execution_config_root = ".config"
forbidden_external_product_roots = [
  "adopters/sample",
  "profiles/sample",
  "tests/fixtures/adopters/sample",
]
''',
        encoding="utf-8",
    )


def test_repository_profile_exposes_generic_tables(tmp_path: Path) -> None:
    _write_profile(tmp_path, external_state="adoption_preview", embedded_state="active")

    profile = load_repository_profile(tmp_path)

    assert profile.identity["profile_id"] == "sample"
    assert profile_table(tmp_path, "external_backend")["minimum_version"] == "external>=embedded"
    assert profile_table(tmp_path, "adoption_boundary")["execution_config_root"] == ".config"


def test_retirement_readiness_blocks_until_external_default_and_embedded_frozen(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(adopter, external_state="adoption_preview", embedded_state="active")
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


def test_retirement_readiness_rejects_product_core_adopter_directories(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback={
            "state": "complete",
            "completed_scenarios": (
                "proof_report",
                "work_lane_closeout",
                "domain_gate",
                "assistant_playbook",
            ),
        },
    )
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


def test_retirement_readiness_requires_rollback_window_evidence_for_terminal_state(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(adopter, external_state="retirement_ready", embedded_state="frozen_fallback")
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
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback={
            "state": "complete",
            "completed_scenarios": (
                "proof_report",
                "work_lane_closeout",
                "domain_gate",
                "assistant_playbook",
            ),
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

    assert report["ok"] is True
    assert report["state"] == "ready"
    assert report["required_gaps"] == []


def test_fleet_retirement_readiness_cli_reports_profile_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback={
            "state": "complete",
            "completed_scenarios": (
                "proof_report",
                "work_lane_closeout",
                "domain_gate",
                "assistant_playbook",
            ),
        },
    )

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
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(adopter, external_state="default", embedded_state="reference_only")
    (adopter / ".config").rmdir()
    profile_path = adopter / ".ethos/profile.toml"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8")
        .replace('execution_config_root = ".config"', 'execution_config_root = "tooling"')
        .replace('minimum_version = "external>=embedded"', 'minimum_version = "external<embedded"')
        .replace("shadow_required = true", "shadow_required = false")
        .replace(
            'retirement_policy = "docs/current/development/workflow/external-ethos-adoption.md"',
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
    assert "retirement_execution_config_root_not_config:tooling" in gaps
    assert "retirement_execution_config_root_missing:tooling" in gaps
    assert "retirement_external_minimum_version_not_ge_embedded" in gaps
    assert "retirement_shadow_not_required" in gaps
    assert "retirement_policy_path_missing:docs/missing.md" in gaps
    assert "retirement_parity:retirement_parity_not_clean" in gaps
    assert "retirement_shadow:retirement_shadow_not_matched" in gaps
    assert "retirement_shadow:retirement_shadow_false_negative_count:2" in gaps


def test_retirement_readiness_distinguishes_shadow_and_rollback_stages(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(adopter, external_state="rollback_window", embedded_state="frozen_fallback")
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
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    _write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback={
            "state": "complete",
            "completed_scenarios": (
                "proof_report",
                "work_lane_closeout",
                "domain_gate",
                "assistant_playbook",
            ),
        },
    )

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
    monkeypatch.setattr("ethos.adapters.shadow.run_shadow_parity", fake_run_shadow_parity)

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
