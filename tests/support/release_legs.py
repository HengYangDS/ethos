"""One release leg's upload as `release_assets` reads it: wheel, archive, evidence, inventories."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

VERSION = "0.2.0-alpha.5"


def inventory_documents(name: str, digest: str, *, components: int = 1) -> tuple[dict, dict]:
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
    # Each runner records the archive in its own path syntax; Windows separates with backslashes.
    separator = "\\" if platform == "windows" else "/"
    runner = separator.join(("D:" if platform == "windows" else "", "a", "build/artifacts/native"))
    digest = hashlib.sha256(host.encode()).hexdigest()
    distribution = {
        "path": separator.join((runner, runtime, archive.name)),
        "sha256": digest,
        "runtime_digest": runtime,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "platform": platform,
        "architecture": machine,
        "product_version": VERSION,
    }
    evidence.write_text(json.dumps({"distribution": distribution}), encoding="utf-8")
    write_inventories(job, f"ethos-{VERSION}-{host}.tar.gz", digest)
    return wheel, archive
