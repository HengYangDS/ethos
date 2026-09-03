"""Offline wheel-install smoke owned by the repository Nox graph."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tomllib
import zipfile
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import tools.ci.delivery.acceptance.adopter as adopter_fixture
import tools.ci.delivery.acceptance.invocation as cli_invocation
import tools.ci.delivery.acceptance.lane as lane_acceptance
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import wheel_build_identity
from tools.ci.delivery import supply
from tools.ci.delivery.acceptance.receipt import package_acceptance_evidence
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    from collections.abc import Mapping

    import nox

ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = ROOT / "build/artifacts/python"
WORK = ROOT / "build/runtime/work/local-install-smoke"
EVIDENCE = ROOT / "build/evidence/local-install/smoke.json"
RUNTIME = ProjectRuntime.discover(ROOT)


def _venv_executable(root: Path, name: str) -> Path:
    """Return a virtual-environment executable on POSIX or Windows."""
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return root / directory / f"{name}{suffix}"


def _executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        message = f"required executable is unavailable: {name}"
        raise RuntimeError(message)
    return executable


def _run(
    *command: str,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> str:
    completed = run_command(cwd, command, env=env, remove_env_prefixes=("GIT_",))
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        rendered = " ".join(command)
        message = f"command failed ({completed.returncode}): {rendered}\n{detail}"
        raise RuntimeError(message)
    return completed.stdout.strip()


def _single_wheel() -> Path:
    wheels = tuple(ARTIFACTS.glob("ethos-*.whl"))
    if len(wheels) != 1:
        message = "local install smoke requires exactly one ETHOS wheel"
        raise RuntimeError(message)
    return wheels[0]


def _independent_host_environment() -> tuple[dict[str, str], str]:
    """Return the smallest host environment that supplies Git but no host control plane."""
    git = Path(_executable("git")).resolve()
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "COMSPEC",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "USER",
            "USERNAME",
        }
    }
    env["PATH"] = str(git.parent)
    if shutil.which("git", path=env["PATH"]) is None:
        message = "minimal host environment cannot resolve Git"
        raise RuntimeError(message)
    unavailable = [name for name in ("workstation", "wcp") if shutil.which(name, path=env["PATH"])]
    if unavailable:
        raise RuntimeError(
            "external governance executable leaked into package smoke: " + ", ".join(unavailable)
        )
    return env, git.as_posix()


def observe_independent_command_plane(ethos: Path, adopter: Path) -> dict[str, object]:
    """Run the installed reader and lane admission surface without a host control plane."""
    env, git = _independent_host_environment()
    head = run_command(
        adopter,
        (git, "rev-parse", "HEAD"),
        env=env,
        check=True,
        remove_env_prefixes=("GIT_",),
    ).stdout.strip()
    holder = "agent:test:package-only:independence"
    suffix = ("--root", str(adopter), "--json")
    commands = (
        ("status", *suffix),
        ("plan", "--changed", *suffix),
        (
            "lane",
            "prewrite",
            "README.md",
            "--editor-root",
            str(adopter),
            "--require-editor-root",
            *suffix,
        ),
        (
            "lane",
            "start",
            "smoke-change",
            "--holder-ref",
            holder,
            *suffix,
        ),
        ("prove", *suffix),
        ("land", *suffix),
        (
            "publish",
            "--ref",
            "refs/heads/proposal/package-smoke",
            "--probe-remote",
            "--expect-head",
            head,
            *suffix,
        ),
        (
            "lane",
            "retire",
            "absorbed-ref",
            "--branch",
            "work/absent",
            "--expect-head",
            "0" * 40,
            "--accepted-head",
            "0" * 40,
            *suffix,
        ),
    )
    checked = []
    for args in commands:
        _returncode, payload, _diagnostic = cli_invocation.invoke(
            adopter,
            (str(ethos), *args),
            environment=env,
        )
        if args[:2] == ("publish", "--ref"):
            plan = payload.get("data", {}).get("transition_plan", {})
            gaps = tuple(str(gap) for gap in payload.get("required_gaps", ()))
            if plan.get("effect", {}).get("operation") != "git.ref.compare-and-swap" or any(
                gap.startswith(("publication_topology_", "publication_source_invalid:"))
                for gap in gaps
            ):
                message = (
                    "installed full-ref publication plan is unavailable: "
                    f"command={' '.join(args)} required_gaps={json.dumps(gaps)}"
                )
                raise RuntimeError(message)
        checked.append(" ".join(args[:2]))
    return {
        "git": git,
        "path": env["PATH"],
        "external_governance_available": False,
        "commands": checked,
    }


def _verify_resources(wheel: Path) -> list[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    with zipfile.ZipFile(wheel) as archive:
        for source, target in declared.items():
            source_path = ROOT / source
            if source_path.is_file():
                pairs = ((source_path, target),)
            else:
                pairs = tuple(
                    (path, f"{target}/{path.relative_to(source_path).as_posix()}")
                    for path in source_path.rglob("*")
                    if path.is_file()
                )
            for canonical, packaged in pairs:
                if archive.read(packaged) != canonical.read_bytes():
                    message = f"wheel resource differs from canonical source: {packaged}"
                    raise RuntimeError(message)
    return sorted(declared.values())


def observe_installed_package(smoke: Path, adopter: Path) -> tuple[str, str]:
    python, ethos = _venv_executable(smoke, "python"), _venv_executable(smoke, "ethos")
    _run(str(ethos), "--help", cwd=WORK)
    version = _run(str(ethos), "--version", cwd=WORK)
    origin = _run(
        str(python),
        "-c",
        "from pathlib import Path; import ethos; print(Path(ethos.__file__).resolve())",
        cwd=WORK,
    )
    if not Path(origin).is_relative_to(smoke):
        message = f"installed package escaped smoke environment: {origin}"
        raise RuntimeError(message)
    status_json = _run(str(ethos), "status", "--root", str(adopter), "--json", cwd=adopter)
    _run(
        str(python),
        "-I",
        "-c",
        "import json,sys; "
        "from ethos.result import EthosResult; "
        "result=EthosResult.from_payload(json.loads(sys.argv[1])); "
        "assert result.command=='status' and result.verdict in {'pass','block','unknown'}",
        status_json,
        cwd=adopter,
    )
    _run(
        str(python),
        "-c",
        "from ethos.adapters.openspec.cli import "
        "OFFICIAL_PACKAGE_SPEC, openspec_base_command, verify_official_cli; "
        "c=openspec_base_command(); assert c is not None; r=verify_official_cli(c); "
        "assert r['verdict']=='pass' and r['package']==OFFICIAL_PACKAGE_SPEC",
        cwd=adopter,
    )
    return origin, version


def _activation_observation(report: Mapping[str, object]) -> dict[str, object]:
    """Project one successful runtime activation into stable receipt evidence."""
    return {
        "state": "passed",
        "runtime_digest": str(report["runtime_digest"]),
        "wheel_sha256": str(report["wheel_sha256"]),
        "source_commit": str(report["source_commit"]),
        "source_tree": str(report["source_tree"]),
    }


def observe_runtime_lifecycle(
    *,
    installed_ethos: Path,
    bootstrap_environment: Path,
    bootstrap_repository: Path,
    repository: Path,
    build: BuildIdentity,
    wheel_sha256: str,
    environment: Mapping[str, str],
) -> dict[str, Mapping[str, object]]:
    """Execute and post-observe one complete package-only runtime lifecycle."""
    adopter_fixture.materialize_bootstrap_repository(bootstrap_repository, run=_run)
    candidate = adopter_fixture.prepare_acceptance_topology(repository, run=_run)
    try:
        bootstrap_report = runtime_acceptance.activate_from_entrypoint(
            installed_ethos,
            bootstrap_repository,
            environment=environment,
        )
        bootstrap_python = runtime_acceptance.require_manifest(
            bootstrap_report,
            bootstrap_repository,
            build=build,
            wheel_sha256=wheel_sha256,
        )
        successor_report = runtime_acceptance.activate_from_runtime(
            bootstrap_python,
            repository,
            environment=environment,
        )
        runtime_python = runtime_acceptance.require_manifest(
            successor_report,
            repository,
            build=build,
            wheel_sha256=wheel_sha256,
        )
    finally:
        if bootstrap_environment.exists():
            shutil.rmtree(bootstrap_environment)
        remove_generated_tree(bootstrap_repository)

    runtime_digest = str(successor_report["runtime_digest"])
    hooks_path = Path(str(successor_report["hooks_path"]))
    return {
        "hook_activation": _activation_observation(bootstrap_report),
        "successor_activation": {
            **_activation_observation(successor_report),
            "candidate_worktree": candidate.as_posix(),
        },
        "development_dependencies": runtime_acceptance.require_production_dependencies(
            runtime_python
        ),
        "immutable_identity": runtime_acceptance.require_version_identity(
            runtime_python,
            build=build,
            wheel_sha256=wheel_sha256,
            runtime_digest=runtime_digest,
            environment=environment,
        ),
        "relocation_repair": runtime_acceptance.prove_repair(
            runtime_python,
            repository,
            hooks_path=hooks_path,
            environment=environment,
        ),
        **lane_acceptance.prove_lifecycle(
            runtime_python,
            repository,
            environment=environment,
        ),
    }


def run(session: nox.Session) -> None:
    """Install the built wheel into a fresh offline environment and attest it."""
    head = current_tracked_head(ROOT)
    if WORK.exists():
        remove_generated_tree(WORK)
    EVIDENCE.unlink(missing_ok=True)
    WORK.mkdir(parents=True)
    try:
        wheel, smoke, adopter = _single_wheel(), WORK / "venv", WORK / "adopter"
        uv, source_python = RUNTIME.script("uv"), Path(sys.executable)
        _run(uv, "venv", "--offline", "--python", str(source_python), str(smoke))
        supply.install_into(
            _venv_executable(smoke, "python"),
            constraints=WORK / "runtime-constraints.txt",
        )
        _run(
            uv,
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--cache-dir",
            str(supply.UV_CACHE),
            "--python",
            str(_venv_executable(smoke, "python")),
            str(wheel),
        )
        adopter_fixture.materialize_adopter(
            adopter,
            openspec_config=ROOT / "openspec/config.yaml",
            run=_run,
        )
        line_endings = adopter_fixture.line_ending_conformance(adopter, run=_run)
        origin, version = observe_installed_package(smoke, adopter)
        installed_ethos = _venv_executable(smoke, "ethos")
        independent_host = observe_independent_command_plane(installed_ethos, adopter)
        _run(uv, "pip", "check", "--python", str(_venv_executable(smoke, "python")))
        resources = _verify_resources(wheel)
        build = wheel_build_identity(wheel)
        wheel_sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()
        package_environment, _git = _independent_host_environment()
        package_environment["UV_CACHE_DIR"] = supply.UV_CACHE.as_posix()
        package_environment["UV_OFFLINE"] = "1"
        lifecycle = observe_runtime_lifecycle(
            installed_ethos=installed_ethos,
            bootstrap_environment=smoke,
            bootstrap_repository=WORK / "bootstrap-repository",
            repository=adopter,
            build=build,
            wheel_sha256=wheel_sha256,
            environment=package_environment,
        )
        if current_tracked_head(ROOT) != head:
            session.error(f"local install smoke HEAD moved from {head}")
        payload = package_acceptance_evidence(
            root=ROOT,
            head=head,
            wheel=wheel,
            origin=origin,
            version=version,
            line_endings=line_endings,
            independent_host=independent_host,
            resources=resources,
            runtime_lifecycle=lifecycle,
            generated_at=datetime.now(UTC),
        )
    finally:
        remove_generated_tree(WORK)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    session.log(json.dumps(payload, indent=2, sort_keys=True))
