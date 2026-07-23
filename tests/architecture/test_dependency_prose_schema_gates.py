from __future__ import annotations

import json
import os
import stat
import subprocess
import tomllib
from pathlib import Path

from tests.support.architecture import run_json
from tests.support.architecture import tool_block

# fmt: off

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


def test_python_vulnerability_audit_scans_frozen_uv_lock() -> None:
    config = tomllib.loads((ROOT / ".config/checks/security/audit.toml").read_text())
    assert config["uv_audit"]["state"] == "active_owner_gate"
    assert config["uv_audit"]["input"] == "uv.lock"
    runner = (ROOT / "tools/ci/scripts/run-python-vulnerability-audit.sh").read_text(
        encoding="utf-8"
    )
    assert "uv audit" in runner
    assert "--frozen" in runner
    assert "--preview-features audit-command" in runner
    assert "PYTHONWARNINGS" not in runner

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
    assert payload["tool"] == "uv audit"
    assert payload["tool_input"] == "uv.lock"
    assert payload["service"] == "OSV"
    assert payload["dependency_count"] > 0
    assert payload["vulnerability_count"] == 0

def test_dependency_hygiene_declares_noncanonical_cel_import_mapping() -> None:
    runner = (ROOT / "tools/ci/scripts/run-dependency-hygiene.sh").read_text(encoding="utf-8")

    assert "--package-module-name-map cel-python=celpy" in runner


def test_dependency_hygiene_declares_parse_only_jinja_dynamic_import() -> None:
    policy = tomllib.loads((ROOT / ".config/checks/deptry/policy.toml").read_text())
    package = next(item for item in policy["package"] if item["id"] == "ethos")
    runner = (ROOT / "tools/ci/scripts/run-dependency-hygiene.sh").read_text(encoding="utf-8")

    assert package["per_rule_ignores"] == ["DEP002=jinja2"]
    assert "parse-only source-budget provider" in package["justification"]
    assert "--per-rule-ignores DEP002=jinja2" in runner


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
        "#!/usr/bin/env bash\nset -euo pipefail\n",
        encoding="utf-8",
    )
    install_taplo.chmod(0o755)
    bin_dir = repo / "bin"
    bin_dir.mkdir()
    taplo = bin_dir / "taplo"
    taplo.write_text(
        "#!/usr/bin/env bash\n"
        '[[ "${RUST_LOG:-}" == "warn" ]] || echo " INFO taplo: success noise" >&2\n',
        encoding="utf-8",
    )
    taplo.chmod(0o755)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    completed = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-config-lint.sh", "payload.toml"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
            "PATH": bin_dir.as_posix() + os.pathsep + "/usr/bin:/bin",
            "PYTHON": Path(os.sys.executable).as_posix(),
        },
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == ""


def test_config_lint_json_uses_stdlib_when_jq_is_unavailable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".config/checks/json").mkdir(parents=True)
    (repo / "tools/ci/scripts").mkdir(parents=True)
    (repo / ".config/checks/json/format.toml").write_text(
        (ROOT / ".config/checks/json/format.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo / "payload.json").write_text('{\n  "ok": true\n}\n', encoding="utf-8")
    runner = repo / "tools/ci/scripts/run-config-lint.sh"
    runner.write_text(
        (ROOT / "tools/ci/scripts/run-config-lint.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runner.chmod(0o755)
    bin_dir = repo / "bin"
    bin_dir.mkdir()
    git = bin_dir / "git"
    git.write_text("#!/usr/bin/env bash\nexec /usr/bin/git \"$@\"\n", encoding="utf-8")
    git.chmod(0o755)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    completed = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-config-lint.sh", "payload.json"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
            "PATH": bin_dir.as_posix() + os.pathsep + "/usr/bin:/bin",
            "PYTHON": Path(os.sys.executable).as_posix(),
        },
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_scope_binding_requirement_has_one_accepted_authority() -> None:
    spec = (ROOT / "openspec/specs/repository-governance/spec.md").read_text(encoding="utf-8")

    assert "### Requirement: Authoritative Adopter Material Change Scope Binding" in spec
    assert spec.count("Adopter Material Change Scope Binding") == 1
    assert "same selected-Change companion model" in spec
    assert "no historical profile-write exception remains" in spec


# fmt: on
