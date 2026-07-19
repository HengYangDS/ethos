# ruff: noqa: I001 - compact source-budget projection preserves the exact test AST.
# fmt: off

from __future__ import annotations
from typing import TYPE_CHECKING
from tests.unit.adoption.retirement.fixtures import git_add_all
from tests.unit.adoption.retirement.fixtures import init_git_repo
from tests.unit.adoption.retirement.fixtures import terminal_report
from tests.unit.adoption.retirement.fixtures import terminal_rollback
from tests.unit.adoption.retirement.fixtures import write_profile
if TYPE_CHECKING:
    from pathlib import Path

def test_retirement_readiness_accepts_terminal_embedded_retired_history_restore_state(tmp_path: Path) -> None:
    adopter = tmp_path / 'adopter'
    product = tmp_path / 'product'
    adopter.mkdir()
    product.mkdir()
    init_git_repo(adopter)
    init_git_repo(product)
    rollback = terminal_rollback(adopter, product)
    write_profile(adopter, external_state='retired', embedded_state='retired', rollback=rollback, control={'state': 'retired', 'default_backend': 'external', 'external_backend': 'retirement_ready', 'rollback_mode': 'git_revert_or_restore_from_history'})
    control_path = adopter / '.config/interfaces/external-ethos-backend.toml'
    control_path.write_text(f"""{control_path.read_text(encoding='utf-8')}\n[rollback_window]\nstate = "complete"\n""", encoding='utf-8')
    git_add_all(adopter)
    report = terminal_report(adopter, product)
    assert report['required_gaps'] == []
    assert report['ok'] is True
    assert report['state'] == 'ready'
