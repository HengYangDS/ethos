"""Build deterministic portable distributions from an already verified runtime."""

from __future__ import annotations

import gzip
import hashlib
import json
import shlex
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.repository.release.identity import is_release_build
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage

if TYPE_CHECKING:
    from collections.abc import Mapping


def package_runtime(
    runtime: Path, wheel: Path, destination: Path, *, download_url: str | None = None
) -> dict[str, object]:
    """Archive exact installed bytes; project Homebrew only on supported hosts."""
    selected = require_selected_runtime(runtime)
    url = download_url or destination.resolve().as_uri()
    _require_distribution_version(selected, url)
    payload = wheel.read_bytes()
    if wheel.is_symlink() or hashlib.sha256(payload).hexdigest() != selected.wheel_sha256:
        message = "distribution_wheel_mismatch"
        raise ValueError(message)
    if destination.is_symlink() or destination.resolve().is_relative_to(runtime.resolve()):
        message = "distribution_destination_invalid"
        raise ValueError(message)
    disk_image = destination.suffix == ".dmg"
    if disk_image and selected.platform != "darwin":
        message = "distribution_disk_image_requires_macos"
        raise ValueError(message)
    if not disk_image and not destination.name.endswith(".tar.gz"):
        message = "distribution_format_unsupported"
        raise ValueError(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cask_path: Path | None = None
    with TemporaryDirectory(prefix=".ethos-distribution-", dir=destination.parent) as work:
        archive_path = Path(work) / destination.name
        if disk_image:
            payload_root = Path(work) / "payload"
            copied = payload_root / "ethos/runtime" / selected.digest
            shutil.copytree(runtime, copied, symlinks=True)
            package = payload_root / "ethos/packages" / selected.wheel_sha256 / wheel.name
            package.parent.mkdir(parents=True)
            shutil.copy2(wheel, package)
            if require_selected_runtime(copied).digest != selected.digest:
                message = "distribution_inputs_changed"
                raise ValueError(message)
            _disk_image(payload_root, archive_path)
        else:
            with (
                archive_path.open("wb") as stream,
                gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed,
                tarfile.open(fileobj=compressed, mode="w") as archive,
            ):
                archive.add(
                    runtime,
                    arcname=f"ethos/runtime/{selected.digest}",
                    filter=_metadata,
                )
                archive.add(
                    wheel,
                    arcname=f"ethos/packages/{selected.wheel_sha256}/{wheel.name}",
                    filter=_metadata,
                )
        if require_selected_runtime(runtime) != selected or wheel.read_bytes() != payload:
            message = "distribution_inputs_changed"
            raise ValueError(message)
        with archive_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        cask = None if selected.platform == "windows" else homebrew_cask(selected, url, digest)
        cask_path = _publish_outputs(archive_path, destination, cask, Path(work))
    return {
        "path": str(destination),
        "homebrew_cask": str(cask_path) if cask_path is not None else None,
        "published": False,
        "sha256": digest,
        "runtime_digest": selected.digest,
        "wheel_sha256": selected.wheel_sha256,
        "platform": selected.platform,
        "architecture": selected.architecture,
        **selected.build.projection(),
    }


def _publish_outputs(archive: Path, destination: Path, cask: str | None, work: Path) -> Path | None:
    """Replace the archive only after its companion Cask is staged and recoverable."""
    if cask is None:
        archive.replace(destination)
        return None
    cask_path = destination.parent / "homebrew" / "Casks" / "ethos.rb"
    if any(path.is_symlink() for path in (cask_path.parent.parent, cask_path.parent, cask_path)):
        message = "distribution_cask_destination_invalid"
        raise ValueError(message)
    staged = work / "ethos.rb"
    staged.write_text(cask, encoding="utf-8")
    cask_path.parent.mkdir(parents=True, exist_ok=True)
    previous = work / "previous-ethos.rb"
    if cask_path.exists():
        shutil.copy2(cask_path, previous)
    staged.replace(cask_path)
    try:
        archive.replace(destination)
    except OSError:
        if previous.exists():
            previous.replace(cask_path)
        else:
            cask_path.unlink(missing_ok=True)
        raise
    return cask_path


def _disk_image(payload: Path, destination: Path) -> None:
    """Create one native envelope without executing or re-signing its sealed payload."""
    producer = ("/usr/sbin/diskutil", "image", "create", "from")
    capability = run_command(payload, (*producer, "--help"), timeout=10)
    if capability.returncode not in {0, 1}:
        capability.check_returncode()
    command = (
        (*producer, "--format", "UDZO", "--volumeName", "ETHOS")
        if capability.returncode == 0
        else (
            "/usr/bin/hdiutil",
            "create",
            "-format",
            "UDZO",
            "-volname",
            "ETHOS",
            "-srcfolder",
        )
    )
    run_command(payload, (*command, str(payload), str(destination)), check=True, timeout=180)


def _metadata(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalize archive-only metadata while retaining executable payload permissions."""
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ""
    return info


def homebrew_cask(selected: SelectedRuntime, url: str, digest: str) -> str:
    """Project one platform-qualified archive into native Homebrew installation."""
    _require_distribution_version(selected, url)
    operating_system = "macos" if selected.platform == "darwin" else selected.platform
    architecture = "arm64" if selected.architecture == "aarch64" else selected.architecture
    if operating_system not in {"macos", "linux"} or architecture not in {
        "arm64",
        "x86_64",
    }:
        message = "distribution_platform_unsupported"
        raise ValueError(message)
    if "#{" in url:
        message = "distribution_url_invalid"
        raise ValueError(message)
    version = (
        selected.build.product_version
        if is_release_build(selected.build)
        else selected.build.distribution_version
    )
    return f'''# Generated from exact package acceptance; not a separate version authority.
cask "ethos" do
  version {json.dumps(version)}
  sha256 "{digest}"
  url {json.dumps(url)}
  name "ETHOS"
  desc "Reliable human and agent repository evolution"
  homepage "https://github.com/HengYangDS/ethos"

  depends_on :{operating_system}
  depends_on arch: :{architecture}
  depends_on formula: "git"

  preflight_steps do
    on_macos do
      run "/usr/bin/codesign",
          args: ["--verify", "--strict", "--all-architectures", "--check-notarization",
                 "--test-requirement", "=notarized",
                 "{{{{staged_path}}}}/ethos/runtime/{selected.digest}/python/bin/python"],
          network_access: true
    end
    set_permissions "ethos/runtime/{selected.digest}", "a-w"
    run "ethos/runtime/{selected.digest}/python/bin/python", base: :staged_path,
        args: ["-B", "-I", "-c",
               "from pathlib import Path; import sys; " \\
               "from ethos.adapters.repo.runtime.selection import require_selected_runtime; " \\
               "require_selected_runtime(Path(sys.prefix).parent)"]
  end

  command_wrapper "ethos",
                  executable: "#{{staged_path}}/ethos/runtime/{selected.digest}/python/bin/ethos"
end
'''


def _require_distribution_version(selected: SelectedRuntime, url: str) -> None:
    """Keep source-development packages out of remote release-channel projections."""
    if urlsplit(url).scheme != "file" and not is_release_build(selected.build):
        message = "distribution_release_build_required"
        raise ValueError(message)


def _prove_external_supply_recovery(
    prefix: tuple[str, ...],
    repo: Path,
    runtime: Path,
    *,
    environment: Mapping[str, str],
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
    runtime_acceptance.activate_from_runtime(
        Path(prefix[0]), repo, environment=environment, installed_runtime=runtime
    )
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


@observe_stage("shared_supply")
def prove_shared_supply(
    archive: Path,
    work: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Exercise independent repositories against the same delivered immutable supply."""
    installed = work / "shared-installation"
    with observe_stage("shared_archive_extraction"), tarfile.open(archive) as packed:
        packed.extractall(installed, filter="tar")
    generations = tuple((installed / "ethos/runtime").iterdir())
    if len(generations) != 1:
        message = "shared_supply_generation_ambiguous"
        raise ValueError(message)
    with observe_stage("shared_source_validation"):
        selected = require_selected_runtime(generations[0])
    scoped_environment = {**environment, "XDG_DATA_HOME": str(work / "host-data")}
    pinned_root = (
        work / "host-data/ethos/installations" / selected.digest[:16] / "runtime" / selected.digest
    )
    repositories = [work / f"shared-adopter-{ordinal}" for ordinal in range(2)]
    selectors, databases = [], []
    for repo in repositories:
        run_command(
            work,
            ("git", "init", "--quiet", "--initial-branch=dev", str(repo)),
            check=True,
        )
        with observe_stage("shared_repository_binding", target=repo.name):
            data = runtime_acceptance.activate_from_runtime(
                selected.python, repo, environment=scoped_environment
            )
        common = Path(git_common_dir(repo))
        selector = common / "ethos/runtime/CURRENT"
        selectors.append(selector)
        databases.append(common / "ethos/state.sqlite")
        if any(path.is_dir() for path in selector.parent.iterdir()):
            message = "shared_supply_was_copied"
            raise RuntimeError(message)
        if Path(str(data.get("runtime_manifest_path") or "")) != pinned_root / "manifest.json":
            message = "shared_supply_was_reselected"
            raise RuntimeError(message)
    with observe_stage("shared_target_validation"):
        pinned = require_selected_runtime(pinned_root)
    prefix = (str(pinned.python), "-B", "-I", "-m", "ethos.cli")
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
            repo,
            (*prefix, "status", "--root", str(repo), "--json"),
            environment=scoped_environment,
        )
        data = report.get("data")
        runtime = data.get("hook_runtime") if isinstance(data, dict) else None
        if not isinstance(runtime, dict) or runtime.get("current") is not (ordinal != 0):
            message = f"shared_repository_isolation_failed:{detail}"
            raise RuntimeError(message)
    runtime_acceptance.activate_from_runtime(
        pinned.python,
        repositories[0],
        environment=scoped_environment,
        installed_runtime=pinned.root,
    )
    _prove_external_supply_recovery(
        prefix, repositories[0], pinned.root, environment=scoped_environment
    )
    if selectors[0].read_bytes() != original or require_selected_runtime(pinned_root) != pinned:
        message = "shared_supply_recovery_or_integrity_failed"
        raise RuntimeError(message)
    _prove_package_carrier_removal(installed, prefix, repositories, scoped_environment)
    return {
        "state": "passed",
        "runtime_digest": selected.digest,
        "repository_count": len(repositories),
        "shared_bytes": True,
        "independent_state": True,
        "damaged_selector_isolated": True,
        "invalid_supply_preserves_selection": True,
        "missing_selection_recovered": True,
        "source_removal_preserves_consumers": True,
        "recovered": True,
        "package_manager_uninstall_qualified": False,
    }


def _prove_package_carrier_removal(
    installed: Path,
    prefix: tuple[str, ...],
    repositories: list[Path],
    environment: Mapping[str, str],
) -> None:
    """Remove package-owned bytes and run both repositories from pinned supply."""
    remove_generated_tree(installed)
    for repo in repositories:
        code, report, detail = invoke(
            repo,
            (*prefix, "status", "--root", str(repo), "--json"),
            environment=environment,
        )
        data = report.get("data")
        runtime = data.get("hook_runtime") if isinstance(data, dict) else None
        if code or not isinstance(runtime, dict) or runtime.get("current") is not True:
            message = f"shared_supply_source_removal_failed:{detail}"
            raise RuntimeError(message)
