"""Hosted projections retain native policy and evidence transport boundaries."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import tomllib
from pathlib import Path

import pytest
import yaml

import tools.ci.ci_projection as owner
from ethos.adapters.process import run_command
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import observe_projections
from tools.ci.ci_projection import check_templates
from tools.ci.ci_projection import compile_providers
from tools.ci.ci_projection import projection_entries

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ci_materials():
    """Share immutable native inputs; every fault case gets its own mutable copy."""
    config = tomllib.loads((ROOT / owner.CONFIG_RELATIVE_PATH).read_text())
    paths = {path for relation in observe_projections(ROOT) for path in relation.materials}
    paths.update(path for entry in config["projection"] for path in entry["required_owner_scripts"])
    paths.update(entry["projection"] for entry in config["forge_surface"])
    return config, {path: (ROOT / path).read_text() for path in paths}


@pytest.fixture(scope="module")
def github():
    """Read the actual hosted projection once; source parity is checked separately."""
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())


@pytest.fixture(scope="module")
def gitlab():
    """Read the actual GitLab projection consumed by its native runner."""
    return yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())


def _range_coordinates(command: str) -> tuple[str, ...]:
    arguments = shlex.split(command)
    assert arguments[:6] == ["uv", "run", "--frozen", "--offline", "ethos", "hook"]
    assert arguments[6] == "commit-range"
    assert arguments[-3:] == ["--root", ".", "--json"]
    options = arguments[7:-3]
    assert options[::2] == ["--target-ref", "--proposed-head", "--remote-head", "--remote"]
    return tuple(options[1::2])


def test_dual_forge_projections_share_native_compilation(github, gitlab) -> None:
    assert {item["provider"] for item in projection_entries()} == {"github", "gitlab"}
    assert check_templates(json_output=False) == 0
    jobs = {name: github["jobs"][name] for name in ("quality", "verify", "package")}
    steps = [step for job in jobs.values() for step in job["steps"]]
    commands = [step.get("run", "") for step in steps]
    assert commands.count("tools/ci/scripts/bootstrap-python.sh") == 1
    assert commands.count("tools/ci/scripts/run-head-bound-proof.sh") == 1
    assert sum("actions/checkout@" in step.get("uses", "") for step in steps) == 1
    assert not any(
        " -m nox -s build" in command or " -m nox -s supply_chain" in command
        for command in commands
    )
    assert not {
        "ETHOS_TEST_WORKERS",
        "ETHOS_TEST_TIMEOUT_SECONDS",
        "ETHOS_TEST_TIMEOUT_METHOD",
    }.intersection(github["jobs"]["quality"].get("env", {}))
    upload = next(step for step in steps if step.get("name") == "Upload proof receipt")
    junit = "build/evidence/quality/tests/pytest/junit*.xml"
    assert junit in upload["with"]["path"]
    assert upload.get("if") == "always()"
    artifacts = gitlab["ethos:verify"]["artifacts"]
    assert artifacts["when"] == "always"
    assert "build/evidence/quality/tests/pytest/junit*.xml" in artifacts["paths"]
    assert artifacts["reports"]["junit"] == "build/evidence/quality/tests/pytest/junit*.xml"
    assert artifacts["reports"]["coverage_report"] == {
        "coverage_format": "cobertura",
        "path": "build/evidence/quality/tests/coverage/coverage.xml",
    }


@pytest.mark.parametrize("provider", ["github", "gitlab"])
def test_provider_commands_use_shared_owners_without_activating_mutation(provider, gitlab) -> None:
    entry = next(item for item in projection_entries() if item["provider"] == provider)
    text = (ROOT / entry["projection"]).read_text()
    assert "tools/ci/scripts/run-head-bound-proof.sh" in text
    assert "tools/ci/scripts/configure-git-checkout.sh" not in text
    assert "ethos hook install" not in text
    assert "\n    - openspec validate" not in text
    if provider == "gitlab":
        assert {name for name in gitlab if name.startswith("ethos:")} == {
            "ethos:commit-policy",
            "ethos:verify",
            "ethos:host-conformance",
            "ethos:npm",
        }
        assert gitlab["ethos:verify"]["script"][-1] == "tools/ci/scripts/run-head-bound-proof.sh"
        assert gitlab["ethos:verify"]["before_script"] == []
        assert "bootstrap-python.sh" in gitlab["ethos:verify"]["image"]["entrypoint"][2]
        assert "build/artifacts/python/" in gitlab["ethos:verify"]["artifacts"]["paths"]
        assert "stuck_or_timeout_failure" not in gitlab["default"]["retry"]["when"]


@pytest.mark.parametrize(
    ("job", "name"), [("verify", "repository proof"), ("package", "package artifacts")]
)
def test_required_github_checks_project_only_successful_execution(github, job, name) -> None:
    projected = github["jobs"][job]
    assert projected["name"] == name
    assert projected["needs"] == "quality"
    assert projected["if"] == "${{ always() }}"
    (step,) = projected["steps"]
    assert step["env"] == {"QUALITY_RESULT": "${{ needs.quality.result }}"}
    for result in ("success", "failure", "cancelled", "skipped", ""):
        observed = run_command(
            ROOT,
            ("bash", "-c", step["run"]),
            env=os.environ | {"QUALITY_RESULT": result},
            timeout=5,
        )
        assert (observed.returncode == 0) == (result == "success")


def test_integration_events_transport_exact_commit_range_coordinates(github, gitlab) -> None:
    github_steps = {
        step["name"]: step
        for step in github["jobs"]["quality"]["steps"]
        if isinstance(step, dict) and "name" in step
    }

    assert [
        (github_steps[name]["if"], _range_coordinates(github_steps[name]["run"]))
        for name in ("Admit pushed commit range", "Admit pull request commit range")
    ] == [
        (
            "github.event_name == 'push'",
            ("${{ github.ref }}", "${{ github.sha }}", "${{ github.event.before }}", "origin"),
        ),
        (
            "github.event_name == 'pull_request'",
            (
                "refs/heads/${{ github.event.pull_request.base.ref }}",
                "${{ github.event.pull_request.head.sha }}",
                "${{ github.event.pull_request.base.sha }}",
                "origin",
            ),
        ),
    ]

    gitlab_job = gitlab["ethos:commit-policy"]
    assert gitlab_job["variables"] == {"GIT_STRATEGY": "clone"}
    rules = gitlab_job["rules"]
    assert [tuple(rule.get("variables", {}).values()) for rule in rules] == [
        ("refs/heads/${CI_COMMIT_BRANCH}", "${CI_COMMIT_SHA}", "${CI_COMMIT_BEFORE_SHA}"),
        (
            "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}",
            "${CI_MERGE_REQUEST_SOURCE_BRANCH_SHA}",
            "${CI_MERGE_REQUEST_TARGET_BRANCH_SHA}",
        ),
        (
            "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}",
            "${CI_COMMIT_SHA}",
            "${CI_MERGE_REQUEST_DIFF_BASE_SHA}",
        ),
        (),
    ]
    assert rules[-1] == {"when": "never"}
    assert _range_coordinates(gitlab_job["script"][0]) == (
        "${ETHOS_COMMIT_TARGET_REF}",
        "${ETHOS_COMMIT_PROPOSED_HEAD}",
        "${ETHOS_COMMIT_REMOTE_HEAD}",
        "origin",
    )

    provider_text = yaml.safe_dump({"github": github, "gitlab": gitlab})
    assert "rev-list" not in provider_text
    assert "subject_pattern" not in provider_text


def test_hosted_runtime_versions_are_checked_projections_of_native_owners(github, gitlab):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    node = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text())
    uv_version = next(
        item.removeprefix("uv>=")
        for item in project["dependency-groups"]["dev"]
        if item.startswith("uv>=")
    )
    steps = [step for job in github["jobs"].values() for step in job["steps"]]
    for tool, field, expected in (
        ("astral-sh/setup-uv@", "version", uv_version),
        ("actions/setup-node@", "node-version", node["default_version"]),
    ):
        assert {step["with"][field] for step in steps if step.get("uses", "").startswith(tool)} == {
            expected
        }
    assert (
        gitlab["ethos:npm"]["parallel"]["matrix"][0]["NODE_VERSION"]
        == node["compatibility_versions"]
    )
    images = {
        job["image"]
        for job in gitlab.values()
        if isinstance(job, dict) and isinstance(job.get("image"), str)
    }
    providers = {entry["provider"]: entry for entry in projection_entries()}
    assert all("@sha256:" in entry["emulator_image"] for entry in providers.values())
    assert all(int(entry["emulator_timeout_seconds"]) > 0 for entry in providers.values())
    declared = providers["gitlab"]
    assert declared["emulator_job"] == "ethos:verify"
    assert images == {declared["emulator_image"]}
    assert declared["emulator_image"].startswith(f"ghcr.io/astral-sh/uv:{uv_version}-")


def test_host_conformance_receives_native_python_supply_before_activation(github, gitlab) -> None:
    github_job = github["jobs"]["host-conformance"]
    github_steps = github_job["steps"]
    setup_uv = next(
        step for step in github_steps if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    )
    commands = [str(step.get("run", "")) for step in github_steps]

    assert all(
        not str(step.get("uses", "")).startswith("actions/setup-python@") for step in github_steps
    )
    assert github_job["env"]["UV_PYTHON_INSTALL_DIR"] == (
        "${{ github.workspace }}/build/runtime/python"
    )
    assert setup_uv["with"]["python-version"] == "${{ matrix.python }}"
    preparation = [
        "uv python install --no-bin ${{ matrix.python }}",
        "uv sync --locked --group dev",
        "uv run --frozen python -m nox -s host_conformance",
    ]
    assert [command for command in commands if command in preparation] == preparation

    gitlab_job = gitlab["ethos:host-conformance"]
    assert gitlab_job["stage"] == "verify"
    assert gitlab_job["script"] == ["uv run --frozen --offline python -m nox -s host_conformance"]


def test_full_proof_owns_github_workflow_syntax_before_hosted_execution() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert declaration["proof_sets"]["full"].count("github-workflow-syntax") == 1
    gate = gates["github-workflow-syntax"]
    assert gate["command"] == ["tools/ci/scripts/run-actionlint.sh"]
    assert gate["depends_on"] == ["config-quality"]
    assert gate["writes_files"] is True
    assert gate["network_policy"] == "required"


def test_github_action_pins_are_unique_full_commit_ids(github) -> None:
    pins: dict[str, str] = {}
    for step in (step for job in github["jobs"].values() for step in job["steps"]):
        if "uses" in step:
            action, commit = step["uses"].split("@")
            assert re.fullmatch(r"[0-9a-f]{40}", commit)
            assert pins.setdefault(action, commit) == commit
    assert pins


def test_native_projection_cli_is_deterministic_and_read_only(tmp_path):
    """The real CLI emits the exact two committed projections without rewriting them."""
    command = (".venv/bin/python", "tools/ci/ci_templates.py", "check-templates", "--render")
    expected = {
        item["projection"]: (ROOT / item["projection"]).read_text() for item in projection_entries()
    }
    first = run_command(ROOT, command, timeout=30, check=True).stdout
    assert first == run_command(ROOT, command, timeout=30, check=True).stdout
    assert json.loads(first) == expected
    assert all((ROOT / path).read_text() == text for path, text in expected.items())
    with pytest.raises((ValueError, FileNotFoundError)):
        compile_providers(tmp_path)


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "drift",
        "byte-drift",
        "self-certified",
        "malformed",
        "missing",
        "unformatted",
        "bootstrap",
        "missing-output",
    ],
)
def test_cue_owner_requires_native_semantics_without_parallel_templates(
    tmp_path, monkeypatch, capsys, fault, ci_materials
):
    """A native CUE relation needs no YAML template and rejects forged output."""
    config, materials = ci_materials
    files = dict(materials)
    model, output = config["compiler"]["source"], config["projection"][0]["projection"]
    if fault in {"drift", "self-certified"}:
        files[output] = files[output].replace("name: ETHOS CI", "name: Unapproved")
    elif fault == "byte-drift":
        files[output] += "\n"
    elif fault in {"bootstrap", "malformed"}:
        relative, content = {
            "bootstrap": (".config/ci/mise-install.sh", "#!/bin/sh\nexit 0\n"),
            "malformed": (model, "invalid: ["),
        }[fault]
        files[relative] = content
    elif fault in {"missing", "missing-output"}:
        files.pop(model if fault == "missing" else output)
    elif fault == "unformatted":
        files[model] = files[model].replace('name: "ETHOS CI"', 'name:    "ETHOS CI"')
    if fault == "self-certified":
        files[model] = run_command(
            ROOT,
            (str(locked_tool(ROOT, "cue")), "fmt", "-"),
            stdin=files[model]
            + (
                "\ncompiled: observations: compiled.providers\n"
                'compiled: rendered: {github: "forged", gitlab: "forged"}\n'
            ),
            timeout=15,
            check=True,
        ).stdout
    for relative, content in files.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "CONFIG_PATH", tmp_path / owner.CONFIG_RELATIVE_PATH)
    assert (owner.check_templates(json_output=True) == 0) is (fault == "none")
    report = json.loads(capsys.readouterr().out)
    if fault in {"drift", "self-certified", "bootstrap", "byte-drift"}:
        provider = "github" if fault == "byte-drift" else "compiler"
        reason = {
            "bootstrap": "mise_bootstrap_drift",
            "byte-drift": f"projection byte drift: {output}",
        }.get(fault, "cue_projection_drift")
        assert report["failures"] == [{"provider": provider, "reason": reason}]


@pytest.mark.parametrize(
    ("fault", "error"),
    [
        ("none", None),
        ("missing-lock", "mise.lock"),
        ("version-drift", "mise_supply_unavailable"),
        ("project-hook", None),
        ("native-version", "cue_version_mismatch"),
        ("providers", "cue_projection_providers_mismatch"),
        ("compile", "cue_compilation_failed"),
    ],
)
def test_cue_compiler_consumes_exact_locked_supply(tmp_path, fault, error, ci_materials):
    """Missing or mismatched locks cannot be repaired by ambient installed tools."""
    config, materials = ci_materials
    files, compiler = dict(materials), config["compiler"]
    if fault == "missing-lock":
        files.pop("mise.lock")
    elif fault in {"version-drift", "native-version"}:
        files["mise.toml"] = files["mise.toml"].replace('cue = "0.17.1"', 'cue = "0.17.0"')
    elif fault == "project-hook":
        files["mise.toml"] += '\n[hooks]\nenter = "touch FORBIDDEN"\n'
    executable = (
        locked_tool(ROOT, "cue") if fault in {"native-version", "providers", "compile"} else None
    )
    if fault == "providers":
        files[compiler["source"]] += "\ncompiled: providers: unexpected: {}\n"
    elif fault == "compile":
        files[compiler["source"]] = "invalid: ["
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    if error:
        with pytest.raises((ValueError, KeyError), match=error):
            compile_projections(tmp_path, owner.CONFIG_RELATIVE_PATH, files, executable=executable)
    else:
        assert set(compile_projections(tmp_path, owner.CONFIG_RELATIVE_PATH, files)) == {
            "github",
            "gitlab",
        }
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


@pytest.mark.parametrize("fault", ["none", "syntax", "missing-lock", "version-drift"])
def test_workflow_gate_uses_locked_native_tool_without_ambient_fallback(
    tmp_path, monkeypatch, fault
):
    """Run the real gate over a tiny workflow with a hostile ambient actionlint."""
    for path in ("mise.toml", "mise.lock"):
        shutil.copyfile(ROOT / path, tmp_path / path)
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "name: check\non: push\njobs:\n  check:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n"
    )
    if fault == "syntax":
        workflow.write_text("on: push\njobs: [\n")
    elif fault == "missing-lock":
        (tmp_path / "mise.lock").unlink()
    elif fault == "version-drift":
        config = tmp_path / "mise.toml"
        config.write_text(config.read_text().replace('"1.7.12"', '"0.0.0"'))
    bins = tmp_path / "bin"
    bins.mkdir()
    trap = bins / "actionlint"
    trap.write_text("#!/bin/sh\ntouch AMBIENT_EXECUTED\nexit 0\n")
    trap.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bins}{os.pathsep}{os.environ['PATH']}")
    before = workflow.read_bytes()
    assert (owner.check_workflow(tmp_path) == 0) is (fault == "none")
    assert workflow.read_bytes() == before
    assert not (tmp_path / "AMBIENT_EXECUTED").exists()
