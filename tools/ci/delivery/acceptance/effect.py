"""Offline wheel-install smoke owned by the repository Nox graph."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tomllib
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import copy_context
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import tools.ci.delivery.acceptance.adopter as adopter_fixture
import tools.ci.delivery.acceptance.brownfield as brownfield_acceptance
import tools.ci.delivery.acceptance.invocation as cli_invocation
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.process import command_scope
from ethos.adapters.process import defer_interruptions
from ethos.adapters.process import run_command
from ethos.adapters.process import windows_powershell
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.materialization.dependency_supply import install_locked_runtime
from ethos.adapters.repo.runtime.materialization.dependency_supply import (
    prepare_locked_requirements,
)
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import current_runtime
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.acceptance.receipt import package_acceptance_evidence
from tools.ci.delivery.acceptance.receipt import package_failure_evidence
from tools.ci.delivery.artifact import require_artifact_current
from tools.ci.delivery.artifact import selected_wheel
from tools.ci.delivery.distribution import package_runtime
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    from concurrent.futures import Future

    import nox

    from ethos.adapters.repo.runtime.transition import PackageArtifact

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
    with observe_stage(cli_invocation.command_label(command), kind="process", target=cwd.name):
        completed = run_command(
            cwd, command, env=env, inherit_environment=env is None, remove_env_prefixes=("GIT_",)
        )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        rendered = " ".join(command)
        message = f"command failed ({completed.returncode}): {rendered}\n{detail}"
        raise RuntimeError(message)
    return completed.stdout.strip()


def independent_host_environment() -> tuple[dict[str, str], str]:
    """Retain native OS context and Git without inheriting agent control planes."""
    git = Path(_executable("git")).resolve()
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "ALLUSERSPROFILE",
            "APPDATA",
            "COMMONPROGRAMFILES",
            "COMSPEC",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "LOCALAPPDATA",
            "PATHEXT",
            "PROGRAMDATA",
            "PROGRAMFILES",
            "SYSTEMDRIVE",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "USER",
            "USERPROFILE",
            "USERNAME",
            "UV_PYTHON_INSTALL_DIR",
            "WINDIR",
        }
    }
    native_dirs = ()
    if os.name == "nt":
        powershell = Path(windows_powershell())
        native_dirs = (powershell.parents[2], powershell.parents[3])
    env["PATH"] = os.pathsep.join((str(git.parent), *(str(path) for path in native_dirs)))
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
    env, git = independent_host_environment()
    head = run_command(
        adopter,
        (git, "rev-parse", "HEAD"),
        env=env,
        check=True,
        inherit_environment=False,
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
            data = payload.get("data")
            plan = data.get("transition_plan") if isinstance(data, dict) else None
            effect = plan.get("effect") if isinstance(plan, dict) else None
            required = payload.get("required_gaps")
            gaps = tuple(str(gap) for gap in required) if isinstance(required, list) else ()
            if (
                not isinstance(effect, dict)
                or effect.get("operation") != "git.ref.compare-and-swap"
                or any(
                    gap.startswith(("publication_topology_", "publication_source_invalid:"))
                    for gap in gaps
                )
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


def observe_installed_package(smoke: Path, adopter: Path) -> tuple[str, str, dict[str, object]]:
    python, ethos = _venv_executable(smoke, "python"), _venv_executable(smoke, "ethos")
    _run(str(ethos), "--help", "--root", str(adopter), cwd=WORK)
    version = _run(str(ethos), "--version", "--root", str(adopter), cwd=WORK)
    origin = _run(
        str(python),
        "-B",
        "-I",
        "-c",
        "from pathlib import Path; import ethos,sys; "
        "from ethos.repository.release.identity import packaged_build_identity; "
        "assert packaged_build_identity().distribution_version in sys.argv[1], "
        "'installed_console_identity_mismatch'; print(Path(ethos.__file__).resolve())",
        version,
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
    cli_invocation.require_installed_guidance(status_json, origin)
    _run(
        str(python),
        "-c",
        "from ethos.adapters.openspec.cli import "
        "OFFICIAL_PACKAGE_SPEC, openspec_base_command, verify_official_cli; "
        "c=openspec_base_command(); assert c is not None; r=verify_official_cli(c); "
        "assert r['verdict']=='pass' and r['package']==OFFICIAL_PACKAGE_SPEC",
        cwd=adopter,
    )
    command_plane = json.loads(
        _run(
            str(python),
            "-B",
            "-I",
            str(Path(__file__).with_name("mcp.py")),
            str(ethos),
            str(WORK),
            cwd=WORK,
        )
    )
    return origin, version, command_plane


def _observe_package(
    session: nox.Session, selected: PackageArtifact, *, head: str
) -> dict[str, object]:
    """Execute the complete installed workload on one supplied package identity."""
    wheel = selected.path
    smoke, adopter = WORK / "venv", WORK / "adopter"
    uv, source_python = RUNTIME.script("uv"), RUNTIME.python
    with observe_stage("locked_package_installation"):
        _run(uv, "venv", "--offline", "--python", str(source_python), str(smoke))
        requirements = prepare_locked_requirements(ROOT, WORK, source_python)
        install_locked_runtime(
            ROOT,
            source_python,
            _venv_executable(smoke, "python"),
            wheel,
            requirements,
        )
    with observe_stage("adopter_preparation"):
        adopter_fixture.materialize_adopter(
            adopter,
            openspec_config=ROOT / "openspec/config.yaml",
            run=_run,
        )
        line_endings = adopter_fixture.line_ending_conformance(adopter, run=_run)
    with observe_stage("installed_command_plane"):
        origin, version, command_plane = observe_installed_package(smoke, adopter)
    installed_ethos = _venv_executable(smoke, "ethos")
    build, wheel_sha256 = selected.build, selected.sha256
    package_environment = {**independent_host_environment()[0], "UV_OFFLINE": "1"}
    # Formation owns only the repositories it creates, so it runs beside the other
    # installed-console stages; the lifecycle waits for it before retiring the console.
    with ThreadPoolExecutor(max_workers=1) as formation_pool, command_scope():
        # Ty cannot solve the result type through the generic Context.run.
        formation_run = cast(
            "Future[dict[str, object]]",
            formation_pool.submit(
                copy_context().run,
                adopter_fixture.prove_formation,
                installed_ethos,
                WORK,
                origin=origin,
                environment=package_environment,
            ),
        )
        with observe_stage("host_independence"):
            independent_host = observe_independent_command_plane(installed_ethos, adopter)
            _run(uv, "pip", "check", "--python", str(_venv_executable(smoke, "python")))
        with observe_stage("wheel_resources"):
            resources = _verify_resources(wheel)
        with observe_stage("brownfield"):
            brownfield = brownfield_acceptance.prove_brownfield(
                installed_ethos, WORK, environment=package_environment, run=_run
            )
        lifecycle = runtime_acceptance.observe_lifecycle(
            installed_ethos=installed_ethos,
            bootstrap_environment=smoke,
            bootstrap_repository=WORK / "bootstrap-repository",
            repository=adopter,
            build=build,
            wheel_sha256=wheel_sha256,
            environment=package_environment,
            bootstrap_users=(formation_run,),
            run=_run,
        )
        formation = formation_run.result()
    runtime = current_runtime(Path(git_common_dir(adopter)), expected_build=build).root
    with observe_stage("runtime_archive"):
        distribution = package_runtime(
            runtime,
            wheel,
            WORK / "native" / f"ethos-{build.distribution_version}.tar.gz",
        )
    distribution["shared_supply"] = runtime_acceptance.prove_shared_supply(
        Path(str(distribution["path"])), WORK, environment=package_environment
    )
    distribution.pop("path")
    distribution.pop("homebrew_cask", None)
    distribution["retained"] = False
    require_artifact_current(selected, head=head, repo=ROOT)
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
        command_plane=command_plane,
        formation=formation,
        brownfield=brownfield,
        resources=resources,
        runtime_lifecycle=lifecycle,
        generated_at=datetime.now(UTC),
    )
    payload["distribution"] = distribution
    payload["build_identity"] = build.projection()
    return payload


def run(
    session: nox.Session, *, artifact: PackageArtifact | None = None, evidence: Path | None = None
) -> None:
    """Verify one exact wheel and finalize owned work before restoring interruption."""
    head = current_tracked_head(ROOT)
    output = evidence if evidence is not None else EVIDENCE
    selected = artifact or selected_wheel(ROOT, head=head, artifacts=ARTIFACTS)
    require_artifact_current(selected, head=head, repo=ROOT)
    terminal, events = output.with_suffix(".terminal.json"), output.with_suffix(".events.jsonl")
    with (
        command_scope(handle_termination=True) as scope,
        cli_invocation.acceptance_observation(events, head=head, wheel_sha256=selected.sha256),
    ):
        try:

            def retain_failure(error: BaseException) -> None:
                pending = terminal.with_suffix(".tmp")
                try:
                    pending.write_text(
                        json.dumps(
                            package_failure_evidence(
                                head=head,
                                wheel_sha256=selected.sha256,
                                error=error,
                                owned_work_absent=not os.path.lexists(WORK),
                                acceptance_written=output.exists(),
                                generated_at=datetime.now(UTC),
                            ),
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    pending.replace(terminal)
                finally:
                    pending.unlink(missing_ok=True)

            try:
                with defer_interruptions(), observe_stage("setup"):
                    if WORK.exists():
                        remove_generated_tree(WORK)
                    output.unlink(missing_ok=True)
                    terminal.unlink(missing_ok=True)
                    WORK.mkdir(parents=True)
                with observe_stage("package_acceptance"):
                    payload = {
                        **_observe_package(session, selected, head=head),
                        "execution_events": events.as_posix(),
                    }
                if artifact is not None:
                    payload["command"] = (
                        cast("str", payload["command"]) + f" -- --release --expect-head {head}"
                    )
            except BaseException as error:
                with defer_interruptions():
                    try:
                        retain_failure(error)
                    finally:
                        scope.cancel()
                    raise
            finally:
                with defer_interruptions(), ExitStack() as cleanup:
                    cleanup.callback(remove_generated_tree, WORK)
                    with observe_stage("owned_cleanup"):
                        cleanup.__exit__(*sys.exc_info())
            with defer_interruptions():
                rendered = json.dumps(payload, indent=2, sort_keys=True)
                session.log(rendered)
                output.write_text(rendered + "\n", encoding="utf-8")
        except BaseException as error:
            with defer_interruptions():
                output.unlink(missing_ok=True)
                retain_failure(error)
                raise
