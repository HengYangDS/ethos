"""The OpenSpec profile adapter compiles and observes intent only through its selected owner."""

import pytest

import ethos.adapters.openspec.cli as official
from ethos.adapters.openspec.profile import active_change_progress_report
from ethos.adapters.openspec.profile import load_profile_commitment
from tests.support.governed_repository import write_test_profile


def test_profile_requires_openspec_and_a_readable_official_list(tmp_path, monkeypatch):
    """Without OpenSpec nothing compiles; a missing CLI or an unreadable list blocks progress."""
    root = tmp_path / "repo"
    with pytest.raises(ValueError, match="openspec_profile_not_enabled"):
        load_profile_commitment(root)
    write_test_profile(root, openspec={"material_paths": ["openspec/**"]})
    monkeypatch.setattr(official, "openspec_base_command", lambda: None)
    assert active_change_progress_report(root)["required_gaps"] == ["openspec_official_cli_missing"]
    receipt = {"exit_code": 0, "parse_error": "", "json": {}}
    monkeypatch.setattr(official, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(official, "run_json", lambda *_args: receipt)
    assert active_change_progress_report(root)["required_gaps"] == ["openspec_list_unreadable"]
