from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.planning.rules import repo_with_product_rules

if TYPE_CHECKING:
    from pathlib import Path


def _commit_all(repo: Path, message: str) -> None:
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
        message,
    )


def test_plan_changed_requires_quality_audit_for_quality_gate_governance_script(
    tmp_path: Path,
) -> None:
    repo = repo_with_product_rules(tmp_path)
    changed = (
        repo
        / ".agents"
        / "skills"
        / "ethos-quality-gate-governance"
        / "scripts"
        / "quality_audit.py"
    )
    changed.parent.mkdir(parents=True)
    changed.write_text("print('quality audit')\n", encoding="utf-8")
    _commit_all(repo, "seed quality audit script")
    changed.write_text("print('quality audit changed')\n", encoding="utf-8")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["summary"]["matched_rule_count"] == 2
    assert payload["summary"]["required_gate_count"] == 2
    assert {rule["id"] for rule in payload["data"]["matched_rules"]} == {
        "quality-gate-governance",
        "skill-portfolio-governance",
    }
    assert payload["data"]["required_gates"] == [
        {
            "id": "quality-audit",
            "command": ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py .",
            "blocking": True,
        },
        {
            "id": "skill-portfolio-audit",
            "command": ".agents/skills/ethos-skill-portfolio-governance/scripts/portfolio_audit.py .",
            "blocking": True,
        },
    ]
