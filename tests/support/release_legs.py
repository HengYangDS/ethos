"""One release leg's upload as `release_assets` reads it: wheel, archive, evidence, inventories."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from tools.ci.delivery import release_assets

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

VERSION = "0.2.0-alpha.5"
# The commit every fixture leg records as its source, which assembly expects as the release head.
HEAD = "0123456789abcdef0123456789abcdef01234567"
# The declared release legs: host -> (platform, machine, wheel tag).
LEGS = {
    "linux-x64": ("linux", "x86_64", "linux_x86_64"),
    "linux-arm64": ("linux", "arm64", "linux_aarch64"),
    "macos-arm64": ("darwin", "arm64", "macosx_14_0_arm64"),
}
HOSTS = frozenset(LEGS)
ENTRY = f"# Changelog\n\n## [{VERSION}] - 2026-10-21\n\n### Added\n\n- Hosted release.\n"


def inventory_documents(
    name: str, digest: str, *, components: int = 1
) -> tuple[dict[str, object], dict[str, object]]:
    """Return an SPDX SBOM and a Syft inventory that describe one archive and its components."""
    root = "SPDXRef-DocumentRoot-File-archive"
    packages = [
        {
            "SPDXID": root,
            "name": name,
            "versionInfo": f"sha256:{digest}",
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
        }
    ] + [
        {"SPDXID": f"SPDXRef-Package-{index}", "name": f"component-{index}"}
        for index in range(components)
    ]
    spdx = {
        "spdxVersion": "SPDX-2.3",
        "name": name,
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relatedSpdxElement": root,
                "relationshipType": "DESCRIBES",
            }
        ],
    }
    syft = {
        "source": {
            "name": name,
            "version": f"sha256:{digest}",
            "type": "file",
            "metadata": {"digests": [{"algorithm": "sha256", "value": digest}]},
        },
        "artifacts": [{"name": f"component-{index}"} for index in range(components)],
        "files": [],
    }
    return spdx, syft


def write_inventories(
    job: Path, name: str, digest: str, *, components: int = 1
) -> tuple[Path, Path]:
    """Write a leg's two inventories where its upload carries them, beside its smoke record."""
    directory = job / "evidence/release"
    directory.mkdir(parents=True, exist_ok=True)
    spdx, syft = inventory_documents(name, digest, components=components)
    paths = (directory / "runtime.spdx.json", directory / "runtime.syft.json")
    for path, document in zip(paths, (spdx, syft), strict=True):
        path.write_text(json.dumps(document), encoding="utf-8")
    return paths


def qualified_leg(
    inputs: Path, host: str, platform: str, machine: str, tag: str
) -> tuple[Path, ...]:
    """Lay out one leg's upload for its declared host: wheel, archive, evidence and inventories."""
    job = inputs / f"release-runtime-{host}"
    runtime = hashlib.sha256(host.encode()).hexdigest()
    wheel = job / "artifacts/release/python" / f"ethos-0.2.0a5-py3-none-{tag}.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(f"wheel {host}".encode())
    archive = job / "artifacts/native" / runtime / "ethos-0.2.0a5.tar.gz"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(host.encode())
    evidence = job / "evidence/local-install/release-smoke.json"
    evidence.parent.mkdir(parents=True)
    runner = "/a/build/artifacts/native"
    digest = hashlib.sha256(host.encode()).hexdigest()
    distribution = {
        "path": f"{runner}/{runtime}/{archive.name}",
        "sha256": digest,
        "runtime_digest": runtime,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "platform": platform,
        "architecture": machine,
        "product_version": VERSION,
        "distribution_version": "0.2.0a5",
        "source_commit": HEAD,
    }
    evidence.write_text(json.dumps({"distribution": distribution}), encoding="utf-8")
    write_inventories(job, f"ethos-{VERSION}-{host}.tar.gz", digest)
    return wheel, archive


def assemble_release(
    tmp_path: Path,
    *,
    hosts: frozenset[str] = HOSTS,
    expect_head: str = HEAD,
    alter: Callable[[Path, str], object] | None = None,
    host: str = "linux-x64",
) -> tuple[Path, dict[str, str]]:
    """Lay out every declared leg, let `alter` edit `host`'s upload, and assemble the release."""
    inputs, changelog, out = tmp_path / "inputs", tmp_path / "CHANGELOG.md", tmp_path / "out"
    changelog.write_text(ENTRY, encoding="utf-8")
    for name, leg in LEGS.items():
        qualified_leg(inputs, name, *leg)
    if alter is not None:
        alter(inputs / f"release-runtime-{host}", host)
    sums = release_assets.assemble(
        inputs,
        out,
        tag=f"v{VERSION}",
        base_url="https://example.invalid/v",
        changelog=changelog,
        hosts=hosts,
        expect_head=expect_head,
    )
    return out, sums
