from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.support.contract_helpers import git as _git


def _init_repo(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-b", "dev")
    _git(root, "config", "user.name", "Test User")
    _git(root, "config", "user.email", "test@example.com")


def _fake_uv(tmp_path: Path, body: str) -> Path:
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(body, encoding="utf-8")
    fake_uv.chmod(0o755)
    return fake_uv


def _environment(fake_uv: Path, **values: str | None) -> dict[str, str]:
    environment = {**os.environ, "PATH": f"{fake_uv.parent}:{os.environ['PATH']}"}
    for key, value in values.items():
        if value is None:
            environment.pop(key, None)
        else:
            environment[key] = value
    return environment


def _run_bootstrap(
    repo: Path, environment: dict[str, str], *command: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            Path("tools/ci/scripts/with-python-runtime.sh").resolve().as_posix(),
            "--",
            *command,
        ],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )


def test_source_bound_uv_runner_uses_checkout_environment_and_host_cache(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    runner = Path("tools/ci/scripts/run-ethos-lane.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["XDG_CACHE_HOME"] = (tmp_path / "host-cache").as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("ETHOS_RUNTIME_ROOT", None)
    environment["VIRTUAL_ENV"] = (tmp_path / "foreign" / ".venv").as_posix()

    completed = subprocess.run(
        [runner.as_posix(), "status", "--json"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        f"{repo}/build/runtime/venv",
        f"{tmp_path}/host-cache/ethos/uv",
        "run --all-packages --group dev ethos status --json",
    ]
    assert "VIRTUAL_ENV" not in completed.stderr
    assert not (repo / "build/runtime/venv").exists()
    assert (tmp_path / "host-cache/ethos/uv").is_dir()


_UV_CONTEXT = (
    "#!/usr/bin/env bash\n"
    'if [[ "$1" == "sync" ]]; then exit "${UV_SYNC_EXIT:-0}"; fi\n'
    'printf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n'
)


@pytest.mark.parametrize(
    ("body", "values", "command", "expected"),
    [
        (
            _UV_CONTEXT,
            {
                "XDG_CACHE_HOME": "host-cache",
                "UV_PROJECT_ENVIRONMENT": None,
                "UV_CACHE_DIR": None,
                "ETHOS_UV_CACHE_DIR": None,
            },
            ("uv", "run", "--no-sync", "--version"),
            ("environment", "host-cache/ethos/uv", "run --no-sync --version"),
        ),
        (
            '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR"\n',
            {"UV_CACHE_DIR": "ci-cache/uv", "ETHOS_UV_CACHE_DIR": None},
            ("uv", "--version"),
            ("environment", "ci-cache/uv"),
        ),
        (
            "#!/usr/bin/env bash\nprintf '%s\\n' \"$UV_CACHE_DIR\"\n",
            {"UV_CACHE_DIR": "ci-cache/uv", "ETHOS_UV_CACHE_DIR": "operator-cache/uv"},
            ("uv", "--version"),
            ("operator-cache/uv",),
        ),
    ],
)
def test_semantic_runtime_bootstrap_selects_cache(
    tmp_path: Path,
    body: str,
    values: dict[str, str | None],
    command: tuple[str, ...],
    expected: tuple[str, ...],
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = _fake_uv(tmp_path, body)
    actual = _run_bootstrap(
        repo,
        _environment(
            fake_uv,
            **{
                key: (tmp_path / value).as_posix() if value is not None else None
                for key, value in values.items()
            },
        ),
        *command,
    ).stdout.splitlines()

    assert actual == [
        f"{repo}/build/runtime/venv"
        if value == "environment"
        else f"{tmp_path}/{value}"
        if "/" in value
        else value
        for value in expected
    ]
    if "operator-cache/uv" in expected:
        assert (tmp_path / "operator-cache/uv").is_dir()


@pytest.mark.parametrize(
    ("values", "expected_cache", "expected_command"),
    [
        (
            {
                "XDG_CACHE_HOME": "host-cache",
                "UV_PROJECT_ENVIRONMENT": None,
                "UV_CACHE_DIR": None,
                "ETHOS_UV_CACHE_DIR": None,
                "ETHOS_RUNTIME_ROOT": None,
            },
            "host-cache/ethos/uv",
            ("status", "--json"),
        ),
        (
            {
                "UV_PROJECT_ENVIRONMENT": "outer/build/runtime/venv",
                "UV_CACHE_DIR": "host-cache/ethos/uv",
                "ETHOS_RUNTIME_ROOT": "outer",
                "ETHOS_UV_CACHE_DIR": None,
            },
            "nested-bootstrap",
            (),
        ),
    ],
)
def test_semantic_runtime_bootstrap_rewrites_checkout_python(
    tmp_path: Path,
    values: dict[str, str | None],
    expected_cache: str,
    expected_command: tuple[str, ...],
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = _fake_uv(tmp_path, _UV_CONTEXT)
    checkout_python = repo.resolve() / "build/runtime/venv/bin/python"
    environment = _environment(
        fake_uv,
        **{
            key: (tmp_path / value).as_posix() if value is not None else None
            for key, value in values.items()
        },
    )
    environment["UV_SYNC_EXIT"] = "1"
    actual = _run_bootstrap(
        repo,
        environment,
        checkout_python.as_posix(),
        "-m",
        "ethos.cli",
        *expected_command,
    ).stdout.splitlines()

    assert actual[0] == f"{repo.resolve()}/build/runtime/venv"
    assert actual[2] == "run --locked --all-packages --group dev python -m ethos.cli" + (
        f" {' '.join(expected_command)}" if expected_command else ""
    )
    if expected_cache == "nested-bootstrap":
        assert Path(actual[1]).parent == tmp_path / "host-cache/ethos/uv/nested-bootstrap"
    else:
        assert actual[1] == f"{tmp_path}/{expected_cache}"
    assert not checkout_python.exists()


def test_semantic_runtime_bootstrap_repairs_a_stale_checkout_environment(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    capture = tmp_path / "uv-calls.txt"
    fake_uv = _fake_uv(
        tmp_path,
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$UV_CAPTURE"\n'
        'if [[ "$1" == "sync" ]]; then exit 1; fi\n'
        'printf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
    )
    checkout_python = repo / "build/runtime/venv/bin/python"
    checkout_python.parent.mkdir(parents=True)
    checkout_python.write_text("#!/usr/bin/env bash\nprintf 'stale-runtime\\n'\n", encoding="utf-8")
    checkout_python.chmod(0o755)
    environment = _environment(fake_uv, XDG_CACHE_HOME="host-cache")
    environment["UV_CAPTURE"] = capture.as_posix()

    actual = _run_bootstrap(
        repo,
        environment,
        checkout_python.as_posix(),
        "-m",
        "ethos.cli",
        "status",
        "--json",
    ).stdout.splitlines()

    assert actual[0] == f"{repo}/build/runtime/venv"
    assert actual[2] == "run --locked --all-packages --group dev python -m ethos.cli status --json"
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "sync --locked --all-packages --group dev --check",
        "run --locked --all-packages --group dev python -m ethos.cli status --json",
    ]


def test_semantic_runtime_bootstrap_detaches_owner_script_from_uv_sync_lock(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "%s\\n" "$*" > "$UV_CAPTURE"\n'
        '[[ "$1" == "run" ]]\n'
        "shift\n"
        'while [[ "$1" != "env" ]]; do shift; done\n'
        "shift\n"
        'while [[ "$1" == *=* ]]; do export "$1"; shift; done\n'
        'exec "$@"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    owner_script = repo / "tools" / "ci" / "scripts" / "run-owner.sh"
    owner_script.parent.mkdir(parents=True)
    owner_script.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n%s\\n" "$ETHOS_RUNTIME_BOOTSTRAPPED" "$UV_PROJECT_ENVIRONMENT"\n',
        encoding="utf-8",
    )
    owner_script.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    capture = tmp_path / "uv-command.txt"
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["UV_CAPTURE"] = capture.as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("ETHOS_RUNTIME_ROOT", None)

    completed = subprocess.run(
        [
            bootstrap.as_posix(),
            "--",
            "uv",
            "run",
            "--all-packages",
            "--group",
            "dev",
            "env",
            "OWNER_SCRIPT_MODE=test",
            "ETHOS_RUNTIME_BOOTSTRAPPED=1",
            owner_script.as_posix(),
        ],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        "1",
        f"{repo.resolve()}/build/runtime/venv",
    ]
    assert capture.read_text(encoding="utf-8") == (
        "run --no-sync --all-packages --group dev env "
        f"OWNER_SCRIPT_MODE=test ETHOS_RUNTIME_BOOTSTRAPPED=1 {owner_script}\n"
    )
