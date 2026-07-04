from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.release.core import version_manifest

if TYPE_CHECKING:
    from pathlib import Path


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sbom_projection(root: Path) -> dict[str, Any]:
    manifest = version_manifest(root)
    packages = [
        {"name": name, "version": version, "supplier": "ETHOS"}
        for name, version in sorted(manifest["packages"].items())
    ]
    payload = {
        "format": "SPDX-lite",
        "schema_version": 1,
        "truth": "pyproject-and-lockfile",
        "packages": packages,
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
                ],
            },
            "sbom": sbom,
        },
    }
