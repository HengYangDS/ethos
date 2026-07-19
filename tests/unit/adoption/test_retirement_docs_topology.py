# ruff: noqa: I001 - compact source-budget projection preserves the exact test AST.
# fmt: off

from __future__ import annotations
from typing import TYPE_CHECKING
from tests.unit.adoption.retirement.fixtures import git_add_all
from tests.unit.adoption.retirement.fixtures import prepare_terminal_profile
from tests.unit.adoption.retirement.fixtures import terminal_report
if TYPE_CHECKING:
    from pathlib import Path

def test_retirement_readiness_accepts_adopter_declared_compatibility_docs_roots(tmp_path: Path) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    profile = adopter / '.ethos/profile.toml'
    profile.write_text(profile.read_text(encoding='utf-8') + '\n[docs_topology]\nstate_root_policy = "adopter_declared_compatibility"\ntime_state_roots = ["docs/current", "docs/future"]\ncompatibility_decision = "docs/reference/documentation-information-architecture.md"\n', encoding='utf-8')
    (adopter / 'docs/current').mkdir(parents=True)
    (adopter / 'docs/future').mkdir(parents=True)
    (adopter / 'docs/reference/documentation-information-architecture.md').write_text('---\nstate: canonical\nrole: reference\n---\n# Adopter IA\n', encoding='utf-8')
    git_add_all(adopter)
    report = terminal_report(adopter, product)
    assert report['ok'] is True
    assert report['required_gaps'] == []
    assert report['checks']['docs_topology']['ok'] is True
    assert report['checks']['docs_topology']['profile_policy']['state_root_policy'] == 'adopter_declared_compatibility'
    assert report['checks']['docs_topology']['time_state_roots'] == ['docs/current', 'docs/future']

def test_retirement_readiness_accepts_profile_mapped_legacy_status_lines(tmp_path: Path) -> None:
    adopter, product = prepare_terminal_profile(tmp_path)
    for path in [adopter / 'docs/README.md', adopter / 'docs/reference/README.md', adopter / 'docs/evidence/README.md', adopter / 'docs/history/README.md', adopter / 'docs/decisions/README.md', adopter / 'docs/decisions/decision-index.md', adopter / 'docs/decisions/decision-dependency-map.md', adopter / 'docs/decisions/decision-code-links.md', adopter / 'docs/decisions/accepted/README.md', adopter / 'docs/decisions/superseded/README.md', adopter / 'docs/decisions/templates/README.md', adopter / 'docs/decisions/templates/decision-record.md']:
        status = 'reference' if path.name == 'decision-record.md' else 'index'
        path.write_text(f'# {path.name}\n\nStatus: {status}\n', encoding='utf-8')
    profile = adopter / '.ethos/profile.toml'
    profile.write_text(profile.read_text(encoding='utf-8') + '\n[docs_topology]\nstate_metadata_policy = "front_matter_or_status_line"\nstatus_field = "Status"\ncompatibility_decision = "docs/reference/documentation-information-architecture.md"\n\n[docs_topology.state_value_map]\nindex = "canonical"\nreference = "canonical"\n', encoding='utf-8')
    (adopter / 'docs/reference/documentation-information-architecture.md').write_text('---\nstate: canonical\nrole: reference\n---\n# Adopter IA\n', encoding='utf-8')
    git_add_all(adopter)
    report = terminal_report(adopter, product)
    assert report['ok'] is True
    assert report['required_gaps'] == []
    assert report['checks']['docs_topology']['profile_policy']['state_metadata_policy'] == 'front_matter_or_status_line'
