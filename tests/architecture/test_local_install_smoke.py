from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import cast

import tools.ci.delivery.pipeline as delivery_pipeline
from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.adapters.repo.runtime.manifest import canonical_architecture
from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)
from ethos.contracts.semantic import Commitment
from ethos.repository.release.identity import BuildIdentity
from tools.ci.delivery.adopter_fixture import line_ending_conformance
from tools.ci.delivery.adopter_fixture import materialize_adopter
from tools.ci.delivery.pipeline import DeliveryPipeline

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _run(executable: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (executable.as_posix(), *args),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _assert_runtime_manifest(report: dict[str, object], repo: Path) -> None:
    manifest_path = Path(str(report["runtime_manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.parent.parent == repo / ".git/ethos/runtime"
    assert manifest_path.parent.name == report["runtime_digest"]
    assert manifest["schema_version"] == 6
    assert manifest["architecture"] == canonical_architecture(platform.machine())
    assert manifest["runtime_digest"] == report["runtime_digest"]


def test_host_conformance_git_overlay_is_platform_portable() -> None:
    count = int(os.environ["GIT_CONFIG_COUNT"])
    entries = [
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    ]

    assert ("core.fsmonitor", "false") in entries
    assert not {"user.name", "user.email"} & {key for key, _value in entries}
    assert os.environ["GIT_AUTHOR_NAME"] == "ETHOS Test"
    assert os.environ["GIT_AUTHOR_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_COMMITTER_NAME"] == "ETHOS Test"
    assert os.environ["GIT_COMMITTER_EMAIL"] == "test@example.invalid"
    assert len([key for key, _value in entries if key == "init.templateDir"]) == 1
    assert all(value for _, value in entries)
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert os.environ["GIT_TERMINAL_PROMPT"] == "0"


def _prove_relocated_runtime(
    *,
    runtime_python: Path,
    repo: Path,
    hooks_path: Path,
    environment: dict[str, str],
) -> None:
    """Prove status, repair, and proof stay executable after package relocation."""
    command = ("-B", "-I", "-m", "ethos.cli")
    status = _run(
        runtime_python, *command, "status", "--root", repo.as_posix(), "--json", env=environment
    )
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["data"]["hook_runtime"]["current"] is True
    (hooks_path / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    stale_status = _run(
        runtime_python,
        *command,
        "status",
        "--root",
        repo.as_posix(),
        "--json",
        env=environment,
    )
    repair = json.loads(stale_status.stdout)["data"]["hook_runtime"]["next_action"]
    assert shlex.split(repair)[:5] == [runtime_python.as_posix(), *command]
    repaired = subprocess.run(
        shlex.split(repair), capture_output=True, text=True, check=False, env=environment
    )
    assert repaired.returncode == 0, repaired.stdout or repaired.stderr
    assert json.loads(repaired.stdout)["verdict"] == "pass"
    proof = _run(
        runtime_python, *command, "prove", "--root", repo.as_posix(), "--json", env=environment
    )
    assert proof.stdout, proof.stderr
    assert json.loads(proof.stdout)["command"] == "prove"


def _prove_adopter_bootstrap(
    *,
    runtime_python: Path,
    repo: Path,
    environment: dict[str, str],
) -> None:
    """Prove a package-only runtime owns lane and first-Change bootstrap."""
    command = (runtime_python.as_posix(), "-B", "-I", "-m", "ethos.cli")
    holder = "agent:test:package-only:bootstrap"
    lane_environment = {**environment, "ETHOS_ACTOR": holder}
    worktree = repo.parent / "repo-work-bootstrap-change"
    started = subprocess.run(
        (
            *command,
            "lane",
            "start",
            "bootstrap-change",
            "--root",
            repo.as_posix(),
            "--path",
            worktree.as_posix(),
            "--holder-ref",
            holder,
            "--apply",
            "--json",
        ),
        capture_output=True,
        text=True,
        check=False,
        env=lane_environment,
    )
    assert started.returncode == 0, started.stdout or started.stderr
    report = json.loads(started.stdout)
    assert report["verdict"] == "pass", report
    bootstrap = report["data"]["runner_bootstrap"]
    assert shlex.split(bootstrap["command"]) == list(command)
    assert bootstrap["environment_scope"] == "git_common_package_runtime"
    assert "uv run" not in bootstrap["next_action"]

    status = subprocess.run(
        shlex.split(bootstrap["next_action"]),
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
        env=lane_environment,
    )
    assert status.stdout, status.stderr
    assert json.loads(status.stdout)["command"] == "status"

    change_root = "openspec/changes/bootstrap-change"
    prewrite = _run(
        runtime_python,
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "lane",
        "prewrite",
        change_root,
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--root",
        worktree.as_posix(),
        "--json",
        env=lane_environment,
    )
    assert prewrite.stdout, prewrite.stderr
    prewrite_report = json.loads(prewrite.stdout)
    assert prewrite_report["verdict"] == "block"
    assert prewrite_report["required_gaps"] == [
        "openspec_change_metadata_prewrite_required:bootstrap-change"
    ]
    next_action = shlex.split(prewrite_report["next_action"])
    assert next_action[:3] == ["ethos", "lane", "prewrite"]
    assert next_action[3:5] == ["--paths", f"{change_root}/.openspec.yaml"]


def test_package_gate_order_and_offline_contract_have_one_machine_owner() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}
    smoke = gates["local-install-smoke"]
    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert smoke["depends_on"] == ["build"]
    assert smoke["network_policy"] == "offline"
    assert smoke["writes_files"] is True


def test_adopter_line_endings_ignore_host_autocrlf() -> None:
    def run(*command: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    with TemporaryDirectory(prefix="ethos-line-ending-") as directory:
        root = Path(directory)
        adopter = root / "adopter"
        materialize_adopter(
            adopter,
            openspec_config=ROOT / "openspec/config.yaml",
            run=run,
        )
        run("git", "config", "core.autocrlf", "true", cwd=adopter)

        assert line_ending_conformance(adopter, run=run) == ["lf", "crlf"]


def test_package_only_runtime_behavior_remains_owned_by_install_smoke() -> None:
    owner = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")
    assert "build/runtime/work/local-install-smoke" in owner
    assert '"--source-root"' not in owner
    assert '"external_governance_available": False' in owner
    assert '"hosted_ci_status_claimed": False' in owner
    assert '"publish",\n            "--ref"' in owner
    assert '"refs/heads/proposal/package-smoke"' in owner
    assert '"publish", "--proposal"' not in owner
    assert "required_gaps={json.dumps(gaps)}" in owner
    assert "command={' '.join(executed_args)}" in owner


def test_install_smoke_prepares_frozen_supply_before_offline_install(
    monkeypatch,
) -> None:
    events: list[object] = []
    session = cast("nox.Session", object())
    monkeypatch.setattr(delivery_pipeline, "prepare_supply", lambda: events.append("supply"))
    monkeypatch.setattr(
        delivery_pipeline,
        "run_install_smoke",
        lambda observed: events.append(("install", observed)),
    )

    DeliveryPipeline(
        runtime=cast("ProjectRuntime", object()),
        node_package_supply=ROOT / "node_modules",
    ).prove_install(session)

    assert events == ["supply", ("install", session)]


def test_packaged_vector_carries_the_minimal_commitment_contract() -> None:
    vectors = (ROOT / "tests/fixtures/semantic-contract/vectors.json").read_text(encoding="utf-8")
    commitment = Commitment.model_validate_json(json.loads(vectors)["commitment"]["canonical_json"])
    assert commitment.model_dump(mode="json") == {
        "schema_version": 3,
        "id": "change:model-promotion-successor",
        "acceptance": ["selected_input_is_bound"],
    }


def test_hook_install_runs_from_an_isolated_wheel_without_checkout(tmp_path: Path) -> None:
    supply = resolve_node_package_supply(ROOT)
    bootstrap_environment: dict[str, str] = {
        **os.environ,
        "ETHOS_NODE_PACKAGE_SUPPLY": supply.as_posix(),
        "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT))),
    }
    bootstrap_repo = tmp_path / "bootstrap-repo"
    bootstrap_repo.mkdir()
    assert _git(bootstrap_repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    bootstrap = _run(
        Path(sys.executable),
        "-m",
        "ethos.cli",
        "hook",
        "install",
        "--root",
        bootstrap_repo.as_posix(),
        "--json",
        env=bootstrap_environment,
    )
    assert bootstrap.returncode == 0, bootstrap.stdout + bootstrap.stderr
    bootstrap_report = json.loads(bootstrap.stdout)
    assert bootstrap_report["verdict"] == "pass", bootstrap_report
    package_python = Path(bootstrap_report["data"]["python"])
    _assert_runtime_excludes_development_dependencies(package_python)
    packaged_identity = BuildIdentity(
        product_version=bootstrap_report["data"]["product_version"],
        distribution_version=bootstrap_report["data"]["distribution_version"],
        source_commit=bootstrap_report["data"]["source_commit"],
        source_tree=bootstrap_report["data"]["source_tree"],
    )
    assert packaged_identity == runtime_build_identity(ROOT)
    bootstrap_environment.pop("PYTHONPATH")

    repo = tmp_path / "repo"
    repo.mkdir()
    materialize_adopter(
        repo,
        openspec_config=ROOT / "openspec/config.yaml",
        run=lambda *command, cwd=repo: subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
    )
    assert _git(repo, "rm", "-r", "openspec/changes/smoke-change").returncode == 0
    assert _git(repo, "commit", "-m", "remove bootstrap fixture change").returncode == 0
    candidate = tmp_path / "repo-candidate-dev"
    assert (
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "candidate/dev",
            candidate.as_posix(),
            "dev",
        ).returncode
        == 0
    )

    package_only_environment = {
        **bootstrap_environment,
        "UV_CACHE_DIR": (tmp_path / "empty-uv-cache").as_posix(),
    }
    installed = _run(
        package_python,
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "hook",
        "install",
        "--root",
        repo.as_posix(),
        "--json",
        env=package_only_environment,
    )

    assert installed.returncode == 0, installed.stderr
    report = json.loads(installed.stdout)
    assert report["verdict"] == "pass", report
    assert report["data"]["source_commit"] == packaged_identity.source_commit
    assert report["data"]["source_tree"] == packaged_identity.source_tree
    assert report["data"]["expected_source_commit"] == packaged_identity.source_commit
    assert report["data"]["expected_source_tree"] == packaged_identity.source_tree
    assert report["data"]["current"] is True
    assert report["data"]["next_action"] == ""
    runtime_python = Path(report["data"]["python"])
    _assert_runtime_manifest(report["data"], repo)
    _assert_runtime_excludes_development_dependencies(runtime_python)
    bootstrap_repo.rename(tmp_path / "retired-bootstrap-repo")
    git_executable = shutil.which("git")
    assert git_executable is not None
    package_environment = {
        **package_only_environment,
        "PATH": os.pathsep.join((str(Path(git_executable).parent), "/usr/bin", "/bin")),
    }
    assert shutil.which("ethos", path=package_environment["PATH"]) is None
    _prove_relocated_runtime(
        runtime_python=runtime_python,
        repo=repo,
        hooks_path=Path(report["data"]["hooks_path"]),
        environment=package_environment,
    )
    _prove_adopter_bootstrap(
        runtime_python=runtime_python,
        repo=repo,
        environment=package_environment,
    )
    version = _run(
        runtime_python,
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "--version",
        "--json",
        env=package_environment,
    )
    assert version.returncode == 0, version.stderr
    version_identity = json.loads(version.stdout)["data"]["identity"]
    assert version_identity == {
        "schema_version": 1,
        **packaged_identity.projection(),
        "wheel_sha256": report["data"]["wheel_sha256"],
        "runtime_digest": report["data"]["runtime_digest"],
    }


def _assert_runtime_excludes_development_dependencies(python: Path) -> None:
    probe = (
        "import importlib.util; "
        "assert importlib.util.find_spec('pytest') is None; "
        "assert importlib.util.find_spec('ruff') is None"
    )
    assert _run(python, "-B", "-I", "-c", probe, env=os.environ.copy()).returncode == 0
