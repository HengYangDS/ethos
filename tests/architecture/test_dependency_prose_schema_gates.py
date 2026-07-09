from __future__ import annotations

import json
import stat
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_json(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def _tool_block(concern: str) -> str:
    text = (ROOT / "system" / "tools.toml").read_text(encoding="utf-8")
    marker = f'concern = "{concern}"'
    assert marker in text
    before, after = text.split(marker, 1)
    block_start = before.rfind("[[tool]]")
    next_block = after.find("[[tool]]")
    body = marker + (after if next_block == -1 else after[:next_block])
    return before[block_start:] + body


def test_dependency_hygiene_runs_per_distribution_and_writes_summary() -> None:
    config = tomllib.loads((ROOT / ".config/checks/deptry/policy.toml").read_text())
    assert {item["id"] for item in config["package"]} == {"ethos", "ethos-core"}
    assert config["runner"] == "tools/ci/scripts/run-dependency-hygiene.sh"

    payload = _run_json(["tools/ci/scripts/run-dependency-hygiene.sh"])
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

    schema_payload = _run_json(["tools/ci/scripts/run-json-schema-check.sh"])
    assert schema_payload["status"] == "ok"
    subprocess.run(["tools/ci/scripts/run-prose-check.sh"], cwd=ROOT, check=True)


def test_active_dependency_prose_schema_gates_have_all_owner_surfaces() -> None:
    active = {
        "dependency_hygiene": "tools/ci/scripts/run-dependency-hygiene.sh",
        "prose": "tools/ci/scripts/run-prose-check.sh",
        "json_schema": "tools/ci/scripts/run-json-schema-check.sh",
    }
    combined_ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8") + (
        ROOT / ".gitlab-ci.yml"
    ).read_text(encoding="utf-8")
    template_config = (ROOT / ".config/checks/ci/templates.toml").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/reference/runbook-registry.md").read_text(encoding="utf-8")

    for concern, gate in active.items():
        block = _tool_block(concern)
        script = ROOT / gate
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR
        assert gate in combined_ci
        assert gate in template_config
        assert gate in runbook


def test_vulnerability_scanners_remain_planned_until_lock_input_is_supported() -> None:
    config = tomllib.loads((ROOT / ".config/checks/security/audit.toml").read_text())
    assert config["pip_audit"]["state"] == "planned_profile_gate"
    assert "uv.lock" in config["pip_audit"]["reason"]

    for concern in ["python_vuln", "osv_vuln", "image_package_scan", "signing"]:
        block = _tool_block(concern)
        assert "planned = true" in block
