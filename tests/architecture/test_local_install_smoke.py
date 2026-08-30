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
from ethos.contracts.semantic import Commitment
from ethos.repository.release.identity import BuildIdentity
from tools.ci.delivery.adopter_fixture import line_ending_conformance
from tools.ci.delivery.adopter_fixture import materialize_adopter
from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.toolchain.node import node_runtime

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]


def _python_home_executable(runtime: Path, name: str) -> Path:
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return runtime / directory / f"{name}{suffix}"


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


def _prove_relocated_runtime(
    *,
    runtime_ethos: Path,
    repo: Path,
    hooks_path: Path,
    environment: dict[str, str],
) -> None:
    """Prove status, repair, and proof stay executable after package relocation."""
    status = _run(runtime_ethos, "status", "--root", repo.as_posix(), "--json", env=environment)
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["data"]["hook_runtime"]["current"] is True
    (hooks_path / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    stale_status = _run(
        runtime_ethos, "status", "--root", repo.as_posix(), "--json", env=environment
    )
    repair = json.loads(stale_status.stdout)["data"]["hook_runtime"]["next_action"]
    assert shlex.split(repair)[0] == runtime_ethos.as_posix()
    repaired = subprocess.run(
        shlex.split(repair), capture_output=True, text=True, check=False, env=environment
    )
    assert repaired.returncode == 0, repaired.stdout or repaired.stderr
    assert json.loads(repaired.stdout)["verdict"] == "pass"
    proof = _run(runtime_ethos, "prove", "--root", repo.as_posix(), "--json", env=environment)
    assert proof.stdout, proof.stderr
    assert json.loads(proof.stdout)["command"] == "prove"


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
        node=Path("node"),
        npm_cli=Path("npm-cli.js"),
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
    node, npm_cli = node_runtime()
    bootstrap_environment: dict[str, str] = {
        **os.environ,
        "ETHOS_BUILD_NODE": str(node),
        "ETHOS_BUILD_NPM_CLI": str(npm_cli),
    }
    bootstrap_environment.pop("PYTHONPATH", None)
    source_ethos = _python_home_executable(Path(sys.executable).parent.parent, "ethos")
    bootstrap_repo = tmp_path / "bootstrap-repo"
    bootstrap_repo.mkdir()
    assert _git(bootstrap_repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    bootstrap = _run(
        source_ethos,
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
    package_ethos = _python_home_executable(package_python.parent.parent, "ethos")
    _assert_runtime_excludes_development_dependencies(package_python)
    packaged_identity = BuildIdentity(
        product_version=bootstrap_report["data"]["product_version"],
        distribution_version=bootstrap_report["data"]["distribution_version"],
        source_commit=bootstrap_report["data"]["source_commit"],
        source_tree=bootstrap_report["data"]["source_tree"],
    )
    assert packaged_identity == runtime_build_identity(ROOT)

    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    package_only_environment = {
        **bootstrap_environment,
        "UV_CACHE_DIR": (tmp_path / "empty-uv-cache").as_posix(),
    }
    installed = _run(
        package_ethos,
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
    runtime_ethos = _python_home_executable(runtime_python.parent.parent, "ethos")
    git_executable = shutil.which("git")
    assert git_executable is not None
    package_environment = {
        **package_only_environment,
        "PATH": os.pathsep.join((str(Path(git_executable).parent), "/usr/bin", "/bin")),
    }
    assert shutil.which("ethos", path=package_environment["PATH"]) is None
    _prove_relocated_runtime(
        runtime_ethos=runtime_ethos,
        repo=repo,
        hooks_path=Path(report["data"]["hooks_path"]),
        environment=package_environment,
    )
    version = _run(runtime_ethos, "--version", "--json", env=package_environment)
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
