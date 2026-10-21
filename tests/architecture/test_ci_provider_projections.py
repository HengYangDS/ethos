"""Hosted projections retain native policy and evidence transport boundaries."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

import tools.ci.ci_projection as owner
import tools.ci.toolchain.native as native
from ethos.adapters.process import run_command
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import observe_projections
from tools.ci.ci_projection import check_templates
from tools.ci.ci_projection import compile_providers
from tools.ci.ci_projection import emulator_declaration
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
    assert arguments[:5] == ["uv", "run", "--frozen", "--offline", "--no-sync"]
    invocation = arguments[5 : arguments.index("--target-ref")]
    assert invocation == ["python", "-B", "-I", "-m", "ethos.cli", "hook", "commit-range"]
    probe = run_command(
        ROOT, (sys.executable, *invocation[1:], "--help"), timeout=10, env={"PATH": ""}
    )
    assert probe.returncode == 0
    assert arguments[-3:] == ["--root", ".", "--json"]
    options = arguments[arguments.index("--target-ref") : -3]
    assert options[::2] == ["--target-ref", "--proposed-head", "--remote-head", "--remote"]
    return tuple(options[1::2])


def test_dual_forge_projections_share_native_compilation(github, gitlab) -> None:
    assert "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR" not in gitlab["variables"]
    assert not set(gitlab["variables"]) & {"UV_OFFLINE", "NPM_CONFIG_OFFLINE"}
    assert {item["provider"] for item in projection_entries()} == {"github", "gitlab"}
    assert check_templates(json_output=False) == owner.check_workflow() == 0
    jobs = {name: github["jobs"][name] for name in ("quality", "verify", "package")}
    assert jobs["quality"]["runs-on"] == "ubuntu-24.04-arm"
    platforms = github["jobs"]["host-conformance"]["strategy"]["matrix"]["os"]
    assert set(platforms) == {"ubuntu-latest", "windows-latest", "macos-latest"}
    assert {
        github["jobs"][name]["steps"][0]["with"].get("ref")
        for name in ("quality", "host-conformance", "supply-image", "external-links")
    } == {"${{ github.event.pull_request.head.sha || github.sha }}"}
    steps = [step for job in jobs.values() for step in job["steps"]]
    assert all("self-hosted" not in str(job.get("runs-on", "")) for job in github["jobs"].values())
    assert not any(
        {"GIT_CONFIG_COUNT", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"}.intersection(step.get("env", {}))
        for step in steps
    )
    commands = [step.get("run", "") for step in steps]
    assert commands.count("uv run --frozen python -B -m tools.ci.toolchain.commit_trust") == 1
    assert (
        commands.count("uv run --frozen --offline --no-sync python -m nox -s hosted_verification")
        == 1
    )
    assert github["jobs"]["external-links"]["continue-on-error"] is True
    assert "External links" not in [step.get("name") for step in jobs["quality"]["steps"]]
    supply = [step.get("run", "") for step in github["jobs"]["supply-image"]["steps"]]
    assert any("--target smoke --build-context workspace=." in command for command in supply)
    # A build check reads every stage, so the smoke stage's named context must resolve too.
    check = next(command for command in supply if " --check " in command)
    assert "--build-context workspace=." in check
    assert "UV_OFFLINE=true" not in str(github["jobs"]["supply-image"])
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
    allure = "build/evidence/quality/tests/allure/"
    assert allure in upload["with"]["path"]
    assert upload["if"] == github["jobs"]["external-links"]["steps"][-1]["if"] == "always()"
    artifacts = gitlab["ethos:verify"]["artifacts"]
    assert artifacts["when"] == gitlab["ethos:external-links"]["artifacts"]["when"] == "always"
    assert "build/evidence/quality/tests/pytest/junit*.xml" in artifacts["paths"]
    # GitHub retains raw Allure results; GitLab's instance artifact limit cannot hold them.
    assert allure not in artifacts["paths"]
    assert artifacts["reports"]["junit"] == "build/evidence/quality/tests/pytest/junit*.xml"
    assert artifacts["reports"]["coverage_report"] == {
        "coverage_format": "cobertura",
        "path": "build/evidence/quality/tests/coverage/coverage.xml",
    }


def test_linux_supply_image_bakes_native_tools_and_smokes_offline(tmp_path, monkeypatch) -> None:
    """The immutable image, not a cold GitLab job, supplies every native gate tool."""
    dockerfile = (ROOT / ".config/ci/supply/Dockerfile").read_text(encoding="utf-8")
    context_rules = set(
        (ROOT / ".config/ci/supply/Dockerfile.dockerignore")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    manifest = re.search(r"sha256sum(?P<inputs>.*?)> input\.sha256", dockerfile, re.DOTALL)
    assert manifest is not None
    copy_sources = {
        source
        for line in dockerfile.replace("\\\n", " ").splitlines()
        if line.startswith("COPY ") and "--from=" not in line
        for source in shlex.split(line)[1:-1]
    }
    manifest_inputs = set(manifest.group("inputs").replace("\\\n", " ").split())
    # Build-only implementation is copied for provisioning, then removed and revalidated at use.
    assert manifest_inputs <= copy_sources
    assert "src/ethos" in copy_sources
    assert "rm -rf .venv node_modules src/ethos" in dockerfile
    final_stage = dockerfile.split("FROM base AS supply\n", 1)[1].split("FROM supply AS smoke", 1)[
        0
    ]
    assert "COPY --from=prepare --chown=65534:65534 /opt/ethos-supply" in final_stage
    assert "USER 65534:65534" in final_stage
    assert "src/ethos" not in final_stage
    # Dependency supply does not build the project wheel or consume its prose/version.
    assert {"README.md", "VERSION"}.isdisjoint(manifest_inputs)
    for path in copy_sources:
        assert (ROOT / path).exists()
        allow = f"!{path}/**" if (ROOT / path).is_dir() else f"!{path}"
        assert allow in context_rules
        for parent in Path(path).parents:
            if parent != Path():
                assert f"!{parent.as_posix()}/" in context_rules
    assert "MISE_DATA_DIR=/opt/ethos-supply/mise-data" in dockerfile
    assert {
        "tests/fixtures/quality-sample/pyproject.toml",
        "tests/fixtures/quality-sample/uv.lock",
    } <= copy_sources
    # The fixture's own uv settings, including its prerelease policy, bind its lock.
    assert "uv --directory /tmp/ethos-quality-sample sync --locked --group dev" in dockerfile
    native_command = "tools/ci/toolchain/native.py --root . --mise gitleaks scc syft vale"
    assert f"PYTHONPATH=src .venv/bin/python {native_command}" in dockerfile
    for relative in copy_sources:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / relative).is_dir():
            shutil.copytree(ROOT / relative, target)
        else:
            target.write_bytes((ROOT / relative).read_bytes())
    monkeypatch.setenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", str(tmp_path / "ambient-cache"))
    environment = {
        "PYTHONPATH": str(tmp_path / "src"),
        "ETHOS_CI_TOOL_CACHE_DIR": str(tmp_path / "tool-cache"),
    }
    imported = run_command(
        tmp_path,
        (sys.executable, "-B", "tools/ci/toolchain/native.py", "--help"),
        env=environment,
        inherit_environment=False,
        timeout=10,
    )
    assert imported.returncode == 0, imported.stderr
    selected = run_command(
        tmp_path,
        (
            sys.executable,
            "-B",
            "-c",
            (
                "from pathlib import Path\n"
                "from ethos.adapters.toolchain.mise import native_tool_cache\n"
                "print(native_tool_cache(Path.cwd()))\n"
            ),
        ),
        env=environment,
        inherit_environment=False,
        timeout=10,
    )
    assert selected.returncode == 0, selected.stderr
    assert selected.stdout.strip() == str(tmp_path / "tool-cache")
    smoke = dockerfile.split("FROM supply AS smoke\n", 1)[1].replace("\\\n", " ")
    assert "RUN --network=none" in smoke
    assert "python -B -m tools.ci.toolchain.native --root . --mise vale gitleaks scc syft" in smoke
    [selector] = re.findall(r"'(tests/[^']+::[^']+)'", smoke)
    collected = run_command(
        ROOT,
        (
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            selector,
        ),
        timeout=60,
    )
    assert collected.returncode == 0, collected.stdout + collected.stderr


@pytest.mark.parametrize("provider", ["github", "gitlab"])
def test_provider_commands_use_shared_owners_without_activating_mutation(provider, gitlab) -> None:
    entry = next(item for item in projection_entries() if item["provider"] == provider)
    text = (ROOT / entry["projection"]).read_text()
    assert "uv run --frozen --offline --no-sync python -m nox -s hosted_verification" in text
    assert "tools/ci/scripts/configure-git-checkout.sh" not in text
    assert "ethos hook install" not in text
    assert "\n    - openspec validate" not in text
    if provider == "gitlab":
        jobs = {name.removeprefix("ethos:") for name in gitlab if name.startswith("ethos:")}
        assert jobs == {"commit-policy", "external-links", "host-conformance", "npm", "verify"}
        assert gitlab["ethos:verify"]["script"][-1] == (
            "uv run --frozen --offline --no-sync python -m nox -s hosted_verification"
        )
        assert "external-links" not in " ".join(gitlab["ethos:verify"]["script"])
        assert gitlab["ethos:external-links"]["allow_failure"] is True
        bootstrap = gitlab["ethos:verify"]["before_script"]
        assert bootstrap[0] == 'sha256sum --check --quiet "$ETHOS_CI_SUPPLY_MANIFEST"'
        assert all(
            gitlab[name]["before_script"] == bootstrap
            for name in gitlab
            if name.startswith("ethos:")
        )
        assert gitlab["ethos:verify"]["image"] == gitlab["ethos:npm"]["image"]
        assert "build/artifacts/python/" in gitlab["ethos:verify"]["artifacts"]["paths"]
        assert "stuck_or_timeout_failure" not in gitlab["default"]["retry"]["when"]


def test_hosted_pipeline_does_not_launch_nonexecuted_provider_observation(github, gitlab) -> None:
    """Hosted jobs must not spend a Nox startup on an unclaimed dry-run envelope."""
    github_commands = [step.get("run", "") for step in github["jobs"]["quality"]["steps"]]
    gitlab_commands = gitlab["ethos:verify"]["script"]
    assert all("-s hosted_observation" not in command for command in github_commands)
    assert all("-s hosted_observation" not in command for command in gitlab_commands)
    assert "ETHOS_HOSTED_OBSERVATION_EXECUTE" not in github["jobs"]["quality"].get("env", {})
    assert "ETHOS_HOSTED_OBSERVATION_EXECUTE" not in gitlab["ethos:verify"].get("variables", {})


@pytest.mark.parametrize(
    ("job", "name"), [("verify", "repository proof"), ("package", "package artifacts")]
)
def test_required_github_checks_project_only_successful_execution(github, job, name) -> None:
    projected = github["jobs"][job]
    assert projected["name"] == name
    assert projected["needs"] == "quality"
    assert projected["if"] == "${{ always() && !inputs.supply_image && !inputs.release_tag }}"
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
        step["name"]: step for step in github["jobs"]["quality"]["steps"] if "name" in step
    }
    for event, name, fields in (
        ("push", "Admit pushed commit range", ("ref", "sha", "event.before")),
        ("pull_request", "Admit pull request commit range", ("base.ref", "head.sha", "base.sha")),
    ):
        prefix = "github" if event == "push" else "github.event.pull_request"
        coordinates = [f"${{{{ {prefix}.{field} }}}}" for field in fields]
        if event == "pull_request":
            coordinates[0] = "refs/heads/" + coordinates[0]
        assert github_steps[name]["if"] == f"github.event_name == '{event}'"
        assert _range_coordinates(github_steps[name]["run"]) == (*coordinates, "origin")
    gitlab_job = gitlab["ethos:commit-policy"]
    assert gitlab_job["variables"] == {"GIT_STRATEGY": "clone"}
    rules = gitlab_job["rules"]
    mr = "CI_MERGE_REQUEST"
    fields = (
        ("CI_COMMIT_BRANCH", "CI_COMMIT_SHA", "CI_COMMIT_BEFORE_SHA"),
        (f"{mr}_TARGET_BRANCH_NAME", f"{mr}_SOURCE_BRANCH_SHA", f"{mr}_TARGET_BRANCH_SHA"),
        (f"{mr}_TARGET_BRANCH_NAME", "CI_COMMIT_SHA", f"{mr}_DIFF_BASE_SHA"),
    )
    expected = [
        (f"refs/heads/${{{ref}}}", f"${{{head}}}", f"${{{base}}}") for ref, head, base in fields
    ]
    assert [tuple(rule.get("variables", {}).values()) for rule in rules] == [*expected, ()]
    assert rules[-1] == {"when": "never"}
    assert _range_coordinates(gitlab_job["script"][0]) == (
        "${ETHOS_COMMIT_TARGET_REF}",
        "${ETHOS_COMMIT_PROPOSED_HEAD}",
        "${ETHOS_COMMIT_REMOTE_HEAD}",
        "origin",
    )
    provider_text = yaml.safe_dump({"github": github, "gitlab": gitlab})
    assert all(token not in provider_text for token in ("rev-list", "subject_pattern"))


def test_hosted_runtime_versions_are_checked_projections_of_native_owners(github, gitlab):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    mise = tomllib.loads((ROOT / ".config/mise/config.toml").read_text())
    declaration = tomllib.loads((ROOT / owner.CONFIG_RELATIVE_PATH).read_text())
    assert declaration["compiler"]["inputs"]["node"] == ".config/mise/config.toml"
    uv_version = next(
        item.removeprefix("uv>=")
        for item in project["dependency-groups"]["dev"]
        if item.startswith("uv>=")
    )
    steps = [step for job in github["jobs"].values() for step in job["steps"]]
    assert {
        step["with"]["version"]
        for step in steps
        if step.get("uses", "").startswith("astral-sh/setup-uv@")
    } == {uv_version}
    assert mise["tools"]["node"] in github["jobs"]["host-conformance"]["name"]
    npm_job = gitlab["ethos:npm"]
    assert npm_job["variables"]["NODE_VERSION"] == mise["tools"]["node"]
    assert npm_job["script"][-1] == (
        "uv run --frozen --offline --no-sync python -m nox -s javascript_tests"
    )
    images = {
        job["image"]
        for job in gitlab.values()
        if isinstance(job, dict) and isinstance(job.get("image"), str)
    }
    providers = {entry["provider"]: entry for entry in projection_entries()}
    assert "@sha256:" in providers["github"]["emulator_image"]
    assert "emulator_image" not in providers["gitlab"]
    assert all(int(entry["emulator_timeout_seconds"]) > 0 for entry in providers.values())
    declared = providers["gitlab"]
    assert declared["emulator_job"] == "ethos:verify"
    assert images == {emulator_declaration(declared)["emulator_image"]}


def test_host_conformance_receives_native_python_supply_before_activation(github, gitlab) -> None:
    job = github["jobs"]["host-conformance"]
    github_steps = job["steps"]
    setup_uv = next(
        step for step in github_steps if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    )
    commands = [str(step.get("run", "")) for step in github_steps]

    assert not any("actions/setup-python@" in str(step.get("uses", "")) for step in github_steps)
    assert job["env"]["UV_PYTHON_INSTALL_DIR"] == "${{ github.workspace }}/build/runtime/python"
    assert setup_uv["with"]["python-version"] == "${{ matrix.python }}"
    preparation = [
        "uv python install --no-bin ${{ matrix.python }}",
        "uv sync --locked --no-install-project --group dev",
        "uv run --no-sync python -B tools/ci/toolchain/native.py --root . --mise vale",
        "uv sync --locked --group dev",
        "uv run --frozen python -m nox -s host_conformance",
        "uv run --frozen python -m nox -s javascript_tests",
    ]
    assert [command for command in commands if command in preparation] == preparation
    npm_sync = next(command for command in commands if "ci --ignore-scripts" in command)
    assert (
        commands.index(preparation[1]) < commands.index(preparation[2]) < commands.index(npm_sync)
    )
    assert commands.index(npm_sync) < commands.index(preparation[3])

    gitlab_job = gitlab["ethos:host-conformance"]
    assert gitlab_job["stage"] == "verify"
    assert gitlab_job["script"] == [
        "uv run --frozen --offline --no-sync python -m nox -s host_conformance"
    ]


def test_hosted_cache_roots_do_not_move_with_child_working_directories(github, gitlab) -> None:
    workspace_cache = "${{ github.workspace }}/build/runtime/tool-cache/"
    assert github["env"]["UV_CACHE_DIR"] == workspace_cache + "uv"
    assert github["env"]["ETHOS_CI_TOOL_CACHE_DIR"] == workspace_cache + "ci-tools"
    assert gitlab["variables"]["UV_CACHE_DIR"].startswith("/")
    assert gitlab["variables"]["ETHOS_CI_TOOL_CACHE_DIR"].startswith("/")


def test_full_proof_owns_github_workflow_syntax_before_hosted_execution() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert declaration["proof_sets"]["full"].count("github-workflow-syntax") == 1
    gate = gates["github-workflow-syntax"]
    assert gate["command"] == ["{python}", "-m", "tools.ci.ci_projection"]
    assert gate["depends_on"] == ["config-quality"]
    assert gate["writes_files"] is False
    assert gate["network_policy"] == "offline"


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


def _offline_generation(root, command, **kwargs):
    """Allow native local compilation but reject a network-bearing generation call."""
    if "install-script" in command:
        message = "unexpected_network_generation"
        raise ValueError(message)
    return run_command(root, command, **kwargs)


@pytest.mark.parametrize(
    ("fault", "target", "old", "new"),
    [
        ("none", "output", "", ""),
        ("drift", "output", "name: ETHOS CI", "name: Unapproved"),
        ("byte-drift", "output", None, "\n"),
        ("self-certified", "output", "name: ETHOS CI", "name: Unapproved"),
        ("malformed", "model", None, "invalid: ["),
        ("missing", "model", None, None),
        ("unformatted", "model", 'name: "ETHOS CI"', 'name:    "ETHOS CI"'),
        ("missing-output", "output", None, None),
        ("bootstrap-version", "mise", "2026.10.14", "0.0.0"),
        ("bootstrap-lock", "declaration", "linux-arm64 =", "linux-unsupported ="),
    ],
)
def test_cue_owner_requires_native_semantics_without_parallel_templates(
    tmp_path, monkeypatch, capsys, fault, target, old, new, ci_materials
):
    """Offline native consumers reject forged projections and unbound supply."""
    config, materials = ci_materials
    files = dict(materials)
    monkeypatch.setattr(native, "run_command", _offline_generation)
    model, output = config["compiler"]["source"], config["projection"][0]["projection"]
    relative = {
        "model": model,
        "output": output,
        "declaration": owner.CONFIG_RELATIVE_PATH,
        "mise": config["compiler"]["supply"]["config"],
    }[target]
    if new is None:
        files.pop(relative)
    elif fault == "byte-drift":
        files[relative] += new
    else:
        files[relative] = files[relative].replace(old, new) if old is not None else new
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
    if fault in {"drift", "self-certified", "byte-drift"} or fault.startswith("bootstrap"):
        provider = "github" if fault == "byte-drift" else "compiler"
        reason = (
            "mise_executable_record_invalid"
            if fault.startswith("bootstrap")
            else f"projection byte drift: {output}"
            if fault == "byte-drift"
            else "cue_projection_drift"
        )
        assert report["failures"][0] == {"provider": provider, "reason": reason}
        assert len(report["failures"]) == (3 if fault == "bootstrap-missing" else 1)


@pytest.mark.parametrize(
    ("fault", "error"),
    [
        ("none", None),
        ("missing-lock", ".config/mise/mise.lock"),
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
        files.pop(compiler["supply"]["lock"])
    elif fault in {"version-drift", "native-version"}:
        files[compiler["supply"]["config"]] = files[compiler["supply"]["config"]].replace(
            'cue = "0.17.1"', 'cue = "0.17.0"'
        )
    elif fault == "project-hook":
        files[compiler["supply"]["config"]] += '\n[hooks]\nenter = "touch FORBIDDEN"\n'
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
