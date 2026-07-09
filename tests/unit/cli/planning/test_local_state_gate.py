from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.planning.rules import repo_with_product_rules

if TYPE_CHECKING:
    from pathlib import Path


def test_plan_changed_requires_local_state_gate_for_local_state_audit_policy(
    tmp_path: Path,
) -> None:
    repo = repo_with_product_rules(tmp_path)
    changed = repo / ".config" / "checks" / "local-state" / "audit.toml"
    changed.parent.mkdir(parents=True)
    changed.write_text('schema = "ethos-local-state-audit-v1"\n', encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "seed local state policy",
    )
    changed.write_text(
        'schema = "ethos-local-state-audit-v1"\n# changed\n',
        encoding="utf-8",
    )

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["summary"]["matched_rule_count"] == 2
    assert payload["summary"]["required_gate_count"] == 2
    assert {rule["id"] for rule in payload["data"]["matched_rules"]} == {
        "local-state-boundary",
        "quality-gate-governance",
    }
    assert payload["data"]["required_gates"] == [
        {
            "id": "local-state-audit",
            "command": "tools/ci/scripts/run-local-state-audit.sh",
            "blocking": True,
        },
        {
            "id": "quality-audit",
            "command": ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py .",
            "blocking": True,
        },
    ]
