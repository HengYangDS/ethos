from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import cast

import ethos.assistants.playbooks as playbooks_module
from ethos.assistants.playbooks import playbooks_report
from ethos_core.contracts.context_projection import ASSISTANT_TRUTH_BOUNDARY


def projection_contract() -> dict[str, object]:
    return {
        "truth": "repository-source-and-contracts",
        "surfaces": ["codex", "claude", "jetbrains", "mcp", "acp"],
        "rules": [
            "assistant projections are thin adapters",
            "context packs may expose tools but must not become truth stores",
            "MCP and ACP adapters are protocol projections",
        ],
    }


def projection_drift_report(root: Path) -> dict[str, object]:
    """Report assistant projection digest drift against activation metadata."""
    contract = projection_contract()
    playbooks = playbooks_report(root, mode="v2-strict")
    registry = cast("dict[str, object]", playbooks["registry"])
    registry_meta = cast("dict[str, object]", registry["meta"])
    registry_digest = str(registry["digest"])
    expected_registry_digest = str(registry_meta.get("expected_registry_digest") or "")
    generator_digest = _sha256_file(Path(playbooks_module.__file__))
    expected_generator_digest = str(registry_meta.get("expected_generator_digest") or "")
    activation_digest = _sha256_file(root / ".agents" / "skills" / "activation.toml")
    drift = [
        {"kind": "skill_package", "gap": gap}
        for gap in cast("list[str]", playbooks["required_gaps"])
        if str(gap).startswith("skill_package_")
    ]
    if not expected_registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_expected_digest_missing"})
    elif expected_registry_digest != registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_digest_mismatch"})
    if not expected_generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_expected_digest_missing"}
        )
    elif expected_generator_digest != generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_digest_mismatch"}
        )
    ok = contract["truth"] == ASSISTANT_TRUTH_BOUNDARY and not drift
    gaps = (
        tuple(item["gap"] for item in drift)
        if contract["truth"] == ASSISTANT_TRUTH_BOUNDARY
        else ("assistant_projection_truth_drift",)
    )
    return {
        "ok": ok,
        "state": "clean" if ok else "blocked",
        "required_gaps": gaps,
        "contract": contract,
        "drift": drift,
        "registry_digest": registry_digest,
        "registry": {
            "digest": registry_digest,
            "expected_digest": expected_registry_digest,
            "ok": expected_registry_digest == registry_digest,
        },
        "generator": {
            "id": "ethos.assistants.playbooks",
            "digest": generator_digest,
            "expected_digest": expected_generator_digest,
            "ok": expected_generator_digest == generator_digest,
        },
        "inputs": [{"path": ".agents/skills/activation.toml", "digest": activation_digest}],
    }


def _sha256_file(path: Path) -> str:
    digest = sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"
