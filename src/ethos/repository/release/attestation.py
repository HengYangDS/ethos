from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.release.configuration import version_manifest

if TYPE_CHECKING:
    from pathlib import Path


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _lockfile_packages(root: Path) -> list[dict[str, Any]]:
    lock_path = root / "uv.lock"
    if not lock_path.exists():
        return []
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages: list[dict[str, Any]] = []
    for item in lock.get("package", []):
        if not isinstance(item, dict):
            continue
        source = item.get("source", {})
        if isinstance(source, dict) and ("editable" in source or "virtual" in source):
            continue
        name = str(item.get("name", ""))
        version = str(item.get("version", ""))
        if not name or not version:
            continue
        package: dict[str, Any] = {
            "name": name,
            "version": version,
            "supplier": "lockfile",
            "layer": "lockfile_transitive",
        }
        if isinstance(source, dict) and source.get("registry"):
            package["source"] = str(source["registry"])
        wheels = item.get("wheels", [])
        if isinstance(wheels, list):
            hashes = sorted(
                str(wheel.get("hash", ""))
                for wheel in wheels
                if isinstance(wheel, dict) and wheel.get("hash")
            )
            if hashes:
                package["hashes"] = hashes
        sdist = item.get("sdist", {})
        if isinstance(sdist, dict) and sdist.get("hash"):
            package["sdist_hash"] = str(sdist["hash"])
        packages.append(package)
    return sorted(packages, key=lambda package: (package["name"], package["version"]))


def sbom_projection(root: Path) -> dict[str, Any]:
    manifest = version_manifest(root)
    workspace_packages = [
        {
            "name": name,
            "version": version,
            "supplier": "ETHOS",
            "layer": "workspace",
        }
        for name, version in sorted(manifest["packages"].items())
    ]
    lockfile_packages = _lockfile_packages(root)
    lock_path = root / "uv.lock"
    payload = {
        "format": "SPDX-lite",
        "schema_version": 2,
        "truth": "pyproject-and-lockfile",
        "lockfile": {
            "path": "uv.lock",
            "digest": _file_sha256(lock_path) if lock_path.exists() else "",
        },
        "package_layers": {
            "workspace": len(workspace_packages),
            "lockfile_transitive": len(lockfile_packages),
        },
        "packages": workspace_packages + lockfile_packages,
    }
    return {**payload, "digest": _stable_digest(payload)}


def release_attestation(root: Path, *, head: str, evidence_digest: str) -> dict[str, Any]:
    manifest = version_manifest(root)
    sbom = sbom_projection(root)
    subject_name = f"ethos@{manifest['version']}"
    subject_digest = _stable_digest(
        {
            "head": head,
            "evidence_digest": evidence_digest,
            "packages": manifest["packages"],
            "lockfile_digest": sbom["lockfile"]["digest"],
            "sbom_digest": sbom["digest"],
        }
    )
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "predicateType": "https://ethos.local/provenance/ethos-release/v1",
        "subject": [
            {
                "name": subject_name,
                "digest": {"sha256": subject_digest},
            }
        ],
        "predicate": {
            "head": head,
            "evidence_digest": evidence_digest,
            "version": manifest["version"],
            "tag": manifest["tag"],
            "slsa": {
                "builder": {"id": "ethos"},
                "buildType": "https://ethos.local/build/python-workspace/v1",
                "materials": [
                    {"uri": "git+repository", "digest": {"sha1": head}},
                    {"uri": "ethos+evidence", "digest": {"sha256": evidence_digest}},
                    {
                        "uri": "file+uv.lock",
                        "digest": {"sha256": sbom["lockfile"]["digest"].removeprefix("sha256:")},
                    },
                    {"uri": "ethos+sbom", "digest": {"sha256": sbom["digest"]}},
                ],
            },
            "sbom": sbom,
        },
    }
