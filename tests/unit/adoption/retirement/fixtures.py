from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import tomli_w

from ethos.repository.adoption.retirement.core import retirement_readiness_report

if TYPE_CHECKING:
    from pathlib import Path

STANDARD_ROLLBACK_SCENARIOS = tuple(
    "proof_report\nwork_lane_closeout\ndomain_gate\nassistant_playbook".splitlines()
)
CLEAN_PARITY = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
CLEAN_SHADOW = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}
CONTROL_PATH = ".config/interfaces/external-ethos-backend.toml"
DOC_PATHS = tuple(
    f"docs/{path}"
    for path in (
        "README.md\nindex.md\nstart/quickstart.md\ngovernance/README.md\ndecisions/README.md\n"
        "decisions/decision-index.md\ndecisions/decision-dependency-map.md\n"
        "decisions/decision-code-links.md\ndecisions/accepted/README.md\n"
        "decisions/superseded/README.md\ndecisions/templates/README.md\n"
        "decisions/templates/decision-record.md\nevidence/README.md\nplans/README.md\n"
        "history/README.md\nreference/README.md"
    ).splitlines()
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_toml(path: Path, data: dict[str, object]) -> None:
    _write(path, tomli_w.dumps(data))


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", root.as_posix(), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "-C", root.as_posix(), "init", "-q"], check=True)
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test User")
    git(root, "commit", "--allow-empty", "-q", "-m", "initial")


def git_add_all(root: Path) -> None:
    subprocess.run(["git", "-C", root.as_posix(), "add", "-A"], check=True)


def terminal_rollback(adopter: Path, product: Path) -> dict[str, object]:
    return {
        "state": "complete",
        "completed_scenarios": STANDARD_ROLLBACK_SCENARIOS,
        "target_head": git(adopter, "rev-parse", "HEAD"),
        "product_head": git(product, "rev-parse", "HEAD"),
    }


def prepare_terminal_profile(tmp_path: Path) -> tuple[Path, Path]:
    adopter, product = tmp_path / "adopter", tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    init_git_repo(adopter)
    init_git_repo(product)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=terminal_rollback(adopter, product),
    )
    git_add_all(adopter)
    return adopter, product


def terminal_report(adopter: Path, product: Path) -> dict[str, object]:
    return retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=CLEAN_PARITY,
        shadow=CLEAN_SHADOW,
    )


def _write_control(root: Path, external_state: str, control: dict[str, object]) -> None:
    if control.get("write", True):
        _write_toml(
            root / CONTROL_PATH,
            {
                "contract": {
                    "asset_kind": "ExternalEthosBackendSwitch",
                    "profile_binding": ".ethos/profile.toml",
                },
                "current": {
                    "state": control.get("state", external_state),
                    "default_backend": control.get("default_backend", "embedded"),
                    "external_backend": control.get("external_backend", "preview"),
                    "rollback_mode": control.get("rollback_mode", "embedded_fallback"),
                },
                "forbidden": dict.fromkeys(
                    (
                        "repo_local_execution_wrapper",
                        "config_script_home",
                        "adopter_named_external_product_root",
                        "default_flip_without_rollback_window",
                    ),
                    True,
                ),
            },
        )


def _write_rollback(root: Path, rollback: dict[str, object]) -> dict[str, object]:
    relative = "docs/evidence/rollback-window.toml"
    completed = tuple(cast for cast in rollback.get("completed_scenarios", ()))
    target = str(rollback.get("target_head") or "")
    product = str(rollback.get("product_head") or "")
    scenarios: dict[str, object] = {}
    for scenario in completed:
        evidence = f"docs/evidence/rollback-window/{scenario}.json"
        _write(root / evidence, "{}\n")
        scenarios[str(scenario)] = {
            "target_head": target,
            "product_head": product,
            "evidence": evidence,
            "command": f"ethos {scenario}",
            "digest": f"sha256:{scenario}",
        }
    _write_toml(
        root / relative,
        {
            "schema_version": 1,
            "target_head": target,
            "product_head": product,
            "scenarios": scenarios,
        },
    )
    return {
        "state": rollback.get("state", ""),
        "evidence_manifest": relative,
        "completed_scenarios": list(completed),
    }


def write_profile(
    root: Path,
    *,
    external_state: str,
    embedded_state: str,
    rollback: dict[str, object] | None = None,
    control: dict[str, object] | None = None,
) -> None:
    for relative in (".ethos", ".config", "claims", "rules", "openspec", ".agents/skills"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in DOC_PATHS:
        _write(root / relative, "---\nstate: canonical\n---\n# Test\n")
    _write(root / "docs/governance/external-ethos-adoption.md", "# policy\n")
    external: dict[str, object] = {
        "state": external_state,
        "minimum_version": "external>=embedded",
        "shadow_required": True,
    }
    if control is not None:
        external["control"] = CONTROL_PATH
        _write_control(root, external_state, control)
    profile: dict[str, object] = {
        "profile_id": "sample",
        "roots": {
            "rules": "rules",
            "docs": "docs",
            "durable_evidence": "docs/evidence",
            "openspec": "openspec",
            "claims": "claims",
            "agent_skills": ".agents/skills",
        },
        "openspec": {"material_paths": [".ethos/profile.toml"]},
        "embedded_backend": {
            "state": embedded_state,
            "retirement_policy": "docs/governance/external-ethos-adoption.md",
        },
        "external_backend": external,
        "adoption_boundary": {
            "binding_manifest": ".ethos/profile.toml",
            "execution_config_root": ".config",
            "forbidden_external_product_roots": [
                "adopters/sample",
                "profiles/sample",
                "tests/fixtures/adopters/sample",
            ],
        },
    }
    if rollback is not None:
        profile["rollback_window"] = _write_rollback(root, rollback)
    _write_toml(root / ".ethos/profile.toml", profile)
