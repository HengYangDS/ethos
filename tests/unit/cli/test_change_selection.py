"""An explicit `--change` binds one invocation over the inherited `ETHOS_CHANGE`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import result_data
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import write_active_commitment

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

TASKS = "openspec/changes/fixture-change/tasks.md"


def test_prewrite_and_status_serve_the_explicit_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With two active Changes, the option wins over the environment and does not persist."""
    work = prepared_work_lane(tmp_path).worktree
    write_active_commitment(work, change_id="second-local")
    commit_fixture(work, "docs(openspec): declare second-local")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "second-local")
    prewrite = ("lane", "prewrite", TASKS, "--editor-root", str(work), "--require-editor-root")

    inherited = run_ethos_blocked(*prewrite, "--json", cwd=work)
    selected = run_ethos(*prewrite, "--change", "fixture-change", "--json", cwd=work)

    assert f"openspec_change_path_mismatch:second-local:{TASKS}" in inherited["required_gaps"]
    assert selected["verdict"] == "pass", selected["required_gaps"]
    (work / TASKS).write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    observed = {
        choice: {
            item["path"]: (item["state"], item.get("change_id"))
            for item in result_data(run_ethos("status", *choice, "--json", cwd=work))[
                "path_attributions"
            ]
        }[TASKS]
        for choice in ((), ("--change", "fixture-change"))
    }
    assert observed == {
        (): ("observed", "second-local"),
        ("--change", "fixture-change"): ("observed", "fixture-change"),
    }
