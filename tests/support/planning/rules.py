from __future__ import annotations

from pathlib import Path

from tests.support.contract_helpers import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


def repo_with_product_rules(tmp_path: Path) -> Path:
    """Create a temporary repository with the product planning rules installed."""
    repo = init_git_repo(tmp_path / "repo")
    rules = repo / ".ethos" / "rules.toml"
    rules.write_text(
        (ROOT / ".ethos" / "rules.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return repo
