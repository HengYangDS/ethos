"""Retained runtime upgrade preserves independent native repository state."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

import tools.ci.delivery.acceptance.brownfield as brownfield_acceptance
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import runtime_build


def _stage_working_bytes(repository: Path) -> Path:
    indexed = repository / "index-sensitive.txt"
    indexed.write_bytes(b"staged bytes\n")
    run_git(repository, "add", "--", indexed.name)
    indexed.write_bytes(b"working bytes\n")
    return indexed


def _change_staged_bytes(indexed: Path) -> None:
    repository = indexed.parent
    state = run_git(repository, "status", "--porcelain=v1", "-z").stdout
    indexed.write_bytes(b"different staged bytes\n")
    run_git(repository, "add", "--", indexed.name)
    indexed.write_bytes(b"working bytes\n")
    assert run_git(repository, "status", "--porcelain=v1", "-z").stdout == state


@pytest.mark.parametrize(
    "drift",
    [
        "none",
        "hook-config",
        "hook-bytes",
        pytest.param(
            "hook-mode", marks=pytest.mark.skipif(os.name == "nt", reason="POSIX executable mode")
        ),
        "user-file",
        "index",
        "selector",
    ],
)
def test_retained_upgrade_requires_exact_rollback_and_reactivation(monkeypatch, tmp_path, drift):
    """Real Git selection and Lease bytes distinguish rollback from a successful command."""
    repository = init_git_repo(tmp_path / "adopter")
    indexed = _stage_working_bytes(repository)
    common = Path(git_common_dir(repository))
    selector = common / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    prior, successor = (
        require_selected_runtime(
            fixture_runtime_generation(
                tmp_path / name,
                name,
                repository_private=False,
                build=runtime_build(digit * 40, digit * 40),
            )
        )
        for name, digit in (("prior", "a"), ("next", "b"))
    )
    hooks = {
        selected.digest: common / "ethos/hooks" / selected.digest for selected in (prior, successor)
    }
    for directory in hooks.values():
        directory.mkdir(parents=True)
        hook = directory / "pre-push"
        hook.write_bytes(b"#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
    activations = []
    prior_hook = hooks[prior.digest] / "pre-push"
    mutations = {
        "hook-config": lambda: run_git(
            repository, "config", "core.hooksPath", str(hooks[successor.digest])
        ),
        "hook-bytes": lambda: prior_hook.write_bytes(b"changed"),
        "hook-mode": lambda: prior_hook.chmod(0o644),
        "user-file": lambda: (repository / "retained-user-data.txt").write_bytes(b"changed"),
        "index": lambda: _change_staged_bytes(indexed),
        "selector": lambda: selector.write_bytes(runtime_selection_bytes(common, successor.root)),
    }

    def activate(_python, _repository, *, installed_runtime, **_kwargs):
        selected = prior if installed_runtime == prior.root else successor
        activations.append(selected.digest)
        hook_path = hooks[selected.digest]
        selector.write_bytes(runtime_selection_bytes(common, selected.root))
        run_git(repository, "config", "core.hooksPath", str(hook_path))
        if activations.count(prior.digest) == 2 and drift != "none":
            mutations[drift]()
        return {
            **selected.build._asdict(),
            "runtime_manifest_path": str(selected.manifest),
            "runtime_digest": selected.digest,
            "python": str(selected.python),
            "wheel_sha256": selected.wheel_sha256,
            "hooks_path": str(hook_path),
            "rollback_supply": {"runtime_digest": prior.digest, "runtime": str(prior.root)},
        }

    monkeypatch.setattr(runtime_acceptance, "activate_from_runtime", activate)
    if drift == "none":
        result = runtime_acceptance.prove_retained_upgrade(
            successor, repository, predecessor=prior, environment={}
        )
        assert activations == [
            successor.digest,
            prior.digest,
            successor.digest,
            prior.digest,
            successor.digest,
        ]
        preservation = result["preservation"]
        assert isinstance(preservation, dict)
        assert preservation["lease_count"] == 1
        assert (
            result["interruption_recovery"]
            == result["live_consumer_safe_uninstall"]
            == "not_qualified"
        )
    else:
        reason = (
            "package_runtime_identity_mismatch"
            if drift == "selector"
            else "package_upgrade_rollback_prestate_changed"
        )
        with pytest.raises(RuntimeError, match=reason):
            runtime_acceptance.prove_retained_upgrade(
                successor, repository, predecessor=prior, environment={}
            )
        assert activations == [successor.digest, prior.digest, successor.digest, prior.digest]


def test_retained_upgrade_survives_reclaimed_private_successor(monkeypatch, tmp_path):
    repository = init_git_repo(tmp_path / "adopter")
    common = Path(git_common_dir(repository))
    selector = common / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    prior = require_selected_runtime(fixture_runtime_generation(tmp_path / "prior", "prior"))
    successor = require_selected_runtime(
        fixture_runtime_generation(
            selector.parent / "next", "next", build=runtime_build("b" * 40, "b" * 40)
        )
    )
    pinned_root = tmp_path / "installed" / "runtime" / successor.digest

    def activate(python, _repository, *, installed_runtime, **_kwargs):
        if not python.is_file():
            raise FileNotFoundError(python)
        if installed_runtime == successor.root:
            shutil.copytree(successor.root, pinned_root)
            installed_runtime = pinned_root
        selected = require_selected_runtime(installed_runtime)
        hooks = common / "ethos/hooks" / selected.digest
        hooks.mkdir(parents=True, exist_ok=True)
        selector.write_bytes(runtime_selection_bytes(common, selected.root))
        run_git(repository, "config", "core.hooksPath", str(hooks))
        if selected.digest == prior.digest:
            runtime_acceptance.remove_generated_tree(successor.root)
        return {
            **selected.build._asdict(),
            "runtime_manifest_path": str(selected.manifest),
            "runtime_digest": selected.digest,
            "python": str(selected.python),
            "wheel_sha256": selected.wheel_sha256,
            "hooks_path": str(hooks),
            "rollback_supply": {"runtime_digest": prior.digest, "runtime": str(prior.root)},
        }

    monkeypatch.setattr(runtime_acceptance, "activate_from_runtime", activate)
    result = runtime_acceptance.prove_retained_upgrade(
        successor, repository, predecessor=prior, environment={}
    )
    assert result["state"] == "passed"
    assert not successor.root.exists()
    assert require_selected_runtime(pinned_root).python.is_file()
    assert selector.read_bytes() == runtime_selection_bytes(common, pinned_root)


@pytest.mark.parametrize("drift", ["bytes", "mode"])
def test_snapshot_distinguishes_staged_only_change(tmp_path: Path, drift: str) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    indexed = _stage_working_bytes(repository)
    run_git(repository, "config", "core.filemode", "false")
    before = brownfield_acceptance.retained_repository(repository)
    state = run_git(repository, "status", "--porcelain=v1", "-z").stdout
    if drift == "bytes":
        _change_staged_bytes(indexed)
    else:
        object_id = run_git(repository, "ls-files", "--stage", "--", indexed.name).stdout.split()[1]
        run_git(repository, "update-index", "--cacheinfo", f"100755,{object_id},{indexed.name}")
    assert run_git(repository, "status", "--porcelain=v1", "-z").stdout == state
    assert brownfield_acceptance.retained_repository(repository) != before


def test_snapshot_observes_deleted_tracked_file(tmp_path: Path) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    before = brownfield_acceptance.retained_repository(repository)
    (repository / "README.md").unlink()
    deleted = brownfield_acceptance.retained_repository(repository)
    assert deleted != before
    assert ("README.md", None) in deleted.files_sha256


@pytest.mark.skipif(os.name == "nt", reason="POSIX symbolic links")
def test_snapshot_preserves_raw_symlink_target(tmp_path: Path) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    link = repository / "retained-link"
    link.symlink_to("domain//target")
    before = brownfield_acceptance.retained_repository(repository)
    assert dict(before.files_sha256)[link.name] == hashlib.sha256(b"domain//target").hexdigest()
    link.unlink()
    link.symlink_to("domain/target")
    assert brownfield_acceptance.retained_repository(repository) != before


@pytest.mark.skipif(os.name == "nt", reason="POSIX file permissions")
def test_snapshot_distinguishes_user_file_permission_change(tmp_path: Path) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    authored = repository / "retained-user-data.txt"
    authored.chmod(0o644)
    before = brownfield_acceptance.retained_repository(repository)
    authored.chmod(0o600)
    assert brownfield_acceptance.retained_repository(repository) != before


def test_snapshot_observes_linked_worktree_content(tmp_path: Path) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    linked = tmp_path / "linked-peer"
    run_git(repository, "worktree", "add", "-b", "work/retained-peer", str(linked), "HEAD")
    before = brownfield_acceptance.retained_repository(repository)
    (linked / "README.md").write_bytes(b"independent user content\n")
    assert brownfield_acceptance.retained_repository(repository) != before


def test_retained_fixture_has_one_real_leased_dirty_lane(tmp_path: Path) -> None:
    repository = init_git_repo(tmp_path / "adopter")
    brownfield_acceptance.seed_retained_state(repository)
    registration = run_git(repository, "worktree", "list", "--porcelain").stdout
    assert "branch refs/heads/work/retained-upgrade-fixture" in registration
    linked = repository.parent / f"{repository.name}-work-retained-upgrade-fixture"
    state = run_git(linked, "status", "--porcelain=v1", "--untracked-files=all").stdout
    assert "AM retained-index.txt" in state
    assert " D README.md" in state
    assert "?? retained-untracked.txt" in state
    retained = brownfield_acceptance.retained_repository(repository)
    assert len(retained.leases) == 1
    assert retained.leases[0].lane_ref == "work/retained-upgrade-fixture"
