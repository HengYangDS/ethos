from __future__ import annotations

import json
import stat
import subprocess
import tomllib
from pathlib import Path

from tests.support.architecture import run_json
from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]


def test_dependency_hygiene_runs_per_distribution_and_writes_summary() -> None:
    config = tomllib.loads((ROOT / ".config/checks/deptry/policy.toml").read_text())
    assert {item["id"] for item in config["package"]} == {"ethos", "ethos-core"}
    assert config["runner"] == "tools/ci/scripts/run-dependency-hygiene.sh"

    payload = run_json(ROOT, ["tools/ci/scripts/run-dependency-hygiene.sh"])
    persisted = json.loads(
        (ROOT / "build/evidence/quality/dependency/summary.json").read_text(encoding="utf-8")
    )

    assert payload == persisted
    assert payload["kind"] == "ethos_dependency_hygiene"
    assert payload["ok"] is True
    assert payload["evidence_class"] == "local_owner_gate"
    assert "vulnerability scan" in payload["not_claimed"]


def test_prose_and_schema_gates_are_report_first_owner_surfaces() -> None:
    prose = tomllib.loads((ROOT / ".config/checks/prose/codespell.toml").read_text())
    schema = tomllib.loads((ROOT / ".config/checks/schema/jsonschema.toml").read_text())

    assert prose["runner"] == "tools/ci/scripts/run-prose-check.sh"
    assert "evidence" in prose["skip"]
    assert schema["runner"] == "tools/ci/scripts/run-json-schema-check.sh"
    assert schema["check"][0]["mode"] == "metaschema"

    schema_payload = run_json(ROOT, ["tools/ci/scripts/run-json-schema-check.sh"])
    assert schema_payload["status"] == "ok"
    subprocess.run(["tools/ci/scripts/run-prose-check.sh"], cwd=ROOT, check=True)


def test_active_dependency_prose_schema_gates_have_all_owner_surfaces() -> None:
    active = {
        "dependency_hygiene": "tools/ci/scripts/run-dependency-hygiene.sh",
        "prose": "tools/ci/scripts/run-prose-check.sh",
        "json_schema": "tools/ci/scripts/run-json-schema-check.sh",
        "python_vuln": "tools/ci/scripts/run-python-vulnerability-audit.sh",
    }
    combined_ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8") + (
        ROOT / ".gitlab-ci.yml"
    ).read_text(encoding="utf-8")
    template_config = (ROOT / ".config/checks/ci/templates.toml").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/reference/runbook-registry.md").read_text(encoding="utf-8")

    for concern, gate in active.items():
        block = tool_block(ROOT, concern)
        script = ROOT / gate
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR
        assert gate in combined_ci
        assert gate in template_config
        assert gate in runbook


def test_python_vulnerability_audit_scans_uv_exported_resolved_input() -> None:
    config = tomllib.loads((ROOT / ".config/checks/security/audit.toml").read_text())
    assert config["pip_audit"]["state"] == "active_owner_gate"
    assert "uv export" in config["pip_audit"]["input"]
    assert "pip-audit reads uv.lock directly" in config["pip_audit"]["forbidden_claims"]

    payload = run_json(ROOT, ["tools/ci/scripts/run-python-vulnerability-audit.sh"])
    persisted = json.loads(
        (ROOT / "build/evidence/quality/security/python-vulnerability-audit.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload == persisted
    assert payload["kind"] == "ethos_python_vulnerability_audit"
    assert payload["ok"] is True
    assert payload["evidence_class"] == "local_owner_gate"
    assert payload["tool_input"] == "uv-exported-resolved-requirements"
    assert payload["dependency_count"] > 0
    assert payload["vulnerability_count"] == 0
    assert "OSV scan passed" in payload["not_claimed"]
    assert "pip-audit reads uv.lock directly" in payload["not_claimed"]


def test_non_pip_vulnerability_scanners_remain_planned() -> None:
    config = tomllib.loads((ROOT / ".config/checks/security/audit.toml").read_text())
    assert config["osv_scanner"]["state"] == "planned_profile_gate"

    for concern in ["osv_vuln", "image_package_scan", "signing"]:
        block = tool_block(ROOT, concern)
        assert "planned = true" in block


def test_config_lint_targeted_toml_invocation_handles_empty_json_set(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".config/checks/taplo").mkdir(parents=True)
    (repo / "tools/ci/scripts").mkdir(parents=True)
    (repo / ".config/checks/taplo/taplo.toml").write_text(
        (ROOT / ".config/checks/taplo/taplo.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo / "payload.toml").write_text("ok = true\n", encoding="utf-8")
    runner = repo / "tools/ci/scripts/run-config-lint.sh"
    runner.write_text(
        (ROOT / "tools/ci/scripts/run-config-lint.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runner.chmod(0o755)
    install_taplo = repo / "tools/ci/scripts/install-taplo.sh"
    install_taplo.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ntaplo --version\n", encoding="utf-8"
    )
    install_taplo.chmod(0o755)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    completed = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-config-lint.sh", "payload.toml"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
