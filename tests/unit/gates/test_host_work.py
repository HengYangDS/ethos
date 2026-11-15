"""A holder of a host ticket marks the scratch root it makes with its owner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.host_admission as host_admission
import ethos.adapters.gates.host_work as host_work
import ethos.adapters.gates.python_quality as python_quality
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from pathlib import Path

_ACTOR = "agent:test:case:agent-test"
_PROJECT = {
    "src/app.py": "answer = 42\n",
    "tests/test_app.py": "def test_answer(): assert True\n",
    "pyproject.toml": "[project]\nname = 'sample'\nversion = '0.1.0'\n",
    "uv.lock": "version = 1\n",
}


@pytest.mark.parametrize(
    ("ticket", "actor", "owner"),
    [
        (True, _ACTOR, _ACTOR),  # a ticket's holder that declares its actor: the root is marked
        (False, _ACTOR, ""),  # no ticket: the probe's scratch is not a ticket's work
        (True, "", ""),  # no declared actor: the owner stays unknown
    ],
)
def test_the_behavior_probes_scratch_root_carries_its_ticket_holders_mark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, actor: str, owner: str, *, ticket: bool
) -> None:
    """The root that holds a proof's test environment names its owner while the tests run."""
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    repo = committed_source_repo(tmp_path, _PROJECT)
    seen: list[tuple[Path, str, bool]] = []

    def evidence(_root: Path, *, output: Path, **_scope: object) -> dict[str, object]:
        seen.append((output, host_work.work_owner(output), (output / host_work.MARK).exists()))
        return {"verdict": "block", "required_gaps": ["observed"]}

    monkeypatch.setattr(python_quality, "_behavior_evidence", evidence)
    with (
        host_admission.admitted_host_work(repo, "ethos prove", operation="proof.run") as work,
        host_admission.exported(work.environment if ticket else {}),
    ):
        report = python_quality.behavior_report(repo)

    ((root, marked, exists),) = seen
    assert (report["required_gaps"], marked, exists) == (["observed"], owner, bool(owner))
    # The mark ends with the scratch it names.
    assert not root.exists()
