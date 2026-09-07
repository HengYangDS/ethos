"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import hashlib
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook.binding as hook_binding
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.ethos_cli_runner import run_ethos
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.runtime_scenarios import runtime_build


def _fixture_repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    install_fixture_hook_runtime(repo)
    return repo


def test_hook_binding_follows_the_exact_configured_generation(
    tmp_path: Path,
) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())

    observed = hook_runtime_binding(repo)
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert observed["hooks_path"] == generation.as_posix()
    assert observed["required_gaps"] == []
    assert projected["data"]["hook_runtime"] == observed
    expected = runtime_build("c" * 40, "d" * 40)

    stale = hook_runtime_binding(repo, expected_build=expected)

    assert stale["source_commit"] == observed["source_commit"]
    assert stale["source_tree"] == observed["source_tree"]
    assert (stale["expected_source_commit"], stale["expected_source_tree"]) == (
        "c" * 40,
        "d" * 40,
    )
    assert not stale["current"]
    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["next_action"] == shlex.join(
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


@pytest.mark.parametrize(
    ("launcher", "unarmed_field", "armed_field"),
    [
        ("commit-msg", "commit_message_transport", "push_range_enforcement"),
        ("pre-push", "push_range_enforcement", "commit_message_transport"),
    ],
)
def test_status_blocks_when_declared_commit_policy_transport_is_not_armed(
    tmp_path: Path,
    launcher: str,
    unarmed_field: str,
    armed_field: str,
) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())
    workspace = repo / ".ethos" / "workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "fix: .+"\n'
        'signing_required = true\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )
    (generation / launcher).unlink()

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    capability = projected["data"]["commit_policy_enforcement"]
    gap = f"write_admission_not_armed:{launcher}_launcher_missing"
    assert capability["state"] == "unarmed"
    assert capability["declared"] is True
    assert capability["declaration"] == {
        "subject_pattern": "fix: .+",
        "signing_required": True,
        "signing_format": "ssh",
    }
    assert capability[unarmed_field] == "unarmed"
    assert capability[armed_field] == "armed"
    assert capability["required_gaps"] == [gap]
    assert capability["next_action"] == runtime_command(
        repo, "hook", "install", "--root", repo.as_posix(), "--json"
    )
    assert gap in projected["required_gaps"]
    assert projected["next_action"] == capability["next_action"]


def test_status_projects_declared_commit_policy_as_fully_armed(tmp_path: Path) -> None:
    repo = _fixture_repository(tmp_path)
    workspace = repo / ".ethos" / "workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert projected["data"]["commit_policy_enforcement"] == {
        "state": "armed",
        "declared": True,
        "declaration": {
            "subject_pattern": "fix: .+",
            "signing_required": False,
            "signing_format": "ssh",
        },
        "commit_message_transport": "armed",
        "push_range_enforcement": "armed",
        "required_gaps": [],
        "next_action": "",
    }


def test_status_keeps_the_accepted_runtime_current_while_new_hook_semantics_are_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _fixture_repository(tmp_path)
    workspace = repo / ".ethos" / "workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )
    names = ("pre-commit", "pre-push", "reference-transaction")
    launchers = {name: hook_binding.hook_launcher(name) for name in names}
    digest = hashlib.sha256(
        b"".join(
            name.encode() + b"\0" + content.encode() + b"\0" for name, content in launchers.items()
        )
    ).hexdigest()
    generation = Path(git_common_dir(repo)) / "ethos/hooks" / digest
    generation.mkdir(parents=True)
    for name, content in launchers.items():
        launcher = generation / name
        launcher.write_text(content, encoding="utf-8")
        launcher.chmod(0o755)
    assert git_process(repo, "config", "core.hooksPath", generation.as_posix()).returncode == 0
    monkeypatch.setattr(
        hook_binding,
        "_selected_runtime_hook_contract",
        lambda *_args: {
            "scripts": list(names),
            "launchers": launchers,
            "generation_digest": digest,
            "commit_policy_execution_version": 0,
        },
        raising=False,
    )

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    runtime = projected["data"]["hook_runtime"]
    capability = projected["data"]["commit_policy_enforcement"]
    assert runtime["state"] == "current"
    assert runtime["scripts"] == list(names)
    assert runtime["required_gaps"] == []
    assert capability == {
        "state": "pending_acceptance",
        "declared": True,
        "declaration": {
            "subject_pattern": "fix: .+",
            "signing_required": False,
            "signing_format": "ssh",
        },
        "commit_message_transport": "pending_acceptance",
        "push_range_enforcement": "pending_acceptance",
        "required_gaps": [],
        "next_action": "",
    }
    assert not any(
        gap.startswith("write_admission_not_armed:") for gap in projected["required_gaps"]
    )
    assert "hook install" not in projected["next_action"]


