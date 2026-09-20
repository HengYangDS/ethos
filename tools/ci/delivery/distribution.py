"""Build deterministic portable distributions from an already verified runtime."""

from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import require_selected_runtime


def package_runtime(
    runtime: Path, wheel: Path, destination: Path, *, download_url: str | None = None
) -> dict[str, object]:
    """Archive exact installed bytes without rebuilding or changing their identity."""
    selected = require_selected_runtime(runtime)
    payload = wheel.read_bytes()
    if wheel.is_symlink() or hashlib.sha256(payload).hexdigest() != selected.wheel_sha256:
        message = "distribution_wheel_mismatch"
        raise ValueError(message)
    if destination.is_symlink() or destination.resolve().is_relative_to(runtime.resolve()):
        message = "distribution_destination_invalid"
        raise ValueError(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ethos-distribution-", dir=destination.parent) as work:
        archive_path = Path(work) / "product.tar.gz"
        with (
            archive_path.open("wb") as stream,
            gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as archive,
        ):
            archive.add(runtime, arcname=f"ethos/runtime/{selected.digest}", filter=_metadata)
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
        formula = _homebrew_formula(
            selected, download_url or destination.resolve().as_uri(), digest
        )
        archive_path.replace(destination)
        formula_path = destination.parent / "homebrew" / "ethos.rb"
        formula_path.parent.mkdir(exist_ok=True)
        formula_path.write_text(formula)
    return {
        "path": str(destination),
        "homebrew_formula": str(formula_path),
        "published": False,
        "sha256": digest,
        "runtime_digest": selected.digest,
        "wheel_sha256": selected.wheel_sha256,
        "platform": selected.platform,
        "architecture": selected.architecture,
        **selected.build.projection(),
    }


def _metadata(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalize archive-only metadata while retaining executable payload permissions."""
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ""
    return info


def _homebrew_formula(selected: SelectedRuntime, url: str, digest: str) -> str:
    """Project one platform-qualified archive into native Homebrew installation."""
    operating_system = "macos" if selected.platform == "darwin" else selected.platform
    architecture = "arm64" if selected.architecture == "aarch64" else selected.architecture
    if operating_system not in {"macos", "linux"} or architecture not in {"arm64", "x86_64"}:
        message = "distribution_platform_unsupported"
        raise ValueError(message)
    if "#{" in url:
        message = "distribution_url_invalid"
        raise ValueError(message)
    return f'''# Generated from exact package acceptance; not a separate version authority.
class Ethos < Formula
  desc "Reliable human and agent repository evolution"
  homepage "https://github.com/HengYangDS/ethos"
  url {json.dumps(url)}
  version {json.dumps(selected.build.distribution_version)}
  sha256 "{digest}"
  license "Apache-2.0"

  depends_on :{operating_system}
  depends_on arch: :{architecture}
  depends_on "git"
  skip_clean "libexec"

  def install
    libexec.install "runtime", "packages"
    bin.write_exec_script libexec/"runtime/{selected.digest}/python/bin/ethos"
  end

  test do
    assert_match {json.dumps(selected.build.source_commit[:12])},
                 shell_output("#{{bin}}/ethos --version")
    system libexec/"runtime/{selected.digest}/python/bin/python", "-B", "-I", "-c",
           "from pathlib import Path; import sys; " \\
           "from ethos.adapters.repo.runtime.selection import require_selected_runtime; " \\
           "require_selected_runtime(Path(sys.argv[1]))",
           libexec/"runtime/{selected.digest}"
  end
end
'''
