"""Package-only runtime activation and identity acceptance."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import sys
from concurrent.futures import wait
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import defer_interruptions
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import require_runtime_selection_scope
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from tools.ci.delivery.acceptance import adopter as adopter_fixture
from tools.ci.delivery.acceptance import brownfield as brownfield_acceptance
from tools.ci.delivery.acceptance import lane as lane_acceptance
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.acceptance.receipt import runtime_activation_evidence

if TYPE_CHECKING:
    from collections.abc import Mapping
    from concurrent.futures import Future

    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity
    from tools.ci.delivery.acceptance.adopter import CommandRunner


@observe_stage("hook_activation")
def activate_from_entrypoint(
    executable: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Activate the first immutable runtime from one installed wheel entrypoint."""
    return _activate((executable.as_posix(),), repo, environment=environment)


@observe_stage("repository_activation")
def activate_from_runtime(
    python: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
    installed_runtime: Path | None = None,
) -> dict[str, object]:
    """Activate exact supplied bytes without implying a predecessor upgrade."""
    return _activate(
        (python.as_posix(), "-B", "-I", "-m", "ethos.cli"),
        repo,
        environment=environment,
        installed_runtime=installed_runtime,
    )


def _activate(
    prefix: tuple[str, ...],
    repo: Path,
    *,
    environment: Mapping[str, str],
    installed_runtime: Path | None = None,
) -> dict[str, object]:
    selection = ("--runtime", str(installed_runtime)) if installed_runtime is not None else ()
    command = (
        *prefix,
        "hook",
        "install",
        *selection,
        "--root",
        repo.as_posix(),
        "--json",
    )
    returncode, payload, diagnostic = invoke(repo, command, environment=environment)
    if returncode or payload.get("verdict") != "pass":
        message = f"package_runtime_activation_failed:{diagnostic}"
        raise RuntimeError(message)
    data = payload.get("data")
    if not isinstance(data, dict):
        message = "package_runtime_activation_result_missing"
        raise TypeError(message)
    return data


def require_manifest(
    report: Mapping[str, object],
    repo: Path,
    *,
    build: BuildIdentity,
    wheel_sha256: str,
) -> Path:
    """Require one selected runtime manifest to match its wheel and source identity."""
    try:
        manifest_path = Path(str(report["runtime_manifest_path"]))
        runtime_digest = str(report["runtime_digest"])
        python = Path(str(report["python"]))
    except KeyError as error:
        message = "package_runtime_manifest_missing"
        raise RuntimeError(message) from error
    if not manifest_path.is_file():
        message = "package_runtime_manifest_missing"
        raise RuntimeError(message)
    try:
        selected = current_runtime(Path(git_common_dir(repo)), expected_build=build)
    except (OSError, TypeError, ValueError) as error:
        message = "package_runtime_identity_mismatch"
        raise RuntimeError(message) from error
    expected_report = {
        **build._asdict(),
        "wheel_sha256": wheel_sha256,
        "runtime_digest": selected.digest,
    }
    if (
        selected.manifest != manifest_path
        or selected.digest != runtime_digest
        or selected.python != python
        or selected.wheel_sha256 != wheel_sha256
        or any(report.get(key) != value for key, value in expected_report.items())
    ):
        message = "package_runtime_identity_mismatch"
        raise RuntimeError(message)
    return selected.python


