"""Executable portability and orchestration ownership contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_ROOTS = (
    ".config",
    ".ethos",
    ".github",
    "docs",
    "rules",
    "system",
)


def _active_files() -> list[Path]:
    files: list[Path] = []
    for relative in ACTIVE_ROOTS:
        files.extend(path for path in (ROOT / relative).rglob("*") if path.is_file())
    files.extend(path for path in (ROOT / "openspec/specs").rglob("*") if path.is_file())
    files.extend((ROOT / ".gitlab-ci.yml", ROOT / ".pre-commit-config.yaml"))
    return files


def test_active_commands_do_not_encode_posix_virtualenv_layout() -> None:
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in _active_files()
        if ".venv/bin/" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_local_ci_has_one_cross_platform_python_owner() -> None:
    noxfile = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    owner = (ROOT / "tools/ci/local_ci.py").read_text(encoding="utf-8")

    assert "def local_ci(" in noxfile
    assert "ThreadPoolExecutor" in owner
    assert "max_workers=workers" in owner
    assert not (ROOT / "tools/ci/scripts/run-local-ci.sh").exists()


def test_git_hooks_are_untracked_runtime_projections_over_the_python_owner() -> None:
    tracked = subprocess.run(
        ("git", "ls-files", ".githooks"),
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert tracked == ""
    owner = (ROOT / "src/ethos/adapters/repo/hook_runtime.py").read_text(encoding="utf-8")
    renderer = (ROOT / "src/ethos/repository/hooks.py").read_text(encoding="utf-8")

    assert "def execute_hook(" in owner
    assert "def hook_launcher(" in renderer


def test_windows_virtualenv_executables_are_first_class() -> None:
    smoke = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")

    assert 'directory = "Scripts" if os.name == "nt" else "bin"' in smoke
    assert 'suffix = ".exe" if os.name == "nt" else ""' in smoke
