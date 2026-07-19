"""Coverage-closure v3: registrymisc reachable branches (100% no-exemption)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos_core.contracts.system.contracts as system_contracts
from ethos.repository import context
from ethos.repository.registry import commands
from ethos.repository.registry.docs.links import stable_paths_report
from ethos.repository.release import core as release_core
from ethos_core.contracts import rules

if TYPE_CHECKING:
    from pathlib import Path


def test_scan_retired_prefixes_skips_single_token_fenced_line(tmp_path: Path) -> None:
    # A fenced line with exactly one token gives len(tokens) < 2 -> commands.py 175->179
    # (skip the two-token prefix build) rather than 175->176.
    (tmp_path / "README.md").write_text("# Doc\n\n```bash\nethos\n```\n", encoding="utf-8")

    assert commands._scan_retired_public_command_prefixes(tmp_path) == []


def test_stable_paths_report_without_config_file(tmp_path: Path) -> None:
    # No docs/_meta/stable_paths.toml -> docs.py 347->357 skips the exists() block, configured empty.
    report = stable_paths_report(tmp_path)

    assert report["ok"] is False
    assert report["configured"] == []


def test_rule_attestation_gaps_skips_facts_when_not_dict() -> None:
    # input_snapshot is a dict but its 'facts' is absent (None) -> rules.py 267 isinstance False -> 267->274.
    gaps = rules.rule_attestation_gaps({"input": {"digest": "x"}}, {})

    assert "rule_attestation_output_missing" in gaps


def test_system_contracts_report_contract_without_schema_ref(tmp_path: Path) -> None:
    # A valid contract lacking a 'schema' key -> system/contracts.py 83 isinstance False -> 83->69 loop back.
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "authority.toml").write_text('title = "authority"\n', encoding="utf-8")

    report = system_contracts.system_contracts_report(tmp_path)

    assert report["contracts"]["authority"] is True


def test_authority_order_returns_empty_when_order_not_list(tmp_path: Path) -> None:
    # authority.toml present but 'order' is a string, not a list -> context.py 24 True -> line 25 return ().
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "authority.toml").write_text('order = "flat"\n', encoding="utf-8")

    assert context._authority_order(tmp_path) == ()


def test_release_config_missing_file_returns_empty(tmp_path: Path) -> None:
    # No .ethos/release.toml -> release/core.py line 28 return {}.
    assert release_core.release_config(tmp_path) == {}
