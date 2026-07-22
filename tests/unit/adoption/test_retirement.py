from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock

import pytest
import tomli_w

from ethos.repository.adoption.retirement.core import retirement_readiness_report
from ethos.repository.adoption.retirement.rollback import rollback_manifest_gaps
from tests.support.ethos_cli_runner import run_ethos
from tests.unit.adoption.retirement.fixtures import CLEAN_PARITY
from tests.unit.adoption.retirement.fixtures import CLEAN_SHADOW
from tests.unit.adoption.retirement.fixtures import CONTROL_PATH
from tests.unit.adoption.retirement.fixtures import STANDARD_ROLLBACK_SCENARIOS
from tests.unit.adoption.retirement.fixtures import git
from tests.unit.adoption.retirement.fixtures import git_add_all
from tests.unit.adoption.retirement.fixtures import init_git_repo
from tests.unit.adoption.retirement.fixtures import prepare_terminal_profile
from tests.unit.adoption.retirement.fixtures import terminal_report
from tests.unit.adoption.retirement.fixtures import terminal_rollback
from tests.unit.adoption.retirement.fixtures import write_profile

if TYPE_CHECKING:
    from pathlib import Path

MANIFEST_PATH = "docs/evidence/rollback-window.toml"


def _adopter_product(tmp_path: Path) -> tuple[Path, Path]:
    adopter, product = tmp_path / "adopter", tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    return adopter, product


def _readiness(
    adopter: Path,
    product: Path,
    *,
    parity: dict[str, object] | None = None,
    shadow: dict[str, object] | None = None,
) -> dict[str, object]:
    return retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=CLEAN_PARITY if parity is None else parity,
        shadow=CLEAN_SHADOW if shadow is None else shadow,
    )


def _assert_gaps(report: dict[str, object], *expected: str) -> None:
    gaps = cast("list[str]", report["required_gaps"])
    assert all(gap in gaps for gap in expected)


def test_retirement_readiness_reports_initial_stage_and_actions(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter,
        external_state="adoption_preview",
        embedded_state="active_until_external_ge_embedded",
    )

    report = _readiness(adopter, product)

    assert report["ok"] is False
    assert report["state"] == "external_not_default"
    _assert_gaps(
        report,
        "retirement_external_backend_not_default:adoption_preview",
        "retirement_embedded_backend_not_frozen:active_until_external_ge_embedded",
        "retirement_lifecycle_incomplete:external_not_default",
    )
    actions = cast("list[str]", report["next_actions"])
    assert not any("parity shadow" in action for action in actions)
    assert actions[:3] == [
        "switch adopter default backend to external under a reversible control",
        "freeze embedded backend as fallback/reference during rollback window",
        f"ethos fleet retirement-readiness --target {adopter.as_posix()} "
        f"--root {product.as_posix()} --json",
    ]


@pytest.mark.parametrize(
    (
        "states",
        "control",
        "expected_gaps",
    ),
    [
        pytest.param(
            ("adoption_preview", "active_until_external_ge_embedded", ""),
            {"default_backend": "external", "external_backend": "default"},
            (
                "retirement_backend_control_default_mismatch:embedded:external",
                "retirement_backend_control_external_backend_mismatch:preview:default",
            ),
            id="preview-mismatch",
        ),
        pytest.param(
            ("adoption_preview", "active_until_external_ge_embedded", ""),
            {"write": False},
            (f"retirement_backend_control_missing:{CONTROL_PATH}",),
            id="missing-manifest",
        ),
        pytest.param(
            ("default", "reference_only", "planned"),
            {
                "state": "default",
                "default_backend": "external",
                "external_backend": "default",
            },
            (),
            id="valid-default",
        ),
    ],
)
def test_retirement_readiness_validates_backend_control_partitions(
    tmp_path: Path,
    states: tuple[str, str, str],
    control: dict[str, object],
    expected_gaps: tuple[str, ...],
) -> None:
    external_state, embedded_state, rollback_state = states
    adopter, product = _adopter_product(tmp_path)
    write_profile(
        adopter, external_state=external_state, embedded_state=embedded_state, control=control
    )
    control_path = adopter / CONTROL_PATH
    if rollback_state:
        control_path.write_text(
            f'{control_path.read_text(encoding="utf-8")}\n[rollback_window]\nstate = "planned"\n',
            encoding="utf-8",
        )

    report = _readiness(adopter, product)

    checks = cast("dict[str, dict[str, object]]", report["checks"])
    control_ok = not expected_gaps
    assert checks["backend_control"]["ok"] is control_ok
    assert checks["backend_control"]["path"] == control_path.as_posix()
    _assert_gaps(report, *expected_gaps)
    if control_ok:
        assert not any(
            gap.startswith("retirement_backend_control_")
            for gap in cast("list[str]", report["required_gaps"])
        )
    else:
        assert any(
            "external-ethos-backend" in action
            for action in cast("list[str]", report["next_actions"])
        )


