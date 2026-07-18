from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.repository.adoption.retirement.core import retirement_readiness_report

if TYPE_CHECKING:
    from pathlib import Path

STANDARD_ROLLBACK_SCENARIOS = (
    "proof_report",
    "work_lane_closeout",
    "domain_gate",
    "assistant_playbook",
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", root.as_posix(), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "-C", root.as_posix(), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", root.as_posix(), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", root.as_posix(), "config", "user.name", "Test User"], check=True)
    subprocess.run(
        ["git", "-C", root.as_posix(), "commit", "--allow-empty", "-q", "-m", "initial"],
        check=True,
    )


def git_head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD")


def git_add_all(root: Path) -> None:
    subprocess.run(["git", "-C", root.as_posix(), "add", "-A"], check=True)


def terminal_rollback(adopter: Path, product: Path) -> dict[str, object]:
    return {
        "state": "complete",
        "completed_scenarios": STANDARD_ROLLBACK_SCENARIOS,
        "target_head": git_head(adopter),
        "product_head": git_head(product),
    }


def prepare_terminal_profile(
    tmp_path: Path, *, rollback_overrides: dict[str, object] | None = None
) -> tuple[Path, Path]:
    adopter = tmp_path / "adopter"
    product = tmp_path / "product"
    adopter.mkdir()
    product.mkdir()
    init_git_repo(adopter)
    init_git_repo(product)
    rollback = terminal_rollback(adopter, product)
    if rollback_overrides:
        rollback.update(rollback_overrides)
    write_profile(
        adopter,
        external_state="retirement_ready",
        embedded_state="frozen_fallback",
        rollback=rollback,
    )
    git_add_all(adopter)
    return adopter, product


def terminal_report(adopter: Path, product: Path) -> dict[str, object]:
    parity = {"ok": True, "required_gaps": [], "pending_packages": [], "adopter": "sample"}
    shadow = {"ok": True, "state": "matched", "required_gaps": [], "false_negative_count": 0}
    return retirement_readiness_report(
        target=adopter,
        product_root=product,
        parity_gaps=parity,
        shadow=shadow,
    )


def write_docs_kernel(root: Path) -> None:
    entries = {
        "docs/README.md": "# Docs",
        "docs/index.md": "# Docs Index",
        "docs/start/quickstart.md": "# Quickstart",
        "docs/governance/README.md": "# Governance",
        "docs/decisions/README.md": "# Decisions",
        "docs/decisions/decision-index.md": "# Decision Index",
        "docs/decisions/decision-dependency-map.md": "# Decision Dependency Map",
        "docs/decisions/decision-code-links.md": "# Decision Code Links",
        "docs/decisions/accepted/README.md": "# Accepted Decisions",
        "docs/decisions/superseded/README.md": "# Superseded Decisions",
        "docs/decisions/templates/README.md": "# Decision Templates",
        "docs/decisions/templates/decision-record.md": "# Decision Record Template",
        "docs/evidence/README.md": "# Evidence",
        "docs/plans/README.md": "# Plans",
        "docs/history/README.md": "# History",
        "docs/reference/README.md": "# Reference",
    }
    for relative, content in entries.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nstate: canonical\n---\n{content}\n", encoding="utf-8")


def write_profile(
    root: Path,
    *,
    external_state: str,
    embedded_state: str,
    rollback: dict[str, object] | None = None,
    control: dict[str, object] | None = None,
) -> None:
    (root / ".ethos").mkdir(parents=True)
    (root / ".config").mkdir()
    write_docs_kernel(root)
    (root / "claims").mkdir()
    (root / "rules").mkdir()
    (root / "openspec").mkdir()
    (root / ".agents/skills").mkdir(parents=True)
    (root / "docs/governance/external-ethos-adoption.md").write_text(
        "# policy\n",
        encoding="utf-8",
    )
    control_line = ""
    if control is not None:
        control_path = str(control.get("path") or ".config/interfaces/external-ethos-backend.toml")
        control_line = f'control = "{control_path}"\n'
        if control.get("write", True):
            control_file = root / control_path
            control_file.parent.mkdir(parents=True, exist_ok=True)
            control_file.write_text(
                "\n".join(
                    [
                        "[contract]",
                        'asset_kind = "ExternalEthosBackendSwitch"',
                        'truth_boundary = "configuration only"',
                        'profile_binding = ".ethos/profile.toml"',
                        "",
                        "[current]",
                        f'state = "{control.get("state", external_state)}"',
                        f'default_backend = "{control.get("default_backend", "embedded")}"',
                        f'external_backend = "{control.get("external_backend", "preview")}"',
                        f'rollback_mode = "{control.get("rollback_mode", "embedded_fallback")}"',
                        "",
                        "[allowed_transitions]",
                        'preview_to_reversible_default_requires = ["shadow_parity_clean", "embedded_fallback_available"]',
                        'reversible_default_to_retirement_ready_requires = ["rollback_window_complete", "embedded_backend_frozen", "retirement_decision_record"]',
                        "",
                        "[forbidden]",
                        "repo_local_execution_wrapper = true",
                        "config_script_home = true",
                        "adopter_named_external_product_root = true",
                        "default_flip_without_rollback_window = true",
                    ]
                ),
                encoding="utf-8",
            )
    rollback_table = ""
    if rollback is not None:
        evidence_manifest = str(
            rollback.get("evidence_manifest") or "docs/evidence/rollback-window.toml"
        )
        manifest_kind = str(rollback.get("manifest") or "complete")
        completed_items = rollback.get("completed_scenarios", ())
        required_items = rollback.get("required_scenarios", ())
        if manifest_kind == "placeholder":
            (root / evidence_manifest).parent.mkdir(parents=True, exist_ok=True)
            (root / evidence_manifest).write_text(
                "# rollback window\n",
                encoding="utf-8",
            )
        else:
            scenario_lines = []
            target_head = str(rollback.get("target_head") or "")
            product_head = str(rollback.get("product_head") or "")
            for item in completed_items:
                evidence_path = f"docs/evidence/rollback-window/{item}.json"
                (root / evidence_path).parent.mkdir(parents=True, exist_ok=True)
                (root / evidence_path).write_text("{}\n", encoding="utf-8")
                scenario_lines.extend(
                    [
                        f"[scenarios.{item}]",
                        f'target_head = "{target_head}"',
                        f'product_head = "{product_head}"',
                        f'evidence = "{evidence_path}"',
                        f'command = "ethos {item}"',
                        f'digest = "sha256:{item}"',
                        "",
                    ]
                )
            (root / evidence_manifest).parent.mkdir(parents=True, exist_ok=True)
            (root / evidence_manifest).write_text(
                "\n".join(
                    [
                        "schema_version = 1",
                        f'target_head = "{target_head}"',
                        f'product_head = "{product_head}"',
                        "",
                        *scenario_lines,
                    ]
                ),
                encoding="utf-8",
            )
        completed = "\n".join(f'  "{item}",' for item in completed_items)
        required = "\n".join(f'  "{item}",' for item in required_items)
        rollback_table = (
            "\n[rollback_window]\n"
            f'state = "{rollback.get("state", "")}"\n'
            f'evidence_manifest = "{evidence_manifest}"\n'
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
retirement_policy = "docs/governance/external-ethos-adoption.md"

[external_backend]
state = "{external_state}"
minimum_version = "external>=embedded"
shadow_required = true
{control_line}{rollback_table}
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
