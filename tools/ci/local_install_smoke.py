"""Offline wheel-install smoke owned by the repository Nox graph."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import tomllib
import zipfile
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import tomli_w

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_command
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "build/artifacts/python"
UV_CACHE = ROOT / "build/runtime/tool-cache/uv"
WORK = ROOT / "build/runtime/work/local-install-smoke"
EVIDENCE = ROOT / "build/evidence/local-install/smoke.json"
CONSTRAINTS = WORK / "runtime-constraints.txt"
SUPPLY_ENVIRONMENT = WORK / "supply-environment"
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
    completed = run_command(cwd, command, env=env)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        rendered = " ".join(command)
        message = f"command failed ({completed.returncode}): {rendered}\n{detail}"
        raise RuntimeError(message)
    return completed.stdout.strip()


def _export_runtime_constraints(uv: str) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    _run(
        uv,
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--offline",
        "--cache-dir",
        str(UV_CACHE),
        "--output-file",
        str(CONSTRAINTS),
    )


def prepare_supply() -> None:
    """Materialize the lock-bound runtime supply for later offline consumption."""
    uv, source_python = RUNTIME.script("uv"), Path(sys.executable)
    if SUPPLY_ENVIRONMENT.exists():
        shutil.rmtree(SUPPLY_ENVIRONMENT)
    _export_runtime_constraints(uv)
    _run(uv, "venv", "--python", str(source_python), str(SUPPLY_ENVIRONMENT))
    _run(
        uv,
        "pip",
        "install",
        "--cache-dir",
        str(UV_CACHE),
        "--require-hashes",
        "--requirements",
        str(CONSTRAINTS),
        "--python",
        str(_venv_executable(SUPPLY_ENVIRONMENT, "python")),
    )
    shutil.rmtree(SUPPLY_ENVIRONMENT)


def _single_wheel() -> Path:
    wheels = tuple(ARTIFACTS.glob("ethos-*.whl"))
    if len(wheels) != 1:
        message = "local install smoke requires exactly one ETHOS wheel"
        raise RuntimeError(message)
    return wheels[0]


def commitment_carrier_from_packaged_vector(
    wheel: Path,
    python: Path,
    *,
    commitment_id: str,
    intent: str,
    subjects: tuple[str, ...],
    scope: tuple[str, ...],
) -> str:
    vector = json.loads(
        _run(
            str(python),
            "-I",
            "-c",
            "import importlib.resources,sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "print(importlib.resources.files('ethos').joinpath("
            "'data/semantic-v2/vectors.json').read_text())",
            str(wheel),
        )
    )
    payload = tomllib.loads(vector["commitment"]["carrier_toml"])
    if not all(key in payload for key in ("id", "intent", "subjects", "scope", "dependencies")):
        message = "packaged semantic-v2 vector has no structured commitment fields"
        raise RuntimeError(message)
    payload.update(id=commitment_id, intent=intent, subjects=list(subjects), scope=list(scope))
    for key, value in payload.items():
        if (
            key not in {"subjects", "scope"}
            and isinstance(value, list)
            and all(isinstance(item, str) for item in value)
        ):
            payload[key] = []
    return tomli_w.dumps(payload)


def write_adopted_reader_compatibility(root: Path) -> None:
    """Materialize the exact read-only schema shape retained by current adopters."""
    ethos = root / ".ethos"
    ethos.mkdir(exist_ok=True)
    (ethos / "profile.toml").write_text(
        """profile_id = "installed-cli-adopter"

[openspec]
material_paths = ["**"]
""",
        encoding="utf-8",
    )
    (ethos / "workspace.toml").write_text(
        """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"

[[branch_roles.transitions]]
id = "accepted-to-release"
source_role = "accepted_root"
target_role = "release_root"
capability = "repository.release"
required_gates = []
required_evidence = ["proof:execution"]
coupled_with = ""
""",
        encoding="utf-8",
    )
    (ethos / "commitment.toml").write_text(
        """id = "repository:installed-cli-adopter"
