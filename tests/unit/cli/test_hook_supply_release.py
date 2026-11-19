"""`ethos hook retire-supply --release-absent` previews and releases absent consumers."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

import pytest

from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo


def _case(tmp_path: Path) -> tuple[tuple[str, ...], Path, Path]:
    """Return the preview's words, an installation and the absent consumer that recorded it."""
    store = Path(os.environ["XDG_DATA_HOME"]).resolve() / "ethos/installations"
    installation = store / ("9" * 16)
    (installation / "runtime").mkdir(parents=True)
    (installation / "runtime/payload").write_bytes(b"x" * 2048)
    consumer = (tmp_path / "gone/.git").resolve()
    record_consumer(installation, consumer)
    repository = init_git_repo(tmp_path / "projects/repository")
    words = ("hook", "retire-supply", "--scan", str(tmp_path / "projects"))
    return (*words, "--root", str(repository), "--json"), installation, consumer


def test_the_preview_names_the_absent_consumer_and_the_release_frees_its_record(
    tmp_path: Path,
) -> None:
    """The previewed command unlinks the record, keeps the installation and names the cleanup."""
    words, installation, consumer = _case(tmp_path)

    preview = run_ethos(*words, "--release-absent")

    (row,) = preview["data"]["absent"]
    assert (row["installation"], row["consumer"]) == (installation.as_posix(), consumer.as_posix())
    assert (preview["verdict"], preview["state"]) == ("pass", "planned")
    assert preview["user_decision_required"] is True
    assert preview["summary"]["absent"] == 1
    assert preview["summary"]["held_bytes"] >= 2048
    assert installation_consumers(installation) != {}
    approve = shlex.split(preview["next_action"])
    assert {"--release-absent", "--expect-plan", "--apply", "--authorize"} <= set(approve)

    applied = run_ethos(*approve[1:])

    assert (applied["verdict"], applied["state"]) == ("pass", "released")
    assert applied["data"]["released"] == [consumer.as_posix()]
    assert applied["summary"]["released"] == 1
    assert installation_consumers(installation) == {}
    assert (installation / "runtime/payload").is_file()
    assert shlex.split(applied["next_action"])[:3] == ["ethos", "hook", "install"]


@pytest.mark.parametrize(
    ("dropped", "gap"),
    [("--authorize", "authorization_required"), ("--expect-plan", "host_store_plan_required")],
)
def test_a_release_without_its_plan_or_its_authorization_unlinks_nothing(
    tmp_path: Path, dropped: str, gap: str
) -> None:
    words, installation, consumer = _case(tmp_path)
    plan = ("--expect-plan", "0" * 64) if dropped == "--authorize" else ()
    tokens = tuple(token for token in ("--apply", "--authorize") if token != dropped)

    refused = run_ethos_blocked(*words, "--release-absent", *plan, *tokens)

    assert refused["required_gaps"] == [gap]
    assert list((installation_consumers(installation) or {}).values()) == [consumer]


def test_a_release_that_fails_in_the_middle_names_what_it_released(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The result is the only account of a released record, so a later failure keeps the list."""
    words, installation, _consumer = _case(tmp_path)
    record_consumer(installation, (tmp_path / "also-gone/.git").resolve())
    approve = shlex.split(run_ethos(*words, "--release-absent")["next_action"])
    unlink = Path.unlink
    _first, denied = sorted(installation_consumers(installation) or {})

    def fail_the_second_record(path: Path, *, missing_ok: bool = False) -> None:
        if path == denied:
            raise PermissionError(13, "denied")
        unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_the_second_record)

    refused = run_ethos_blocked(*approve[1:])

    assert refused["required_gaps"] == ["PermissionError: [Errno 13] denied"]
    assert (len(refused["data"]["released"]), refused["summary"]["released"]) == (1, 1)
    assert list(installation_consumers(installation) or {}) == [denied]
    assert shlex.split(refused["next_action"])[:3] == ["ethos", "hook", "install"]


def test_without_the_switch_no_consumer_record_is_planned(tmp_path: Path) -> None:
    """The plan of installations is the one of the release before, and names no consumer."""
    words, installation, consumer = _case(tmp_path)

    preview = run_ethos(*words)

    assert "absent" not in preview["data"]
    assert preview["data"]["retirable"] == []
    assert set(preview["summary"]) >= {"retirable", "kept", "retired", "retirable_bytes"}
    assert list((installation_consumers(installation) or {}).values()) == [consumer]