def test_status_unarms_both_commit_policy_transports_for_a_stale_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _fixture_repository(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_build",
        lambda _repo: (runtime_build("c" * 40, "d" * 40), tmp_path / "accepted"),
    )

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    capability = projected["data"]["commit_policy_enforcement"]
    assert capability["state"] == "unarmed"
    assert capability["commit_message_transport"] == "unarmed"
    assert capability["push_range_enforcement"] == "unarmed"
    assert capability["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert projected["required_gaps"].count("write_admission_not_armed:runtime_build_stale") == 1
    assert capability["next_action"] == shlex.join(
        (
            (tmp_path / "accepted/.venv/bin/python").as_posix(),
            "-B",
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


def test_status_fails_closed_for_a_malformed_commit_policy(tmp_path: Path) -> None:
    repo = _fixture_repository(tmp_path)
    workspace = repo / ".ethos" / "workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "["\n'
        'signing_required = false\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    capability = projected["data"]["commit_policy_enforcement"]
    gap = capability["required_gaps"][0]
    assert projected["verdict"] == "block"
    assert capability["state"] == "invalid"
    assert capability["declared"] is None
    assert capability["required_gaps"] == [gap]
    assert gap.startswith("commit_policy_subject_pattern_invalid:")
    assert gap in projected["required_gaps"]
    assert capability["next_action"] == (
        f"repair {(repo / '.ethos/workspace.toml').as_posix()} [commit_policy]"
    )


def test_status_does_not_require_commit_policy_transports_when_policy_is_absent(
    tmp_path: Path,
) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())
    (generation / "commit-msg").unlink()

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert projected["data"]["commit_policy_enforcement"] == {
        "state": "not_declared",
        "declared": False,
        "declaration": {},
        "commit_message_transport": "not_required",
        "push_range_enforcement": "not_required",
        "required_gaps": [],
        "next_action": "",
    }
    assert "write_admission_not_armed:commit-msg_launcher_missing" not in projected["required_gaps"]


def test_hook_binding_reports_non_utf8_launcher_as_drift(
    tmp_path: Path,
) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())
    (generation / "pre-push").write_bytes(b"\xff")

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:pre-push_launcher_drift" in observed["required_gaps"]


def test_hook_runtime_observation_rejects_launcher_drift(
    tmp_path: Path,
) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())
    launcher = generation / "pre-push"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


@pytest.mark.parametrize("configured_form", ["absolute", "relative"])
def test_hook_binding_rejects_a_symlinked_generation(tmp_path: Path, configured_form: str) -> None:
    repo = _fixture_repository(tmp_path)
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    generation = Path(configured.stdout.strip())
    alias = generation.with_name("f" * 64)
    alias.symlink_to(generation, target_is_directory=True)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    configured = (
        alias.relative_to(repo).as_posix() if configured_form == "relative" else alias.as_posix()
    )
    assert git_process(repo, "config", "--worktree", "core.hooksPath", configured).returncode == 0

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


def test_hook_binding_rejects_a_symlinked_generation_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    real = common / "external-hooks"
    root = common / "ethos" / "hooks"
    real.mkdir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        hook_activation.materialize_hook_launchers(root)


def test_hook_binding_rejects_a_configured_path_outside_the_common_generation_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    external = tmp_path / "external-hooks"
    external.mkdir()
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        git_process(repo, "config", "--worktree", "core.hooksPath", external.as_posix()).returncode
        == 0
    )

    observed = hook_runtime_binding(repo)

    assert observed["hooks_path"] == external.as_posix()
    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


def test_hook_binding_primitives_reject_invalid_hook_projections() -> None:
    with pytest.raises(ValueError, match="hook_name_invalid"):
        hook_binding.hook_launcher("post")
    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_binding.hook_generation_digest({"pre-commit": "only"})


def test_hook_binding_reports_unavailable_source_and_generation_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert (
        subprocess.run(
            ("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=False
        ).returncode
        == 0
    )
    common = repo / ".git"
    generations = common / "ethos/hooks"
    generation = generations / ("a" * 64)
    generation.mkdir(parents=True)
    assert (
        subprocess.run(
            ("git", "config", "core.hooksPath", generation.as_posix()), cwd=repo, check=False
        ).returncode
        == 0
    )
    monkeypatch.setattr(hook_binding, "_selected_runtime", lambda *_args: (None, "runtime_current"))
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_build",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_source",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    report = hook_binding.hook_runtime_binding(repo)
    assert (
        "write_admission_not_armed:runtime_expected_source_unavailable" in report["required_gaps"]
    )