@observe_stage("development_dependencies")
def require_production_dependencies(
    python: Path, *, environment: Mapping[str, str]
) -> dict[str, object]:
    """Exercise production-only staged and shared native formatters in isolation."""
    probe = """
import importlib.util
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.repo.hook.admission import _check_staged_python_format

assert importlib.util.find_spec("pytest") is None
with TemporaryDirectory(prefix="ethos-installed-format-") as temporary:
    root = Path(temporary)
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    policy = root / ".config/checks/ruff/ruff.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text("line-length = 100\\n")
    source = root / "change.py"
    for staged, working, rejected in (("VALUE=1\\n", "VALUE = 1\\n", True),
                                      ("VALUE = 1\\n", "VALUE=1\\n", False)):
        source.write_text(staged)
        subprocess.run(["git", "-C", str(root), "add", "change.py"], check=True)
        source.write_text(working)
        try:
            _check_staged_python_format(root, ("change.py",), configuration=root)
        except RuntimeError as error:
            assert rejected and "pre_commit_python_format_failed" in str(error), str(error)
        else:
            assert not rejected, "installed formatter skipped invalid staged bytes"
        assert source.read_text() == working
        observed = subprocess.check_output(["git", "-C", str(root), "show", ":change.py"])
        assert observed == staged.encode()
    cases = (
        ("native.py", "ruff", b"value=1\\n"),
        ("docs/with space.md", "prettier", b"# Native\\n\\ntext   \\n"),
        ("native.json", "prettier", b'{"value":true}\\n'),
        ("native.yaml", "prettier", b"value: [ one,two ]\\n"),
        ("native.mjs", "prettier", b"export const value={valid:true};\\n"),
        ("native.toml", "taplo", b"value=[1,2]\\n"),
        ("native.sh", "shfmt", b"if true;then echo native;fi\\n"),
        ("native.svg", "svgo", (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
            b'<path d="M0 0h1v1H0z"/></svg>\\n'
        )),
    )
    for relative, _owner, content in cases:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    subprocess.run(["git", "-C", str(root), "add", "--", *(item[0] for item in cases)],
                   check=True)
    index = subprocess.check_output(["git", "-C", str(root), "write-tree"])
    for relative, owner, content in cases:
        path = root / relative
        mode = path.stat().st_mode
        rendered, ignored = render_source_content(root, relative, owner, content)
        assert not ignored and rendered != content and rendered.endswith(b"\\n"), relative
        assert render_source_content(root, relative, owner, rendered) == (rendered, False)
        assert path.read_bytes() == content and path.stat().st_mode == mode, relative
    assert subprocess.check_output(["git", "-C", str(root), "write-tree"]) == index
    ignore = root / ".config/checks/prettier/prettierignore"
    ignore.parent.mkdir(parents=True, exist_ok=True)
    ignore.write_text("../../../docs/ignored.md\\n")
    preserved = b"# Captured\\n\\ntext   \\n"
    assert render_source_content(root, "docs/ignored.md", "prettier", preserved) == (
        preserved, True
    )
"""
    completed = run_command(
        python.parent,
        (python.as_posix(), "-B", "-I", "-c", probe),
        env=environment,
        inherit_environment=False,
        timeout=120,
    )
    if completed.returncode:
        message = f"package_runtime_dependency_acceptance_failed:{completed.stderr.strip()}"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "excluded": ["pytest"],
        "staged_format": "passed",
        "source_format": "passed",
        "formatters": ["ruff", "prettier", "taplo", "shfmt", "svgo"],
    }


