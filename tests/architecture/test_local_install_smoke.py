from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.hook_runtime_install as runtime_install
import tools.ci.delivery.pipeline as delivery_pipeline
from ethos.adapters.repo.hook.source_identity import runtime_source_identity
from ethos.contracts.semantic import load_commitment_file
from tools.ci.delivery.adopter_fixture import commitment_carrier
from tools.ci.delivery.pipeline import DeliveryPipeline

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]


def _venv_executable(venv: Path, name: str) -> Path:
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv / directory / f"{name}{suffix}"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


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


def test_package_only_runtime_behavior_remains_owned_by_install_smoke() -> None:
    owner = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")
    assert "build/runtime/work/local-install-smoke" in owner
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


def test_packaged_vector_derives_a_complete_strict_commitment(
    tmp_path: Path,
) -> None:
    vectors = (ROOT / "tests/fixtures/semantic-contract/vectors.json").read_text(encoding="utf-8")
    carrier = tmp_path / "commitment.toml"
    carrier.write_text(
        commitment_carrier(
            Path("ethos.whl"),
            Path("python"),
            commitment_id="change:install-smoke",
            intent="Prove the installed package carrier.",
            subjects=("repository:install-smoke",),
            scope=("README.md",),
            run=lambda *_args, **_kwargs: vectors,
        ),
        encoding="utf-8",
    )

    commitment = load_commitment_file(carrier)
    assert commitment.id == "change:install-smoke"
    assert commitment.dependencies
    assert commitment.hypotheses
    assert commitment.falsifiers
    assert commitment.experiment_protocols


def test_hook_install_runs_from_an_isolated_wheel_without_checkout(tmp_path: Path) -> None:
    root = ROOT
    uv = Path(sys.executable).with_name("uv.exe" if os.name == "nt" else "uv")
    node_root = Path(import_module("nodejs_wheel").__file__).resolve().parent
    environment: dict[str, str] = {
        **os.environ,
        "ETHOS_BUILD_NODE": (
            node_root / "bin" / ("node.exe" if os.name == "nt" else "node")
        ).as_posix(),
        "ETHOS_BUILD_NPM_CLI": (node_root / "lib/node_modules/npm/bin/npm-cli.js").as_posix(),
    }
    environment.pop("PYTHONPATH", None)
    dist = tmp_path / "dist"
    subprocess.run(
        (uv.as_posix(), "build", "--offline", "--wheel", "--out-dir", dist.as_posix()),
        cwd=root,
        env=environment,
        check=True,
        text=True,
    )
    wheel = next(dist.glob("ethos-*.whl"))
    packaged_identity = runtime_install.wheel_source_identity(wheel)
    assert packaged_identity == runtime_source_identity(root)
    package_venv = tmp_path / "package-venv"
    subprocess.run(
        (
            uv.as_posix(),
            "venv",
            "--relocatable",
            "--python",
            sys.executable,
            package_venv.as_posix(),
        ),
        check=True,
        text=True,
    )
    package_python = _venv_executable(package_venv, "python")
    subprocess.run(
        (
            uv.as_posix(),
            "pip",
            "install",
            "--offline",
            "--python",
            package_python.as_posix(),
            wheel.as_posix(),
        ),
        check=True,
        text=True,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    installed = subprocess.run(
        (
            _venv_executable(package_venv, "ethos").as_posix(),
            "hook",
            "install",
            "--root",
            repo.as_posix(),
            "--json",
        ),
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert installed.returncode == 0, installed.stderr
    report = json.loads(installed.stdout)
    assert report["verdict"] == "pass", report
    assert report["data"]["source_commit"] == packaged_identity.commit
    assert report["data"]["source_tree"] == packaged_identity.tree
    assert report["data"]["expected_source_commit"] == packaged_identity.commit
    assert report["data"]["expected_source_tree"] == packaged_identity.tree
    assert report["data"]["current"] is True
    assert report["data"]["next_action"] == ""
    runtime_python = Path(report["data"]["python"])
    package_venv.rename(tmp_path / "retired-package-venv")
    runtime_ethos = _venv_executable(runtime_python.parent.parent, "ethos")
    rebind_help = subprocess.run(
        (runtime_ethos.as_posix(), "lane", "rebind-commitment", "--help"),
        capture_output=True,
        text=True,
        check=False,
        env={key: value for key, value in environment.items() if key != "PYTHONPATH"},
    )
    derive_help = subprocess.run(
        (runtime_ethos.as_posix(), "lane", "rebind-commitment", "derive", "--help"),
        capture_output=True,
        text=True,
        check=False,
        env={key: value for key, value in environment.items() if key != "PYTHONPATH"},
    )
    assert rebind_help.returncode == 0, rebind_help.stderr
    assert "--receipt" in rebind_help.stdout
    assert derive_help.returncode == 0, derive_help.stderr
    assert "--target-commit" in derive_help.stdout
    version = subprocess.run(
        (runtime_ethos.as_posix(), "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip()
