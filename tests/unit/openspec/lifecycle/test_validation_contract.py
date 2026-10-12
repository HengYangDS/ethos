"""Complete native OpenSpec reports retain identity, findings and caller scope."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as cli
from ethos.adapters.openspec.lifecycle.validation import validation_result_gaps

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def native_validation(tmp_path: Path) -> tuple[Path, tuple[str, ...], dict[str, object]]:
    """Read an original producer, not a private reconstructed report schema."""
    root = tmp_path / "native root"
    spec = root / "openspec/specs/contracts/spec.md"
    spec.parent.mkdir(parents=True)
    (root / "openspec/config.yaml").write_text("schema: spec-driven\n")
    spec.write_text(
        "# Contracts Specification\n\n## Purpose\n\n"
        "Retain native report acceptance and complete findings.\n\n## Requirements\n\n"
        "### Requirement: Complete report\n\nThe system SHALL preserve native findings.\n\n"
        "#### Scenario: Reader observes the report\n\n"
        "- **WHEN** validation runs\n- **THEN** the report retains its complete meaning\n"
    )
    command = cli.openspec_base_command()
    assert command is not None
    observed = cli.run_json(root, command, ("validate", "--all", "--strict", "--json"))
    assert observed["exit_code"] == 0, observed
    assert validation_result_gaps(observed) == []
    return root, command, observed


@pytest.mark.parametrize("coordinate", ["root", "totals", "duplicate", "issues"])
def test_native_validation_rejects_incomplete_or_misattributed_reports(
    native_validation, monkeypatch: pytest.MonkeyPatch, coordinate: str
) -> None:
    """Each originally admitted defect is rejected through the actual native caller."""
    root, command, original = native_validation
    payload = deepcopy(original["json"])
    if coordinate == "root":
        payload["root"]["path"] = str(root.parent / "another root")
    elif coordinate == "totals":
        payload["summary"]["totals"]["items"] = 999
    elif coordinate == "duplicate":
        payload["items"].append(deepcopy(payload["items"][0]))
        for counts in (payload["summary"]["totals"], payload["summary"]["byType"]["spec"]):
            counts.update(items=2, passed=2)
    else:
        del payload["items"][0]["issues"]
    output = json.dumps(payload)
    monkeypatch.setattr(
        cli, "_run_official", lambda *_a, **_k: subprocess.CompletedProcess(command, 0, output, "")
    )

    result = cli.run_json(root, command, ("validate", "--all", "--strict", "--json"))

    assert validation_result_gaps(result), coordinate
    assert result["stdout"] == output
    assert result["stderr"] == ""
    assert original["json"]["summary"]["totals"]["items"] == 1


def test_native_validation_accepts_equivalent_paths_and_forward_metadata(
    native_validation, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native path equivalence and additive producer fields preserve admission."""
    root, command, original = native_validation
    alias = root.parent / "native alias"
    alias.symlink_to(root, target_is_directory=True)
    payload = deepcopy(original["json"])
    payload["root"]["path"] = str(alias)
    payload["producerMetadata"] = {"extension": "forward-compatible"}
    output = json.dumps(payload)
    monkeypatch.setattr(
        cli, "_run_official", lambda *_a, **_k: subprocess.CompletedProcess(command, 0, output, "")
    )

    result = cli.run_json(root, command, ("validate", "--all", "--strict", "--json"))

    assert validation_result_gaps(result) == []
    assert result["stdout"] == output


def test_native_validation_preserves_distinct_complete_findings(native_validation) -> None:
    """The original findings report is not mistaken for a partial full report."""
    root, command, _original = native_validation

    result = cli.run_json(
        root, command, ("validate", "--all", "--strict", "--report", "findings", "--json")
    )

    assert validation_result_gaps(result) == []
    assert result["json"]["report"]["returnedItems"] == 0
    assert result["json"]["report"]["totalItems"] == 1
    assert result["json"]["itemFindings"] == []