@observe_stage("immutable_identity")
def require_version_identity(
    python: Path,
    repository: Path,
    *,
    build: BuildIdentity,
    wheel_sha256: str,
    runtime_digest: str,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Require the public version surface to expose the complete immutable identity."""
    prefix = (
        (python.as_posix(), "-B", "-I", "-m", "ethos.cli")
        if os.name == "nt"
        else (python.with_name("ethos").as_posix(),)
    )
    command = (*prefix, "--version", "--json", "--root", repository.as_posix())
    returncode, payload, diagnostic = invoke(repository, command, environment=environment)
    data = payload.get("data")
    identity = data.get("identity") if isinstance(data, dict) else {}
    expected = {
        "schema_version": 2,
        **build._asdict(),
        "wheel_sha256": wheel_sha256,
        "runtime_digest": runtime_digest,
    }
    if returncode or identity != expected:
        message = f"package_runtime_version_identity_mismatch:{diagnostic}"
        raise RuntimeError(message)
    return {"state": "passed", "identity": expected}


@observe_stage("relocation_repair")
def prove_repair(
    python: Path,
    repo: Path,
    *,
    hooks_path: Path,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Prove the relocated runtime detects and repairs one stale hook generation."""
    prefix = (python.as_posix(), "-B", "-I", "-m", "ethos.cli")
    status = (*prefix, "status", "--root", repo.as_posix(), "--json")
    returncode, payload, diagnostic = invoke(repo, status, environment=environment)
    data = payload.get("data")
    hook_runtime = data.get("hook_runtime") if isinstance(data, dict) else {}
    if returncode or not isinstance(hook_runtime, dict) or hook_runtime.get("current") is not True:
        message = f"package_runtime_status_failed:{diagnostic}"
        raise RuntimeError(message)
    (hooks_path / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
    _returncode, stale, _stderr = invoke(repo, status, environment=environment)
    stale_data = stale.get("data")
    stale_runtime = stale_data.get("hook_runtime") if isinstance(stale_data, dict) else {}
    repair = str(stale_runtime.get("next_action") or "") if isinstance(stale_runtime, dict) else ""
    arguments = tuple(shlex.split(repair))
    if arguments[:5] != prefix or not arguments:
        message = "package_runtime_repair_continuation_invalid"
        raise RuntimeError(message)
    repaired_code, repaired, repaired_diagnostic = invoke(repo, arguments, environment=environment)
    if repaired_code or repaired.get("verdict") != "pass":
        message = f"package_runtime_repair_failed:{repaired_diagnostic}"
        raise RuntimeError(message)
    proof = (*prefix, "prove", "--root", repo.as_posix(), "--json")
    _proof_code, proof_payload, _proof_stderr = invoke(repo, proof, environment=environment)
    if proof_payload.get("command") != "prove":
        message = "package_runtime_proof_surface_invalid"
        raise RuntimeError(message)
    return {"state": "passed", "repair_command": repair}


def require_upgrade_predecessor(
    path: Path, *, build: BuildIdentity, common: Path
) -> SelectedRuntime:
    """Validate immutable prior bytes and destination scope before acceptance work."""
    selected = require_selected_runtime(path)
    if selected.build == build:
        message = "package_upgrade_predecessor_not_distinct"
        raise ValueError(message)
    require_runtime_selection_scope(common, selected)
    return selected


@observe_stage("retained_state_upgrade")
def prove_retained_upgrade(
    successor: SelectedRuntime,
    repository: Path,
    *,
    predecessor: SelectedRuntime,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Upgrade and roll back a real predecessor with nonempty retained state."""
    common = Path(git_common_dir(repository))
    previous = require_upgrade_predecessor(predecessor.root, build=successor.build, common=common)
    predecessor_report = activate_from_runtime(
        successor.python,
        repository,
        environment=environment,
        installed_runtime=previous.root,
    )
    require_manifest(
        predecessor_report,
        repository,
        build=previous.build,
        wheel_sha256=previous.wheel_sha256,
    )
    # The installed activation already preserves the displaced coordinator in its own store.
    coordinator = predecessor_report.get("rollback_supply")
    if not isinstance(coordinator, dict) or coordinator.get("runtime_digest") != successor.digest:
        message = "package_upgrade_coordinator_supply_missing"
        raise RuntimeError(message)
    successor = require_selected_runtime(
        Path(str(coordinator["runtime"])), expected_build=successor.build
    )
    brownfield_acceptance.seed_retained_state(
        repository, python=previous.python, environment=environment
    )
    before = brownfield_acceptance.retained_repository(repository)
    selector = common / "ethos/runtime/CURRENT"
    original_selector = selector.read_bytes()
    hooks = Path(str(predecessor_report["hooks_path"]))
    original_hooks = runtime_file_inventory(hooks)
    original_hook_config = run_git(
        repository, "config", "--local", "--get", "core.hooksPath"
    ).stdout
    upgraded = activate_from_runtime(
        successor.python,
        repository,
        environment=environment,
        installed_runtime=successor.root,
    )
    require_manifest(
        upgraded, repository, build=successor.build, wheel_sha256=successor.wheel_sha256
    )
    if brownfield_acceptance.retained_repository(repository) != before:
        message = "package_upgrade_retained_state_changed"
        raise RuntimeError(message)
    supply = upgraded.get("rollback_supply")
    if not isinstance(supply, dict) or supply.get("runtime_digest") != previous.digest:
        message = "package_upgrade_rollback_supply_missing"
        raise RuntimeError(message)
    rollback = require_selected_runtime(Path(str(supply["runtime"])), expected_build=previous.build)
    restored = activate_from_runtime(
        successor.python,
        repository,
        environment=environment,
        installed_runtime=rollback.root,
    )
    require_manifest(restored, repository, build=previous.build, wheel_sha256=previous.wheel_sha256)
    if (
        brownfield_acceptance.retained_repository(repository) != before
        or selector.read_bytes() != original_selector
        or run_git(repository, "config", "--local", "--get", "core.hooksPath").stdout
        != original_hook_config
        or Path(str(restored["hooks_path"])) != hooks
        or runtime_file_inventory(hooks) != original_hooks
    ):
        message = "package_upgrade_rollback_prestate_changed"
        raise RuntimeError(message)
    reactivated = activate_from_runtime(
        successor.python,
        repository,
        environment=environment,
        installed_runtime=successor.root,
    )
    require_manifest(
        reactivated,
        repository,
        build=successor.build,
        wheel_sha256=successor.wheel_sha256,
    )
    if brownfield_acceptance.retained_repository(repository) != before:
        message = "package_upgrade_reactivation_retained_state_changed"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "predecessor": runtime_activation_evidence(predecessor_report),
        "successor": runtime_activation_evidence(upgraded),
        "rollback": runtime_activation_evidence(restored),
        "reactivated": runtime_activation_evidence(reactivated),
        "preservation": {
            "head": before.head,
            "files_sha256": dict(before.files_sha256),
            "file_modes": dict(before.file_modes),
            "index_sha256": before.index_sha256,
            "worktree_registration_sha256": hashlib.sha256(
                before.worktree_registration.encode()
            ).hexdigest(),
            "linked_worktrees": {
                path: {
                    "head": retained.head,
                    "index_sha256": retained.index_sha256,
                    "files_sha256": dict(retained.files_sha256),
                    "file_modes": dict(retained.file_modes),
                }
                for path, retained in before.linked_worktrees
            },
            "index_preserved": True,
            "file_modes_preserved": True,
            "linked_worktrees_preserved": True,
            "lease_count": len(before.leases),
            "configuration_preserved": True,
            "state_schema_preserved": True,
            "lease_rows_preserved": True,
            "user_files_preserved": True,
        },
        "interruption_recovery": "not_qualified",
        "live_consumer_safe_uninstall": "not_qualified",
    }


@observe_stage("runtime_lifecycle")
def observe_lifecycle(
    *,
    installed_ethos: Path,
    bootstrap_environment: Path,
    bootstrap_repository: Path,
    repository: Path,
    build: BuildIdentity,
    wheel_sha256: str,
    environment: Mapping[str, str],
    run: CommandRunner,
    bootstrap_users: tuple[Future[dict[str, object]], ...] = (),
) -> dict[str, Mapping[str, object]]:
    """Execute and post-observe one complete package-only runtime lifecycle.

    Work that still runs the installed console finishes before the bootstrap
    environment is removed, including when activation fails.
    """
    adopter_fixture.materialize_bootstrap_repository(bootstrap_repository, run=run)
    candidate = adopter_fixture.prepare_acceptance_topology(repository, run=run)
    try:
        bootstrap_report = activate_from_entrypoint(
            installed_ethos,
            bootstrap_repository,
            environment=environment,
        )
        bootstrap_python = require_manifest(
            bootstrap_report,
            bootstrap_repository,
            build=build,
            wheel_sha256=wheel_sha256,
        )
        successor_report = activate_from_runtime(
            bootstrap_python,
            repository,
            environment=environment,
        )
        runtime_python = require_manifest(
            successor_report,
            repository,
            build=build,
            wheel_sha256=wheel_sha256,
        )
    finally:
        with defer_interruptions(), ExitStack() as cleanup:
            cleanup.callback(remove_generated_tree, bootstrap_repository)
            if bootstrap_environment.exists():
                cleanup.callback(shutil.rmtree, bootstrap_environment)
            wait(bootstrap_users)
            with observe_stage("bootstrap_cleanup"):
                cleanup.__exit__(*sys.exc_info())

    runtime_digest = str(successor_report["runtime_digest"])
    hooks_path = Path(str(successor_report["hooks_path"]))
    return {
        "hook_activation": runtime_activation_evidence(bootstrap_report),
        "repository_activation": {
            **runtime_activation_evidence(successor_report),
            "candidate_worktree": candidate.as_posix(),
        },
        "development_dependencies": require_production_dependencies(
            runtime_python, environment=environment
        ),
        "immutable_identity": require_version_identity(
            runtime_python,
            repository,
            build=build,
            wheel_sha256=wheel_sha256,
            runtime_digest=runtime_digest,
            environment=environment,
        ),
        "relocation_repair": prove_repair(
            runtime_python,
            repository,
            hooks_path=hooks_path,
            environment=environment,
        ),
        "signature_repair": lane_acceptance.prove_signature_repair(
            runtime_python,
            repository,
            environment=environment,
            historical=True,
        ),
        **lane_acceptance.prove_lifecycle(
            runtime_python,
            repository,
            environment=environment,
        ),
    }