def test_retirement_readiness_reports_backend_control_parse_contract_and_state_gaps(
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
    control_path = adopter / CONTROL_PATH
    control_path.write_text(
        control_path.read_text(encoding="utf-8")
        .replace('asset_kind = "ExternalEthosBackendSwitch"', 'asset_kind = "WrongKind"')
        .replace('profile_binding = ".ethos/profile.toml"', 'profile_binding = "other.toml"')
        .replace("repo_local_execution_wrapper = true", "repo_local_execution_wrapper = false"),
        encoding="utf-8",
    )

    _assert_gaps(
        _readiness(adopter, product),
        "retirement_backend_control_asset_kind_invalid:WrongKind",
        "retirement_backend_control_profile_binding_invalid:other.toml",
        "retirement_backend_control_state_mismatch:default:adoption_preview",
        "retirement_backend_control_default_mismatch:external:embedded",
        "retirement_backend_control_external_backend_mismatch:default:preview",
        "retirement_backend_control_rollback_mode_invalid:direct_flip",
        "retirement_backend_control_forbidden_not_true:repo_local_execution_wrapper",
    )
    control_path.write_text("[", encoding="utf-8")
    _assert_gaps(_readiness(adopter, product), f"retirement_backend_control_invalid:{CONTROL_PATH}")


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
    report = _readiness(
        adopter,
        product,
        parity={"ok": True, "required_gaps": [], "pending_packages": "unknown"},
        shadow={
            "ok": False,
            "state": "different",
            "required_gaps": [],
            "false_negative_count": "x",
        },
    )

    _assert_gaps(
        report,
        "retirement_backend_control_external_backend_mismatch:retirement_ready:default",
        "retirement_backend_control_rollback_window_not_declared",
        "retirement_shadow:retirement_shadow_not_matched",
    )
    checks = cast("dict[str, dict[str, object]]", report["checks"])
    assert cast("dict[str, object]", checks["parity"]["summary"])["pending_package_count"] == 0
    assert cast("dict[str, object]", checks["shadow"]["summary"])["false_negative_count"] == 0


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        pytest.param(
            ("report.json", "{}\n"),
            (
                "generated_artifacts_open",
                "retirement_generated_artifacts:generated_artifact_repo_root_drift:report.json",
                "generated_artifacts",
                "ethos quality generated-artifacts",
            ),
            id="generated-artifact",
        ),
        pytest.param(
            ("docs/decisions/decision-code-links.md", None),
            (
                "docs_topology_open",
                "retirement_docs_topology:docs_topology_missing:docs/decisions/decision-code-links.md",
                "docs_topology",
                "ethos quality docs-topology",
            ),
            id="docs-topology",
        ),
    ],
)
def test_retirement_readiness_blocks_repository_drift(
    tmp_path: Path,
    mutation: tuple[str, str | None],
    expected: tuple[str, str, str, str],
) -> None:
    (path, content), (state, gap, check, action) = mutation, expected
    adopter, product = prepare_terminal_profile(tmp_path)
    target = adopter / path
    target.unlink() if content is None else target.write_text(content, encoding="utf-8")
    git_add_all(adopter)

    report = terminal_report(adopter, product)

    assert report["state"] == state
    _assert_gaps(report, gap)
    checks = cast("dict[str, dict[str, object]]", report["checks"])
    assert checks[check]["ok"] is False
    assert any(action in item for item in cast("list[str]", report["next_actions"]))