intent = "Govern the installed CLI adopter."
subjects = ["repository:installed-cli-adopter"]
scope = ["**"]
invariants = ["repository_identity_is_stable"]
acceptance = ["repository_contract_valid"]
authority_refs = ["user_instruction", "AGENTS.md", ".ethos/profile.toml"]
""",
        encoding="utf-8",
    )


def _initialize_adopted_reader(root: Path) -> None:
    git = _executable("git")
    _run(git, "init", "--quiet", "--initial-branch=dev", str(root))
    _run(git, "config", "user.name", "ETHOS Install Smoke", cwd=root)
    _run(git, "config", "user.email", "ethos-install-smoke@example.invalid", cwd=root)
    write_adopted_reader_compatibility(root)
    (root / "README.md").write_text("# adopted reader compatibility\n", encoding="utf-8")
    _run(git, "add", ".", cwd=root)
    _run(git, "commit", "--quiet", "-m", "initialize adopted reader", cwd=root)


def _initialize_adopter(root: Path, wheel: Path, python: Path) -> str:
    git = _executable("git")
    _run(git, "init", "--quiet", "--initial-branch=dev", str(root))
    _run(git, "config", "user.name", "ETHOS Install Smoke", cwd=root)
    _run(git, "config", "user.email", "ethos-install-smoke@example.invalid", cwd=root)
    (root / ".ethos").mkdir()
    change = root / "openspec/changes/smoke-change"
    change.mkdir(parents=True)
    (root / ".ethos/profile.toml").write_text(
        """profile_id = "installed-cli-adopter"

[openspec]
material_paths = ["**"]
""",
        encoding="utf-8",
    )
    (root / ".ethos/commitment.toml").write_text(
        commitment_carrier_from_packaged_vector(
            wheel,
            python,
            commitment_id="repository:installed-cli-adopter",
            intent="Govern the installed CLI adopter.",
            subjects=("repository:installed-cli-adopter",),
            scope=("**",),
        ),
        encoding="utf-8",
    )
    dev = root / "dev"
    dev.mkdir()
    for name in ("verify", "install"):
        command = dev / name
        command.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        command.chmod(0o755)
    (root / ".ethos/release.toml").write_text(
        """[publication]
local_verification_command = "dev/verify"
local_installation_command = "dev/install"

