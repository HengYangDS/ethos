"""Build deterministic portable distributions from an already verified runtime."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
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
from ethos.adapters.repo.runtime.materialization.python_image import render_console_script
from ethos.adapters.repo.runtime.materialization.python_image import render_windows_console_script
from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.repository.release.identity import is_release_build
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    from collections.abc import Mapping

# The only archive directory a package manager puts on PATH; it holds the ETHOS console alone.
CONSOLE_DIRECTORY = "ethos/bin"


def package_runtime(
    runtime: Path,
    wheel: Path,
    destination: Path,
    *,
    download_url: str | None = None,
    acceptance: dict[str, object] | None = None,
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
                _add_console(archive, selected)
        if require_selected_runtime(runtime) != selected or wheel.read_bytes() != payload:
            message = "distribution_inputs_changed"
            raise ValueError(message)
        with archive_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if acceptance is not None and (
            digest != acceptance["sha256"]
            or selected.digest != acceptance["runtime_digest"]
            or selected.wheel_sha256 != acceptance["wheel_sha256"]
        ):
            message = "local_install_distribution_changed"
            raise ValueError(message)
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


def retain_qualified_distribution(
    qualified: dict[str, object],
    runtime: Path,
    wheel: Path,
    destination: Path,
) -> dict[str, object]:
    """Retain the same deterministic package only after its native journey passes."""
    retained = package_runtime(runtime, wheel, destination, acceptance=qualified)
    retained["shared_supply"] = qualified["shared_supply"]
    retained["retained"] = True
    return retained


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
    """Normalize archive-only metadata while retaining executable payload permissions.

    Directories open to their owner, so a package manager can remove what it installed;
    sealed file modes and bytes stay part of the runtime inventory and its digest.
    """
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ""
    if info.isdir():
        info.mode |= 0o700
    return info


def _add_console(archive: tarfile.TarFile, selected: SelectedRuntime) -> None:
    """Add the runtime's ETHOS console as the archive's only `PATH` entry.

    The runtime's own script directory also holds its interpreter and every bundled tool,
    which would otherwise resolve ahead of an adopter's own.
    """
    directory = tarfile.TarInfo(CONSOLE_DIRECTORY)
    directory.type, directory.mode = tarfile.DIRTYPE, 0o555
    archive.addfile(_metadata(directory))
    runtime = f"../runtime/{selected.digest}/python"
    if selected.platform == "windows":
        interpreter = runtime.replace("/", "\\") + "\\python.exe"
        name = "ethos.cmd"
        text = render_windows_console_script("ethos", interpreter).replace("\n", "\r\n")
    else:
        name, text = "ethos", render_console_script("ethos", f"{runtime}/bin/python")
    payload = text.encode()
    console = tarfile.TarInfo(f"{CONSOLE_DIRECTORY}/{name}")
    console.size, console.mode = len(payload), 0o555
    archive.addfile(_metadata(console), io.BytesIO(payload))


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


def _mise(
    mise: Path, project: Path, arguments: tuple[str, ...], environment: Mapping[str, str]
) -> str:
    completed = run_command(
        project,
        (str(mise), "--cd", str(project), *arguments),
        env=environment,
        inherit_environment=False,
        timeout=600,
    )
    if completed.returncode:
        output = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
        detail = f"{shlex.join(arguments)}:exit={completed.returncode}:{output}"
        message = f"shared_supply_package_manager_failed:{detail}"
        raise RuntimeError(message)
    return completed.stdout


@observe_stage("shared_package_installation")
def _install_with_mise(
    archive: Path, home: Path, *, mise: Path, environment: Mapping[str, str]
) -> tuple[Path, Path, dict[str, str]]:
    """Install the archive as adopters do: one locked Mise `http:` tool and its console."""
    with tarfile.open(archive) as packed:
        manifests = [
            name
            for name in packed.getnames()
            if re.fullmatch(r"ethos/runtime/[0-9a-f]{64}/manifest\.json", name)
        ]
        if len(manifests) != 1:
            message = "shared_supply_generation_ambiguous"
            raise ValueError(message)
        member = packed.extractfile(manifests[0])
        manifest = json.load(member) if member else {}
    # Adopters label the tool with its product version, which also keeps a Windows install's
    # paths within what `cmd` runs; the console must still report the exact distribution.
    version = manifest.get("product_version", "")
    distribution = manifest.get("distribution_version")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    # The project is its own repository, as an adopter's is before ETHOS selects a runtime:
    # the installed console then runs its own runtime, not one an enclosing checkout selected.
    project = home / "project"
    project.mkdir(parents=True)
    run_command(home, ("git", "init", "--quiet", "--initial-branch=dev", str(project)), check=True)
    declaration = project / "mise.toml"
    declaration.write_text(
        f'[tools."http:ethos"]\nversion = "{version}"\nurl = "{archive.resolve().as_uri()}"\n'
        f'checksum = "sha256:{digest}"\nbin_path = "{CONSOLE_DIRECTORY}"\n',
        encoding="utf-8",
    )
    scoped = {
        **environment,
        **{f"MISE_{name}_DIR": str(home / name.lower()) for name in ("DATA", "CONFIG", "STATE")},
        "MISE_CACHE_DIR": str(home / "cache"),
        "MISE_CEILING_PATHS": str(home),
        "MISE_GLOBAL_CONFIG_FILE": str(home / "absent-global.toml"),
        "MISE_SYSTEM_CONFIG_DIR": str(home / "absent-system"),
        "MISE_TRUSTED_CONFIG_PATHS": str(declaration),
        "MISE_DISABLE_UPDATE_WARNING": "1",
        "MISE_OFFLINE": "1",
        "MISE_YES": "1",
    }
    for arguments in (("lock",), ("install", "--locked")):
        _mise(mise, project, arguments, scoped)
    installed = Path(_mise(mise, project, ("where", "http:ethos"), scoped).strip())
    entries = sorted(path.name for path in (installed / CONSOLE_DIRECTORY).iterdir())
    if entries not in (["ethos"], ["ethos.cmd"]):
        message = f"shared_supply_path_entries_invalid:{','.join(entries)}"
        raise RuntimeError(message)
    console = _mise(mise, project, ("exec", "--locked", "--", "ethos", "--version"), scoped)
    if not distribution or distribution not in console:
        message = f"shared_supply_console_failed:{console.strip()}"
        raise RuntimeError(message)
    return installed, project, scoped


@observe_stage("shared_supply")
def prove_shared_supply(
    archive: Path,
    work: Path,
    *,
    environment: Mapping[str, str],
    root: Path,
) -> dict[str, object]:
    """Exercise independent repositories against the same delivered immutable supply."""
    mise = prepare_mise(root)
    installed, project, managed = _install_with_mise(
        archive, work / "package-manager", mise=mise, environment=environment
    )
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
    _prove_package_carrier_removal(
        (mise, project, installed, managed), prefix, repositories, scoped_environment
    )
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
        "package_manager": "mise",
        "console_entry_qualified": True,
        "package_manager_uninstall_qualified": True,
    }


def _prove_package_carrier_removal(
    manager: tuple[Path, Path, Path, Mapping[str, str]],
    prefix: tuple[str, ...],
    repositories: list[Path],
    environment: Mapping[str, str],
) -> None:
    """Run the managed console, uninstall it natively, then run both repositories from pins."""
    mise, project, installed, managed = manager
    console = (mise, "--cd", project, "exec", "--locked", "--", "ethos", "status")
    code, report, detail = invoke(
        repositories[0],
        (*map(str, console), "--root", str(repositories[0]), "--json"),
        environment={**managed, **environment},
    )
    data = report.get("data")
    runtime = data.get("hook_runtime") if isinstance(data, dict) else None
    if not isinstance(runtime, dict) or runtime.get("current") is not True:
        message = f"shared_supply_console_failed:{code}:{detail}"
        raise RuntimeError(message)
    _mise(mise, project, ("uninstall", "http:ethos"), managed)
    if installed.exists():
        message = "shared_supply_package_manager_uninstall_incomplete"
        raise RuntimeError(message)
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
