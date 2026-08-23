"""Exact-wheel SPDX SBOM evidence owned by the repository Nox graph."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_command

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".config/release/supply-chain.toml"
SYSTEM_SYFT_LOCATIONS = (Path("/opt/homebrew/bin/syft"), Path("/usr/local/bin/syft"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _single_artifact(pattern: str) -> Path:
    artifacts = tuple(ROOT.glob(pattern))
    if len(artifacts) != 1:
        message = f"expected exactly one artifact matching {pattern}"
        raise RuntimeError(message)
    return artifacts[0]


def _syft(expected_version: str) -> Path:
    run_command(ROOT, (str(ROOT / "tools/ci/scripts/install-syft.sh"),), check=True)
    default_cache = ROOT / "build/runtime/tool-cache/ci-tools"
    cache = Path(os.environ.get("ETHOS_CI_TOOL_CACHE_DIR", default_cache))
    locations = (cache / "syft" / expected_version / "syft", *SYSTEM_SYFT_LOCATIONS)
    for executable in locations:
        if not executable.is_file():
            continue
        completed = run_command(ROOT, (str(executable), "version", "-o", "json"), check=True)
        if json.loads(completed.stdout).get("version") == expected_version:
            return executable
    message = f"expected syft {expected_version} at a repository-declared location"
    raise RuntimeError(message)


def run(session: nox.Session) -> None:
    """Generate one SPDX 2.3 SBOM and a receipt with deliberately bounded claims."""
    policy = tomllib.loads(POLICY.read_text(encoding="utf-8"))
    artifact = _single_artifact(str(policy["artifact_glob"]))
    output, sbom = (ROOT / str(policy[key]) for key in ("output", "sbom"))
    output.parent.mkdir(parents=True, exist_ok=True)
    sbom.parent.mkdir(parents=True, exist_ok=True)
    executable = _syft(str(policy["version"]))
    run_command(
        ROOT,
        (
            str(executable),
            "scan",
            f"file:{artifact}",
            "--quiet",
            "--output",
            f"spdx-json={sbom}",
        ),
        check=True,
    )
    document = json.loads(sbom.read_text(encoding="utf-8"))
    if document.get("spdxVersion") != "SPDX-2.3":
        message = "syft output is not SPDX 2.3"
        raise RuntimeError(message)
    payload = {
        "schema_version": 1,
        "kind": "ethos_release_supply_chain_evidence",
        "verdict": "pass",
        "head": current_tracked_head(ROOT),
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact": {"path": artifact.relative_to(ROOT).as_posix(), "sha256": _digest(artifact)},
        "sbom": {
            "path": sbom.relative_to(ROOT).as_posix(),
            "sha256": _digest(sbom),
            "format": "SPDX-2.3",
        },
        "generator": {"tool": "syft", "version": policy["version"]},
        "not_claimed": [
            "provenance",
            "signature",
            "SLSA level",
            "hosted CI",
            "publication",
        ],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    session.log(rendered)
