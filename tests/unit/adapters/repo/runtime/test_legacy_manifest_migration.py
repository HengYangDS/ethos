"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import hashlib
import json
import platform
import shlex
import sys
from pathlib import Path

import pytest

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.runtime_scenarios import git_process


def _repair_command(repo: Path) -> str:
    return shlex.join(
        (
            Path(sys.executable).resolve().as_posix(),
            "-I",
            "-m",
            "ethos.cli",
            "hook",
            "install",
            "--root",
            repo.as_posix(),
            "--json",
        )
    )


def _commit_without_hooks(repo: Path, message: str) -> None:
    completed = git_process(
        repo,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    assert completed.returncode == 0, completed.stderr


def _materialize_legacy_runtime(
    common: Path,
    *,
    source_commit: str,
    source_tree: str,
) -> Path:
    digest = "a" * 64
    runtime = common / "ethos/runtime" / digest
    python = runtime / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"incumbent-python")
    python.chmod(0o755)
    entrypoint = runtime / "venv/bin/ethos"
    entrypoint.write_text(f"#!{python}\n", encoding="utf-8")
    entrypoint.chmod(0o755)
    payload = {
        "schema_version": 2,
        "runtime_digest": digest,
        "wheel_sha256": "c" * 64,
        "python_abi": "cpython-test",
        "platform": platform.system().lower(),
        "source_commit": source_commit,
        "source_tree": source_tree,
        "runtime_files": {
            "venv/bin/python": hashlib.sha256(python.read_bytes()).hexdigest(),
            "venv/bin/ethos": hashlib.sha256(entrypoint.read_bytes()).hexdigest(),
        },
    }
    (runtime / "manifest.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (runtime.parent / "CURRENT").write_text(f"{digest}\n", encoding="ascii")
    generation = common / "ethos/hooks" / ("b" * 64)
    generation.mkdir(parents=True)
    for name in HOOK_NAMES:
        launcher = generation / name
        launcher.write_text(
            hook_launcher(name).replace(
                '"$RUNTIME_ROOT/$RUNTIME_DIGEST/python/',
                '"$RUNTIME_ROOT/$RUNTIME_DIGEST/venv/',
            ),
            encoding="utf-8",
        )
        launcher.chmod(0o755)
    return generation


def test_candidate_observation_uses_legacy_source_during_schema_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exact legacy manifest remains read-only migration evidence."""
    repo = tmp_path / "ethos"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n', encoding="utf-8")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\naccepted_branch = "dev"\n', encoding="utf-8"
    )
    (repo / "tracked.txt").write_text("accepted\n", encoding="utf-8")
    assert git_process(repo, "add", ".").returncode == 0
    _commit_without_hooks(repo, "accepted")
    accepted_commit = git_process(repo, "rev-parse", "dev").stdout.strip()
    accepted_tree = git_process(repo, "rev-parse", "dev^{tree}").stdout.strip()
    common = Path(git_common_dir(repo))
    generation = _materialize_legacy_runtime(
        common,
        source_commit=accepted_commit,
        source_tree=accepted_tree,
    )
    assert git_process(repo, "config", "core.hooksPath", generation.as_posix()).returncode == 0
    monkeypatch.setattr(
        "ethos.adapters.repo.hook.binding.expected_runtime_build",
        lambda _repo: (_ for _ in ()).throw(ValueError("accepted VERSION unavailable")),
    )
    observed = hook_runtime_binding(repo)

    assert observed["current"] is False
    assert observed["source_commit"] == ""
    assert observed["source_tree"] == ""
    assert observed["required_gaps"] == [
        "write_admission_not_armed:runtime_schema_migration_required"
    ]
    assert observed["next_action"] == _repair_command(repo)
    assert observed["state"] == "stale"
    assert observed["target_current"] is False

    (repo / "tracked.txt").write_text("accepted-next\n", encoding="utf-8")
    assert git_process(repo, "add", "tracked.txt").returncode == 0
    _commit_without_hooks(repo, "advance accepted")

    stale = hook_runtime_binding(repo)

    assert stale["current"] is False
    assert stale["state"] == "stale"
    assert stale["target_current"] is False
    assert stale["source_commit"] == ""
    assert stale["expected_source_commit"] == git_process(repo, "rev-parse", "dev").stdout.strip()
    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["next_action"] == _repair_command(repo)


@pytest.mark.parametrize(
    ("schema", "extra"),
    [(999, {}), (2, {"unexpected": "field"})],
)
def test_runtime_command_rejects_non_exact_legacy_manifest_schema(
    tmp_path: Path,
    schema: int,
    extra: dict[str, str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    _materialize_legacy_runtime(
        common,
        source_commit="a" * 40,
        source_tree="b" * 40,
    )
    manifest = common / "ethos/runtime" / ("a" * 64) / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["schema_version"] = schema
    payload.update(extra)
    manifest.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_command(repo, "--version")
