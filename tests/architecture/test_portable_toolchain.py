"""Executable portability and orchestration ownership contracts."""

from __future__ import annotations

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


def test_windows_virtualenv_executables_are_first_class() -> None:
    smoke = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")

    assert 'directory = "Scripts" if os.name == "nt" else "bin"' in smoke
    assert 'suffix = ".exe" if os.name == "nt" else ""' in smoke
