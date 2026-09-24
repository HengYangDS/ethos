"""Package-only runtime activation and identity acceptance."""

from __future__ import annotations

import os
import shlex
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.repository.release.identity import BuildIdentity


def activate_from_entrypoint(
    executable: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Activate the first immutable runtime from one installed wheel entrypoint."""
    return _activate((executable.as_posix(),), repo, environment=environment)


def activate_from_runtime(
    python: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Activate a successor repository runtime from an immutable package runtime."""
    return _activate(
        (python.as_posix(), "-B", "-I", "-m", "ethos.cli"),
        repo,
        environment=environment,
    )


def _activate(
    prefix: tuple[str, ...],
    repo: Path,
    *,
    environment: Mapping[str, str],
    installed_runtime: Path | None = None,
) -> dict[str, object]:
    selection = ("--runtime", str(installed_runtime)) if installed_runtime is not None else ()
    command = (*prefix, "hook", "install", *selection, "--root", repo.as_posix(), "--json")
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
        selected = require_selected_runtime(manifest_path.parent, expected_build=build)
    except (OSError, TypeError, ValueError) as error:
        message = "package_runtime_identity_mismatch"
        raise RuntimeError(message) from error
    expected_root = Path(git_common_dir(repo)) / "ethos/runtime"
    expected_report = {
        **build._asdict(),
        "wheel_sha256": wheel_sha256,
        "runtime_digest": selected.digest,
    }
    if (
        manifest_path.parent.parent != expected_root
        or selected.manifest != manifest_path
        or selected.digest != runtime_digest
        or selected.python != python
        or selected.wheel_sha256 != wheel_sha256
        or any(report.get(key) != value for key, value in expected_report.items())
    ):
        message = "package_runtime_identity_mismatch"
        raise RuntimeError(message)
    return selected.python


def require_production_dependencies(
    python: Path, *, environment: Mapping[str, str]
) -> dict[str, object]:
    """Require the immutable package runtime to exclude development dependencies."""
    probe = """
import importlib.util
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from ethos.adapters.repo.hook.admission import _check_staged_python_format

assert importlib.util.find_spec("pytest") is None
with TemporaryDirectory(prefix="ethos-installed-format-") as temporary:
    root = Path(temporary)
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / "ruff.toml").write_text("line-length = 100\\n")
    source = root / "change.py"
    for staged, working, rejected in (("VALUE=1\\n", "VALUE = 1\\n", True),
                                      ("VALUE = 1\\n", "VALUE=1\\n", False)):
        source.write_text(staged)
        subprocess.run(["git", "-C", str(root), "add", "change.py"], check=True)
        source.write_text(working)
        try:
            _check_staged_python_format(root, ("change.py",))
        except RuntimeError as error:
            assert rejected and "pre_commit_python_format_failed" in str(error), str(error)
        else:
            assert not rejected, "installed formatter skipped invalid staged bytes"
        assert source.read_text() == working
        observed = subprocess.check_output(["git", "-C", str(root), "show", ":change.py"])
        assert observed == staged.encode()
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
    return {"state": "passed", "excluded": ["pytest"], "staged_format": "passed"}


def require_version_identity(
    python: Path,
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
    command = (*prefix, "--version", "--json")
    returncode, payload, diagnostic = invoke(python.parent, command, environment=environment)
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
    (hooks_path / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
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


def _prove_external_supply_recovery(
    prefix: tuple[str, ...], repo: Path, runtime: Path, *, environment: Mapping[str, str]
) -> None:
    """Reject damaged supply, then recover an absent selection from the invoking package."""
    packages = runtime.parent.parent / "packages"
    preserved = packages.with_name("preserved-packages")
    common = Path(git_common_dir(repo))
    selector = common / "ethos/runtime/CURRENT"
    original = selector.read_bytes()
    packages.rename(preserved)
    try:
        code, report, detail = invoke(
            repo,
            (*prefix, "hook", "install", "--root", str(repo), "--json"),
            environment=environment,
        )
        recovery = shlex.split(str(report.get("next_action") or ""))
        expected = f"hook_install_failed:hook_runtime_installed_supply_invalid:{runtime}"
        if (
            not code
            or report.get("required_gaps") != [expected]
            or "--runtime" not in recovery
            or str(runtime) in recovery
            or report.get("user_decision_required") is not True
            or selector.read_bytes() != original
            or any(path.is_dir() for path in selector.parent.iterdir())
        ):
            message = f"shared_supply_failure_not_preserved:{detail}"
            raise RuntimeError(message)
    finally:
        preserved.rename(packages)
    _activate(prefix, repo, environment=environment, installed_runtime=runtime)
    missing = repo.parent / "missing-installation/ethos/runtime" / runtime.name
    if missing.exists() or missing.is_symlink():
        message = "shared_missing_selection_fixture_occupied"
        raise RuntimeError(message)
    selector.write_bytes(runtime_selection_bytes(common, missing))
    code, recovered, detail = invoke(
        repo,
        (*prefix, "hook", "install", "--root", str(repo), "--json"),
        environment=environment,
    )
    data = recovered.get("data")
    if (
        code
        or recovered.get("verdict") != "pass"
        or not isinstance(data, dict)
        or Path(str(data.get("runtime_manifest_path") or "")) != runtime / "manifest.json"
        or selector.read_bytes() != original
        or any(path.is_dir() for path in selector.parent.iterdir())
    ):
        message = f"shared_missing_selection_recovery_failed:{detail}"
        raise RuntimeError(message)


def prove_shared_supply(
    archive: Path,
    work: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Exercise independent repositories against the same delivered immutable supply."""
    installed = work / "shared-installation"
    with tarfile.open(archive) as packed:
        packed.extractall(installed, filter="tar")
    generations = tuple((installed / "ethos/runtime").iterdir())
    if len(generations) != 1:
        message = "shared_supply_generation_ambiguous"
        raise ValueError(message)
    selected = require_selected_runtime(generations[0])
    prefix = (str(selected.python), "-B", "-I", "-m", "ethos.cli")
    repositories = [work / f"shared-adopter-{ordinal}" for ordinal in range(2)]
    selectors, databases = [], []
    for repo in repositories:
        run_command(work, ("git", "init", "--quiet", "--initial-branch=dev", str(repo)), check=True)
        data = _activate(prefix, repo, environment=environment, installed_runtime=selected.root)
        common = Path(git_common_dir(repo))
        selector = common / "ethos/runtime/CURRENT"
        selectors.append(selector)
        databases.append(common / "ethos/state.sqlite")
        if any(path.is_dir() for path in selector.parent.iterdir()):
            message = "shared_supply_was_copied"
            raise RuntimeError(message)
        if Path(str(data.get("runtime_manifest_path") or "")) != selected.manifest:
            message = "shared_supply_was_reselected"
            raise RuntimeError(message)
    original = selectors[0].read_bytes()
    if (
        databases[0].samefile(databases[1])
        or selectors[0].samefile(selectors[1])
        or original != selectors[1].read_bytes()
    ):
        message = "shared_repository_selection_or_state_invalid"
        raise RuntimeError(message)
    selectors[0].write_bytes(b"invalid\n")
    for ordinal, repo in enumerate(repositories):
        _code, report, detail = invoke(
            repo, (*prefix, "status", "--root", str(repo), "--json"), environment=environment
        )
        data = report.get("data")
        runtime = data.get("hook_runtime") if isinstance(data, dict) else None
        if not isinstance(runtime, dict) or runtime.get("current") is not (ordinal != 0):
            message = f"shared_repository_isolation_failed:{detail}"
            raise RuntimeError(message)
    _activate(prefix, repositories[0], environment=environment, installed_runtime=selected.root)
    _prove_external_supply_recovery(prefix, repositories[0], selected.root, environment=environment)
    if selectors[0].read_bytes() != original or require_selected_runtime(selected.root) != selected:
        message = "shared_supply_recovery_or_integrity_failed"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "runtime_digest": selected.digest,
        "repository_count": len(repositories),
        "shared_bytes": True,
        "independent_state": True,
        "damaged_selector_isolated": True,
        "invalid_supply_preserves_selection": True,
        "missing_selection_recovered": True,
        "recovered": True,
        "package_manager_uninstall_qualified": False,
    }
