"""A holder of a host ticket marks the scratch root it makes with its owner."""

from __future__ import annotations

import errno
import os
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.host_admission as host_admission
import ethos.adapters.gates.host_work as host_work
import ethos.adapters.gates.python_quality as python_quality
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

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


def _refused(*_arguments: object, **_options: object) -> None:
    raise PermissionError


def _interrupted(*_arguments: object, **_options: object) -> None:
    raise KeyboardInterrupt


def _torn(path: Path, _text: str, **_options: object) -> None:
    """Create the file and fail before its record is whole, as a full disk does."""
    path.touch()
    raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


def _claim(root: Path, _directory: Path) -> None:
    host_work.claim_work_directory(root, "render", owner=_ACTOR, operation="host.run")


def _scratch(_root: Path, directory: Path) -> None:
    host_work.mark_ticket_scratch(directory, operation="provider.python-behavior")


_UNAVAILABLE = "^host_work_unavailable$"


_BOTH = [".json", ".partial"]


@pytest.mark.parametrize(
    ("mark", "write", "link", "unlink", "ends", "left"),
    [
        # A record that is not written whole leaves no file behind the refusal.
        (_claim, _torn, None, None, pytest.raises(ValueError, match=_UNAVAILABLE), []),
        # A file system that links no file refuses the claim, which its repair names.
        (_claim, None, _refused, None, pytest.raises(ValueError, match=_UNAVAILABLE), []),
        # A partial that cannot be removed never replaces the exit in flight, for either caller.
        (_claim, None, _interrupted, _refused, pytest.raises(KeyboardInterrupt), [".partial"]),
        (_scratch, None, _interrupted, _refused, pytest.raises(KeyboardInterrupt), [".partial"]),
        # After a whole write and link, a partial that cannot be removed refuses the claim.
        (_claim, None, None, _refused, pytest.raises(ValueError, match=_UNAVAILABLE), _BOTH),
        # A scratch mark never fails the work, so there the same error is dropped.
        (_scratch, None, None, _refused, nullcontext(), _BOTH),
    ],
)
def test_a_partial_record_is_removed_and_never_decides_how_a_mark_ends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mark: Callable[[Path, Path], None],
    write: Callable[..., None] | None,
    link: Callable[..., None] | None,
    unlink: Callable[..., None] | None,
    ends: AbstractContextManager[object],
    left: list[str],
) -> None:
    """A torn write leaves no partial; one that stays replaces no exit that is in flight."""
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    monkeypatch.setenv(host_admission.ADMISSION_ENV, "a-ticket")
    directory = tmp_path / host_work.WORK_HOME / "render"
    directory.mkdir(parents=True)
    fakes = ((Path, "write_text", write), (os, "link", link), (Path, "unlink", unlink))

    with pytest.MonkeyPatch.context() as patch, ends:
        for owner, name, fake in fakes:
            if fake is not None:
                patch.setattr(owner, name, fake)
        mark(tmp_path, directory)

    assert sorted(path.suffix for path in directory.iterdir()) == left
    assert host_work.work_owner(directory) == (_ACTOR if ".json" in left else "")
