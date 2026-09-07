"""Tests for immutable hook binding and commit-policy capability projection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

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

_POLICY = (
    '[commit_policy]\nsubject_pattern = "fix: .+"\n'
    'signing_required = false\nsigning_format = "ssh"\n'
)


def _fixture(tmp_path: Path, *, policy: str | None = None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    install_fixture_hook_runtime(repo)
    if policy is not None:
        path = repo / ".ethos/workspace.toml"
        path.parent.mkdir()
        path.write_text(policy, encoding="utf-8")
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    return repo, Path(configured.stdout.strip())


def _capability(repo: Path) -> tuple[dict[str, object], dict[str, object]]:
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    return projected, projected["data"]["commit_policy_enforcement"]


def test_hook_binding_tracks_exact_generation_and_expected_build(tmp_path: Path) -> None:
    repo, generation = _fixture(tmp_path)

    observed = hook_runtime_binding(repo)
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    stale = hook_runtime_binding(repo, expected_build=runtime_build("c" * 40, "d" * 40))

    assert observed["hooks_path"] == generation.as_posix()
    assert observed["required_gaps"] == []
    assert projected["data"]["hook_runtime"] == observed
    assert (stale["expected_source_commit"], stale["expected_source_tree"]) == (
        "c" * 40,
        "d" * 40,
    )
    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["next_action"].endswith(f"hook install --root {repo} --json")
    assert Path(stale["next_action"].split()[0]).resolve() == Path(sys.executable).resolve()


@pytest.mark.parametrize("launcher", ["commit-msg", "pre-push"])
def test_declared_policy_reports_each_missing_transport(tmp_path: Path, launcher: str) -> None:
    repo, generation = _fixture(tmp_path, policy=_POLICY)
    (generation / launcher).unlink()

    projected, capability = _capability(repo)

    gap = f"write_admission_not_armed:{launcher}_launcher_missing"
    assert capability["state"] == "unarmed"
    assert capability["declaration"]["subject_pattern"] == "fix: .+"
    assert capability["required_gaps"] == [gap]
    assert gap in projected["required_gaps"]
    assert capability["next_action"] == runtime_command(
        repo, "hook", "install", "--root", repo.as_posix(), "--json"
    )


@pytest.mark.parametrize(
    ("policy", "state", "declared", "message", "push"),
    [
        (_POLICY, "armed", "true", "armed", "armed"),
        (None, "not_declared", "false", "not_required", "not_required"),
        (
            (
                '[commit_policy]\nsubject_pattern = "["\n'
                'signing_required = false\nsigning_format = "ssh"\n'
            ),
            "invalid",
            "invalid",
            "unknown",
            "unknown",
        ),
    ],
)
def test_commit_policy_capability_state_matrix(
    tmp_path: Path,
    policy: str | None,
    state: str,
    declared: Literal["true", "false", "invalid"],
    message: str,
    push: str,
) -> None:
    repo, _generation = _fixture(tmp_path, policy=policy)

    projected, capability = _capability(repo)

    assert capability["state"] == state
    expected_declared = {"true": True, "false": False, "invalid": None}[declared]
    assert capability["declared"] is expected_declared
    assert capability["commit_message_transport"] == message
    assert capability["push_range_enforcement"] == push
    if state == "invalid":
        assert projected["verdict"] == "block"
        assert capability["required_gaps"][0].startswith("commit_policy_subject_pattern_invalid:")


def test_candidate_hook_semantics_remain_pending_until_acceptance(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".ethos").mkdir(parents=True)
    (repo / ".ethos/workspace.toml").write_text(_POLICY, encoding="utf-8")
    capability = hook_binding.commit_policy_enforcement(
        repo,
        {"required_gaps": [], "scripts": ["pre-commit", "pre-push", "reference-transaction"]},
    )

    assert capability["state"] == "pending_acceptance"
    assert capability["required_gaps"] == []
    assert capability["next_action"] == ""


def test_stale_runtime_unarms_both_policy_transports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _generation = _fixture(tmp_path, policy=_POLICY)
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_build",
        lambda _repo: (runtime_build("c" * 40, "d" * 40), tmp_path / "accepted"),
    )

    projected, capability = _capability(repo)

    gap = "write_admission_not_armed:runtime_build_stale"
    assert capability["state"] == "unarmed"
    assert capability["commit_message_transport"] == "unarmed"
    assert capability["push_range_enforcement"] == "unarmed"
    assert capability["required_gaps"] == [gap]
    assert projected["required_gaps"].count(gap) == 1
    assert capability["next_action"].startswith((tmp_path / "accepted/.venv/bin/python").as_posix())


@pytest.mark.parametrize("payload", [b"\xff", b"#!/bin/sh\nexit 0\n"])
def test_launcher_drift_fails_closed(tmp_path: Path, payload: bytes) -> None:
    repo, generation = _fixture(tmp_path)
    (generation / "pre-push").write_bytes(payload)

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


@pytest.mark.parametrize("configured_form", ["absolute", "relative"])
def test_symlinked_generation_is_rejected(tmp_path: Path, configured_form: str) -> None:
    repo, generation = _fixture(tmp_path)
    alias = generation.with_name("f" * 64)
    alias.symlink_to(generation, target_is_directory=True)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    configured = (
        alias.relative_to(repo).as_posix() if configured_form == "relative" else alias.as_posix()
    )
    assert git_process(repo, "config", "--worktree", "core.hooksPath", configured).returncode == 0

    assert "write_admission_not_armed:core.hooksPath" in hook_runtime_binding(repo)["required_gaps"]


def test_generation_root_and_external_path_are_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    real = common / "external-hooks"
    root = common / "ethos/hooks"
    real.mkdir()
    root.parent.mkdir(parents=True)
    root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        hook_activation.materialize_hook_launchers(root)
    root.unlink()
    external = tmp_path / "external-hooks"
    external.mkdir()
    assert git_process(repo, "config", "core.hooksPath", external.as_posix()).returncode == 0
    assert "write_admission_not_armed:core.hooksPath" in hook_runtime_binding(repo)["required_gaps"]


def test_binding_primitives_and_unavailable_source_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="hook_name_invalid"):
        hook_binding.hook_launcher("post")
    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_binding.hook_generation_digest({"pre-commit": "only"})

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=True)
    generation = repo / ".git/ethos/hooks" / ("a" * 64)
    generation.mkdir(parents=True)
    subprocess.run(("git", "config", "core.hooksPath", generation.as_posix()), cwd=repo, check=True)
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

    assert (
        "write_admission_not_armed:runtime_expected_source_unavailable"
        in (hook_runtime_binding(repo)["required_gaps"])
    )