[[publication.peers]]
id = "file"
provider = "git"
role = "package_smoke"
git_remote = "origin"
capabilities = ["repository", "publication"]
""",
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "openspec/config.yaml", root / "openspec/config.yaml")
    (change / "commitment.toml").write_text(
        commitment_carrier_from_packaged_vector(
            wheel,
            python,
            commitment_id="change:smoke-change",
            intent="Exercise installed CLI repository binding.",
            subjects=("repository:installed-cli-adopter",),
            scope=("README.md",),
        ),
        encoding="utf-8",
    )
    (root / "README.md").write_text("# installed CLI adopter\n", encoding="utf-8")
    peer = root.parent / "publication-peer.git"
    _run(git, "init", "--quiet", "--bare", str(peer))
    _run(git, "remote", "add", "origin", str(peer), cwd=root)
    _run(git, "add", ".", cwd=root)
    _run(git, "commit", "--quiet", "-m", "initialize installed CLI adopter", cwd=root)
    return _run(git, "rev-parse", "HEAD", cwd=root)


def _line_ending_conformance(adopter: Path) -> list[str]:
    """Round-trip LF, CRLF, and UTF-8 through Git without text-mode inference."""
    fixtures = {
        "lf": b"portable UTF-8: \xe9\x81\x93\n",
        "crlf": b"portable UTF-8: \xe9\x81\x93\r\n",
    }
    observed: list[str] = []
    for style, payload in fixtures.items():
        relative = f"line-ending-{style}.txt"
        path = adopter / relative
        path.write_bytes(payload)
        _run(_executable("git"), "add", "--", relative, cwd=adopter)
        git_blob = run_command(
            adopter,
            (_executable("git"), "show", f":{relative}"),
            text=False,
            check=True,
        ).stdout
        if git_blob != payload or path.read_bytes() != payload:
            message = f"portable line-ending round-trip failed: {style}"
            raise RuntimeError(message)
        observed.append(style)
    _run(
        _executable("git"),
        "reset",
        "--quiet",
        "--",
        *[f"line-ending-{s}.txt" for s in observed],
        cwd=adopter,
    )
    for style in observed:
        (adopter / f"line-ending-{style}.txt").unlink()
    return observed


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


def _independent_cli_checks(ethos: Path, adopter: Path) -> dict[str, object]:
    """Run the installed reader and lane admission surface without a host control plane."""
    env, git = _independent_host_environment()
    head = run_command(adopter, (git, "rev-parse", "HEAD"), env=env, check=True).stdout.strip()
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
            "--source-root",
            str(adopter),
            "--holder-ref",
            holder,
            *suffix,
        ),
        ("prove", *suffix),
        ("land", *suffix),
        (
            "publish",
            "--proposal",
            "package-smoke",
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
        executed_args = args
        completed = run_command(adopter, (str(ethos), *executed_args), env=env)
        if args[:2] == ("plan", "--changed") and completed.returncode != 0:
            executed_args = ("plan", "--root", str(adopter), "--json")
            completed = run_command(adopter, (str(ethos), *executed_args), env=env)
        if "Traceback" in completed.stderr or "Traceback" in completed.stdout:
            message = "installed CLI emitted traceback without a host control plane"
            raise RuntimeError(message)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            message = f"installed CLI did not emit JSON for {args[:2]}"
            raise RuntimeError(message) from exc
        if payload.get("verdict") not in {"pass", "block", "unknown"}:
            message = f"installed CLI emitted an invalid verdict for {args[:2]}"
            raise RuntimeError(message)
        if args[:2] == ("publish", "--proposal"):
            plan = payload.get("data", {}).get("transition_plan", {})
            gaps = tuple(str(gap) for gap in payload.get("required_gaps", ()))
            if plan.get("effect", {}).get("operation") != "proposal.create" or any(
                gap.startswith("publication_topology_") for gap in gaps
            ):
                message = "installed proposal publication plan is unavailable"
                raise RuntimeError(message)
        checked.append(" ".join(executed_args[:2]))
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


def _installed_cli_checks(smoke: Path, adopter: Path, head: str) -> tuple[str, str, str]:
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
    _run(str(ethos), "status", "--root", str(adopter), "--json", cwd=adopter)
    run_command(
        adopter,
        (str(ethos), "plan", "--changed", "--root", str(adopter), "--json"),
    )
    archive = (
        str(ethos),
        "lane",
        "archive-change",
        "--change",
        "smoke-change",
        "--expect-head",
        head,
        "--root",
        str(adopter),
        "--json",
    )
    run_command(adopter, archive)
    run_command(adopter, (*archive[:-1], "--rebuild-from", head, "--json"))
    status_json = _run(str(ethos), "status", "--root", str(adopter), "--json", cwd=adopter)
    sdk_digest = _run(
        str(python),
        "-I",
        "-c",
        "import importlib.resources,json,sys,tempfile; from pathlib import Path; "
        "from ethos.contracts.semantic import load_commitment_file; "
        "from ethos.result import EthosResult; "
        "result=EthosResult.from_payload(json.loads(sys.argv[1])); "
        "assert result.command=='status' and result.verdict in {'pass','block','unknown'}; "
        "vectors=json.loads(importlib.resources.files('ethos').joinpath("
        "'data/semantic-v2/vectors.json').read_text()); "
        "carrier=Path(tempfile.mkdtemp())/'commitment.toml'; "
        "carrier.write_text(vectors['commitment']['carrier_toml']); "
        "commitment=load_commitment_file(carrier); "
        " print(commitment.digest())",
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
    return origin, version, sdk_digest


def _installed_adopted_reader_checks(ethos: Path, adopter: Path) -> dict[str, object]:
    """Prove source-hidden status/plan compatibility without creating v2 authority."""
    observed: dict[str, object] = {}
    for command in (("status",), ("plan", "--changed")):
        completed = run_command(
            adopter,
            (str(ethos), *command, "--root", str(adopter), "--json"),
        )
        if completed.returncode or "Traceback" in completed.stdout + completed.stderr:
            message = f"installed adopted reader failed: {' '.join(command)}"
            raise RuntimeError(message)
        payload = json.loads(completed.stdout)
        if payload.get("verdict") != "pass" or payload.get("required_gaps"):
            message = f"installed adopted reader blocked: {' '.join(command)}"
            raise RuntimeError(message)
        observed[command[0]] = payload
    plan = observed["plan"]
    if not isinstance(plan, dict):
        message = "installed adopted reader plan is invalid"
        raise TypeError(message)
    compatibility = plan.get("data", {}).get("commitment_compatibility", {})
    if compatibility != {
        "carrier": ".ethos/commitment.toml",
        "carrier_bytes_sha256": hashlib.sha256(
            (adopter / ".ethos/commitment.toml").read_bytes()
        ).hexdigest(),
        "mode": "terminal_v1_read_only",
        "mutation_authority": False,
        "proof_authority": False,
        "schema_version": 1,
    }:
        message = "installed adopted reader compatibility projection drifted"
        raise RuntimeError(message)
    return {
        "status": "pass",
        "plan": "pass",
        "mode": "terminal_v1_read_only",
        "transition_plan_available": plan.get("data", {}).get("transition_plan_available"),
    }


def run(session: nox.Session) -> None:
    """Install the built wheel into a fresh offline environment and attest it."""
    head = current_tracked_head(ROOT)
    if WORK.exists():
        shutil.rmtree(WORK)
    EVIDENCE.unlink(missing_ok=True)
    WORK.mkdir(parents=True)
    wheel, smoke, adopter = _single_wheel(), WORK / "venv", WORK / "adopter"
    adopted_reader = WORK / "adopted-reader"
    uv, source_python = RUNTIME.script("uv"), Path(sys.executable)
    _export_runtime_constraints(uv)
    _run(uv, "venv", "--offline", "--python", str(source_python), str(smoke))
    _run(
        uv,
        "pip",
        "install",
        "--offline",
        "--cache-dir",
        str(UV_CACHE),
        "--constraints",
        str(CONSTRAINTS),
        "--python",
        str(_venv_executable(smoke, "python")),
        str(wheel),
    )
    adopter_head = _initialize_adopter(adopter, wheel, _venv_executable(smoke, "python"))
    _initialize_adopted_reader(adopted_reader)
    line_endings = _line_ending_conformance(adopter)
    origin, version, sdk_digest = _installed_cli_checks(smoke, adopter, adopter_head)
    adopted_reader_result = _installed_adopted_reader_checks(
        _venv_executable(smoke, "ethos"), adopted_reader
    )
    independent_host = _independent_cli_checks(_venv_executable(smoke, "ethos"), adopter)
    _run(uv, "pip", "check", "--python", str(_venv_executable(smoke, "python")))
    resources = _verify_resources(wheel)
    if current_tracked_head(ROOT) != head:
        session.error(f"local install smoke HEAD moved from {head}")
    payload = {
        "schema_version": 1,
        "kind": "ethos_local_install_smoke_evidence",
        "verdict": "pass",
        "state": "passed",
        "head": head,
        "command": "uv run --frozen --offline python -m nox -s install_smoke",
        "generated_at": datetime.now(UTC).isoformat(),
        "head_stability": "verified_before_evidence_write",
        "offline": True,
        "fresh_environment": True,
        "host": {
            "platform": platform.system().lower(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "path_style": "windows" if os.name == "nt" else "posix",
            "line_endings": line_endings,
        },
        "conformance": {
            "subprocess_json": True,
            "host_product_independence": independent_host,
            "python_sdk": True,
            "openspec": True,
            "sdk_commitment_digest": sdk_digest,
            "adopted_reader_compatibility": adopted_reader_result,
        },
        "dependencies": "locked_project_environment_projection",
        "module_origins": {"ethos": origin},
        "cli_checks": [
            "ethos --help and --version",
            (
                "installed lifecycle commands run without a host control plane: "
                "status, plan, prewrite, lane start, prove, land, publish proposal, retire"
            ),
            "installed archive-change and rebuild dry-runs",
            "installed status/plan read current terminal-v1 adopter schema without v2 authority",
            "repository-declared OpenSpec package identity",
            "declared wheel resources match canonical sources",
        ],
        "wheel_resources": resources,
        "version": version,
        "wheels": [
            {
                "path": wheel.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
        ],
        "hosted_ci_status_claimed": False,
        "remote_publication_claimed": False,
        "registry_publication_claimed": False,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    session.log(json.dumps(payload, indent=2, sort_keys=True))