def test_rollback_manifest_gaps_rejects_path_and_parse_failures(tmp_path: Path) -> None:
    check = partial(
        rollback_manifest_gaps,
        repo=tmp_path,
        product=tmp_path,
        required_scenarios=[],
    )
    assert check(evidence_manifest="../rollback-window.toml") == [
        "retirement_rollback_window_evidence_manifest_path_outside_repo:../rollback-window.toml"
    ]
    missing = check(evidence_manifest=MANIFEST_PATH)
    assert missing == [f"retirement_rollback_window_evidence_manifest_path_missing:{MANIFEST_PATH}"]
    manifest = tmp_path / MANIFEST_PATH
    manifest.parent.mkdir(parents=True)
    invalid = f"retirement_rollback_window_evidence_manifest_invalid:{MANIFEST_PATH}"
    manifest.write_text("[", encoding="utf-8")
    assert invalid in check(evidence_manifest=MANIFEST_PATH)
    manifest.write_text("target_head = 'x'\nproduct_head = 'x'\nscenarios = []\n", encoding="utf-8")
    assert invalid in check(evidence_manifest=MANIFEST_PATH)


def test_rollback_manifest_gaps_reports_binding_and_git_failures(tmp_path: Path) -> None:
    adopter, product = _adopter_product(tmp_path)
    init_git_repo(adopter)
    init_git_repo(product)
    evidence = adopter / "docs/evidence/untracked.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    target, product_head = "0" * 40, "1" * 40
    complete = {"target_head": target, "product_head": product_head, "command": "x", "digest": "x"}
    manifest = adopter / MANIFEST_PATH
    manifest_text = tomli_w.dumps(
        {
            "schema_version": 1,
            "target_head": target,
            "product_head": product_head,
            "scenarios": {
                "proof_report": {
                    "target_head": "different-target",
                    "product_head": "different-product",
                },
                "work_lane_closeout": complete | {"evidence": "../outside.json"},
                "domain_gate": complete | {"evidence": "docs/evidence/missing.json"},
                "assistant_playbook": complete | {"evidence": "docs/evidence/untracked.json"},
            },
        }
    )
    manifest.write_text(manifest_text, encoding="utf-8")
    gaps = rollback_manifest_gaps(
        repo=adopter,
        product=product,
        evidence_manifest=MANIFEST_PATH,
        required_scenarios=[*STANDARD_ROLLBACK_SCENARIOS, "missing_scenario"],
    )
    assert all(
        gap in gaps
        for gap in (
            f"retirement_rollback_window_evidence_manifest_not_tracked:{MANIFEST_PATH}",
            f"retirement_rollback_window_evidence_manifest_target_head_unreachable:{target}",
            f"retirement_rollback_window_evidence_manifest_product_head_unreachable:{product_head}",
            "retirement_rollback_window_manifest_scenario_target_head_mismatch:proof_report",
            "retirement_rollback_window_manifest_scenario_product_head_mismatch:proof_report",
            "retirement_rollback_window_manifest_scenario_command_missing:proof_report",
            "retirement_rollback_window_manifest_scenario_digest_missing:proof_report",
            "retirement_rollback_window_manifest_scenario_evidence_missing:proof_report",
            "retirement_rollback_window_manifest_scenario_evidence_outside_repo:work_lane_closeout",
            "retirement_rollback_window_manifest_scenario_evidence_path_missing:"
            "domain_gate:docs/evidence/missing.json",
            "retirement_rollback_window_manifest_scenario_evidence_not_tracked:"
            "assistant_playbook:docs/evidence/untracked.json",
            "retirement_rollback_window_manifest_scenario_missing:missing_scenario",
        )
    )
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    git_add_all(adopter)
    manifest.write_text(manifest_text, encoding="utf-8")
    _assert_gaps(
        _readiness(adopter, product),
        f"retirement_rollback_window_evidence_manifest_target_head_unreachable:{target}",
    )


