from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest

from tests.support.contract_helpers import git as _git

BOOTSTRAP = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
RUNNER = Path("tools/ci/scripts/run-ethos-lane.sh").resolve()
UV_CONTEXT = """#!/usr/bin/env bash
if [[ "$1" == "sync" ]]; then exit "${UV_SYNC_EXIT:-0}"; fi
printf '%s\n%s\n%s\n' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"
"""
RUNTIME_KEYS = shlex.split(
    "UV_PROJECT_ENVIRONMENT UV_CACHE_DIR ETHOS_UV_CACHE_DIR ETHOS_RUNTIME_ROOT"
)
LOCKED = "run --locked --all-packages --group dev python -m ethos.cli"
OWNER_ARGS = shlex.split(
    "uv run --all-packages --group dev env OWNER_SCRIPT_MODE=test ETHOS_RUNTIME_BOOTSTRAPPED=1"
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "dev")
    return root


def _executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _uv(tmp_path: Path, body: str) -> Path:
    return _executable(tmp_path / "bin/uv", body)


def _env(uv: Path, **values: str) -> dict[str, str]:
    env = {**os.environ, "PATH": f"{uv.parent}:{os.environ['PATH']}"}
    for key in RUNTIME_KEYS:
        env.pop(key, None)
    env.update(values)
    return env


def _run(repo: Path, env: dict[str, str], *command: str, script: Path = BOOTSTRAP) -> list[str]:
    return subprocess.run(
        [script, *(command if script == RUNNER else ("--", *command))],
        cwd=repo,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()


def test_lane_runner_uses_checkout_runtime_and_host_cache(repo: Path, tmp_path: Path) -> None:
    env = _env(_uv(tmp_path, UV_CONTEXT), XDG_CACHE_HOME=str(tmp_path / "host-cache"))

    assert _run(repo, env, "status", "--json", script=RUNNER) == [
        f"{repo}/build/runtime/venv",
        f"{tmp_path}/host-cache/ethos/uv",
        "run --all-packages --group dev ethos status --json",
    ]
    assert not (repo / "build/runtime/venv").exists()
    assert (tmp_path / "host-cache/ethos/uv").is_dir()


@pytest.mark.parametrize(
    ("values", "command", "cache"),
    [
        (
            {"XDG_CACHE_HOME": "host-cache"},
            ("uv", "run", "--no-sync", "--version"),
            "host-cache/ethos/uv",
        ),
        (
            {"UV_CACHE_DIR": "ci-cache/uv"},
            ("uv", "--version"),
            "ci-cache/uv",
        ),
        (
            {"UV_CACHE_DIR": "ci-cache/uv", "ETHOS_UV_CACHE_DIR": "operator-cache/uv"},
            ("uv", "--version"),
            "operator-cache/uv",
        ),
    ],
)
def test_bootstrap_cache_precedence(
    repo: Path,
    tmp_path: Path,
    values: dict[str, str],
    command: tuple[str, ...],
    cache: str,
) -> None:
    env = _env(
        _uv(tmp_path, UV_CONTEXT), **{key: str(tmp_path / value) for key, value in values.items()}
    )
    assert _run(repo, env, *command) == [
        f"{repo}/build/runtime/venv",
        str(tmp_path / cache),
        " ".join(command[1:]),
    ]
    if cache == "operator-cache/uv":
        assert (tmp_path / "operator-cache/uv").is_dir()


@pytest.mark.parametrize(("mode", "tail"), [("direct", ("status", "--json")), ("nested", ())])
def test_missing_checkout_python_uses_locked_fallback(
    repo: Path, tmp_path: Path, mode: str, tail: tuple[str, ...]
) -> None:
    nested = mode == "nested"
    host_cache = tmp_path / "host-cache"
    env = _env(_uv(tmp_path, UV_CONTEXT), XDG_CACHE_HOME=str(host_cache), UV_SYNC_EXIT="1")
    if nested:
        env.update(
            UV_PROJECT_ENVIRONMENT=str(tmp_path / "outer/build/runtime/venv"),
            UV_CACHE_DIR=str(host_cache / "ethos/uv"),
            ETHOS_RUNTIME_ROOT=str(tmp_path / "outer"),
        )
    python = repo.resolve() / "build/runtime/venv/bin/python"
    actual = _run(repo, env, str(python), "-m", "ethos.cli", *tail)

    assert actual[0] == f"{repo.resolve()}/build/runtime/venv"
    assert actual[2] == LOCKED + (f" {' '.join(tail)}" if tail else "")
    assert (
        Path(actual[1]).parent == host_cache / "ethos/uv/nested-bootstrap"
        if nested
        else actual[1] == str(host_cache / "ethos/uv")
    )
    assert not python.exists()


def test_checkout_python_requires_project_metadata_before_sync_repair(
    repo: Path, tmp_path: Path
) -> None:
    capture = tmp_path / "uv-calls.txt"
    uv = _uv(
        tmp_path,
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "$UV_CAPTURE"\nif [[ "$1" == sync ]]; then exit 1; fi\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
    )
    python = _executable(
        repo / "build/runtime/venv/bin/python", "#!/usr/bin/env bash\nprintf 'stale-runtime\\n'\n"
    )
    env = _env(uv, XDG_CACHE_HOME=str(tmp_path / "host-cache"), UV_CAPTURE=str(capture))

    assert _run(repo, env, str(python)) == ["stale-runtime"]
    for name in ("pyproject.toml", "uv.lock"):
        (repo / name).touch()
    actual = _run(repo, env, str(python), "-m", "ethos.cli", "status", "--json")

    assert actual[0] == f"{repo}/build/runtime/venv"
    assert actual[2] == f"{LOCKED} status --json"
    assert capture.read_text().splitlines() == [
        "sync --locked --all-packages --group dev --check",
        actual[2],
    ]


def test_owner_script_detaches_from_uv_sync_lock(repo: Path, tmp_path: Path) -> None:
    uv = _uv(
        tmp_path,
        '#!/usr/bin/env bash\nset -euo pipefail\nprintf \'%s\\n\' "$*" > "$UV_CAPTURE"\n[[ "$1" == run ]]; shift\nwhile [[ "$1" != env ]]; do shift; done; shift\nwhile [[ "$1" == *=* ]]; do export "$1"; shift; done\nexec "$@"\n',
    )
    owner = _executable(
        repo / "tools/ci/scripts/run-owner.sh",
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n\' "$ETHOS_RUNTIME_BOOTSTRAPPED" "$UV_PROJECT_ENVIRONMENT"\n',
    )
    capture = tmp_path / "uv-command.txt"
    env = _env(uv, UV_CAPTURE=str(capture))
    command = (*OWNER_ARGS, str(owner))

    assert _run(repo, env, *command) == ["1", f"{repo.resolve()}/build/runtime/venv"]
    assert capture.read_text() == f"run --no-sync {' '.join(OWNER_ARGS[2:])} {owner}\n"
