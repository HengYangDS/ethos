"""Exact-wheel SPDX SBOM evidence owned by the repository Nox graph."""

from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from tools.ci.toolchain.native import NativeSupply
from tools.ci.toolchain.native import prepare

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".config/release/supply-chain.toml"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _single_artifact(pattern: str) -> Path:
    artifacts = tuple(ROOT.glob(pattern))
    if len(artifacts) != 1:
        message = f"expected exactly one artifact matching {pattern}"
        raise RuntimeError(message)
    return artifacts[0]


def run(session: nox.Session) -> None:
    """Generate one SPDX 2.3 SBOM and a receipt with deliberately bounded claims."""
    policy = tomllib.loads(POLICY.read_text(encoding="utf-8"))
    artifact = _single_artifact(str(policy["artifact_glob"]))
    output, sbom = (ROOT / str(policy[key]) for key in ("output", "sbom"))
    output.parent.mkdir(parents=True, exist_ok=True)
    sbom.parent.mkdir(parents=True, exist_ok=True)
    supply = NativeSupply.read(ROOT, "syft")
    executable = prepare(ROOT, "syft") / "syft"
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
        remove_env_prefixes=("GIT_",),
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
        "generator": {"tool": "syft", "version": supply.version},
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