@pytest.mark.parametrize("shadow_mode", ["read-existing", "execute"])
def test_fleet_retirement_readiness_cli_reports_terminal_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shadow_mode: str,
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

    parity = Mock(return_value=CLEAN_PARITY)
    read_shadow = Mock(return_value=CLEAN_SHADOW)
    execute_shadow = Mock(return_value=CLEAN_SHADOW)
    monkeypatch.setattr("ethos.surface.cli.fleet.parity_gaps_report", parity)
    monkeypatch.setattr("ethos.surface.cli.fleet.shadow_parity_report", read_shadow)
    monkeypatch.setattr("ethos.adapters.shadow.core.run_shadow_parity", execute_shadow)
    args = [
        "fleet",
        "retirement-readiness",
        "--target",
        adopter.as_posix(),
        "--root",
        product.as_posix(),
    ]
    if shadow_mode == "execute":
        args.append("--execute-shadow")

    payload = run_ethos(*args, "--json")

    if shadow_mode == "execute":
        execute_shadow.assert_called_once_with(
            target=adopter,
            timeout_seconds=30,
            product_root=product,
        )
        read_shadow.assert_not_called()
    else:
        read_shadow.assert_called_once()
        execute_shadow.assert_not_called()
        shadow_args = read_shadow.call_args.kwargs
        assert shadow_args["adopter"] == "sample"
        assert shadow_args["root"] == product
        assert shadow_args["target"] == adopter
        assert shadow_args["current_target_head"] == git(adopter, "rev-parse", "HEAD")
        assert shadow_args["current_product_head"] == git(product, "rev-parse", "HEAD")
        assert shadow_args["current_target_head"] in shadow_args["acceptable_target_heads"]
        assert shadow_args["current_product_head"] in shadow_args["acceptable_product_heads"]
    assert parity.call_args.kwargs["adopter"] == "sample"
    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["summary"] == {"adopter": "sample", "gap_count": 0}
    assert payload["data"]["checks"]["product_boundary"]["ok"] is True


def test_retirement_readiness_reports_binding_and_backend_contract_gaps(
    tmp_path: Path,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state="default", embedded_state="reference_only")
    (adopter / ".config").rmdir()
    (product / "adopters/sample").mkdir(parents=True)
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

    _assert_gaps(
        _readiness(
            adopter,
            product,
            parity={"ok": False, "required_gaps": [], "pending_packages": []},
            shadow={
                "ok": False,
                "state": "different",
                "required_gaps": [],
                "false_negative_count": "2",
            },
        ),
        "retirement_binding_manifest_not_generic:profile.toml",
        "retirement_binding_manifest_missing:profile.toml",
        "retirement_execution_config_root_not_config:tooling",
        "retirement_execution_config_root_missing:tooling",
        "retirement_external_minimum_version_not_ge_embedded",
        "retirement_shadow_not_required",
        "retirement_policy_path_missing:docs/missing.md",
        "retirement_parity:retirement_parity_not_clean",
        "retirement_shadow:retirement_shadow_not_matched",
        "retirement_shadow:retirement_shadow_false_negative_count:2",
        "forbidden_external_product_root_present:adopters/sample",
    )
    missing = tmp_path / "missing"
    missing.mkdir()
    _assert_gaps(
        retirement_readiness_report(target=missing, product_root=product),
        "retirement_profile_missing:.ethos/profile.toml",
        "retirement_binding_manifest_missing:.ethos/profile.toml",
        "retirement_execution_config_root_missing:.config",
    )
    malformed = missing / ".ethos/profile.toml"
    malformed.parent.mkdir()
    malformed.write_text("[", encoding="utf-8")
    _assert_gaps(
        retirement_readiness_report(target=missing, product_root=product),
        "retirement_profile_invalid:.ethos/profile.toml",
    )


@pytest.mark.parametrize(
    ("external_state", "embedded_state", "shadow", "stage"),
    [
        pytest.param(
            "default",
            "active",
            None,
            "embedded_not_frozen",
            id="embedded-active",
        ),
        pytest.param(
            "rollback_window",
            "frozen_fallback",
            {"ok": False, "state": "different", "required_gaps": ["x"]},
            "shadow_open",
            id="shadow-open",
        ),
        pytest.param(
            "rollback_window",
            "frozen_fallback",
            None,
            "rollback_window",
            id="rollback-window",
        ),
    ],
)
def test_retirement_readiness_distinguishes_lifecycle_stages(
    tmp_path: Path,
    external_state: str,
    embedded_state: str,
    shadow: dict[str, object] | None,
    stage: str,
) -> None:
    adopter, product = _adopter_product(tmp_path)
    write_profile(adopter, external_state=external_state, embedded_state=embedded_state)

    report = _readiness(adopter, product, shadow=shadow)

    expected_state = "rollback_window_evidence_open" if stage == "rollback_window" else stage
    assert report["state"] == expected_state
    _assert_gaps(report, f"retirement_lifecycle_incomplete:{stage}")
    if stage == "rollback_window":
        _assert_gaps(
            report,
            "retirement_rollback_window_missing",
            "retirement_rollback_window_scenario_missing:proof_report",
        )
        checks = cast("dict[str, dict[str, object]]", report["checks"])
        assert checks["rollback_window"]["applicable"] is True
        assert any(
            "[rollback_window]" in item for item in cast("list[str]", report["next_actions"])
        )
