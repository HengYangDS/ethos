"""Every result names the build that produced it, so an agent knows which runtime answered."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ethos.surface.cli.runtime_identity as runtime_identity
from ethos.adapters.repo.runtime.authority import committed_build_identity
from ethos.result import EthosResult
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_a_result_names_the_build_that_produced_it(tmp_path: Path) -> None:
    """The identity is the committed build, read once per invocation, never a dirty overlay."""
    repo = init_git_repo(tmp_path / "repo")

    completed = run_ethos_raw("status", "--json", cwd=repo)

    identity = committed_build_identity()
    assert json.loads(completed.stdout)["summary"]["runtime"] == {
        "product_version": identity.product_version,
        "distribution_version": identity.distribution_version,
        "source_commit": identity.source_commit,
    }


def test_a_result_renders_when_its_runtime_cannot_be_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading the build must never stop a result, such as a failed process's report, rendering."""

    def unreadable() -> None:
        raise OSError

    monkeypatch.setattr(runtime_identity, "committed_build_identity", unreadable)

    result = runtime_identity.with_runtime(
        EthosResult(command="status", verdict="pass", state="ready")
    )

    assert result.summary["runtime"] == {"unavailable": "OSError"}
