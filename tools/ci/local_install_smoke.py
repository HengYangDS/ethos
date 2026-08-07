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

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_command

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "build/artifacts/python"
WORK = ROOT / "build/runtime/work/local-install-smoke"
EVIDENCE = ROOT / "build/evidence/local-install/smoke.json"


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


def _project_script(name: str) -> str:
    return str(_venv_executable(Path(sys.executable).parent.parent, name))


def _run(*command: str, cwd: Path = ROOT) -> str:
    completed = run_command(cwd, command, check=True)
    return completed.stdout.strip()


def _single_wheel() -> Path:
    wheels = tuple(ARTIFACTS.glob("ethos-*.whl"))
    if len(wheels) != 1:
        message = "local install smoke requires exactly one ETHOS wheel"
        raise RuntimeError(message)
    return wheels[0]


def _initialize_adopter(root: Path) -> str:
    git = _executable("git")
    _run(git, "init", "--quiet", "--initial-branch=dev", str(root))
    _run(git, "config", "user.name", "ETHOS Install Smoke", cwd=root)
    _run(git, "config", "user.email", "ethos-install-smoke@example.invalid", cwd=root)
    (root / ".ethos").mkdir()
    change = root / "openspec/changes/smoke-change"
    change.mkdir(parents=True)
    shutil.copy2(ROOT / ".ethos/profile.toml", root / ".ethos/profile.toml")
    shutil.copy2(ROOT / "openspec/config.yaml", root / "openspec/config.yaml")
    (change / "commitment.toml").write_text(
        """schema_version = 1
id = "change:smoke-change"
intent = "Exercise installed CLI repository binding."
subjects = ["repository:self"]
scope = ["README.md"]
permissions = ["repository.read", "work-lane.write", "git.ref.compare-and-swap"]
""",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# installed CLI adopter\n", encoding="utf-8")
    _run(git, "add", ".", cwd=root)
    _run(git, "commit", "--quiet", "-m", "initialize installed CLI adopter", cwd=root)
    return _run(git, "rev-parse", "HEAD", cwd=root)


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


def _installed_cli_checks(smoke: Path, adopter: Path, head: str) -> tuple[str, str]:
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


def run(session: nox.Session) -> None:
    """Install the built wheel into a fresh offline environment and attest it."""
    head = current_tracked_head(ROOT)
    if WORK.exists():
        shutil.rmtree(WORK)
    EVIDENCE.unlink(missing_ok=True)
    WORK.mkdir(parents=True)
    wheel, smoke, adopter = _single_wheel(), WORK / "venv", WORK / "adopter"
    uv, source_python = _project_script("uv"), Path(sys.executable)
    _run(uv, "venv", "--offline", "--python", str(source_python), str(smoke))
    _run(
        uv,
        "pip",
        "install",
        "--offline",
        "--python",
        str(_venv_executable(smoke, "python")),
        str(wheel),
    )
    adopter_head = _initialize_adopter(adopter)
    origin, version = _installed_cli_checks(smoke, adopter, adopter_head)
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
        "dependencies": "locked_project_environment_projection",
        "module_origins": {"ethos": origin},
        "cli_checks": [
            "ethos --help and --version",
            "installed status and plan dry-run in an adopter repository",
            "installed archive-change and rebuild dry-runs",
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
