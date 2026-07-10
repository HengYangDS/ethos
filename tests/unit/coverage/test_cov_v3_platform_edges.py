# ruff: noqa: ARG005
"""Coverage-closure v3: platform-independent branches (100% no-exemption).

These two branches are reachable on some host platforms but not others, so the
darwin developer run happened to hit them while the linux CI run did not (or the
reverse), leaving the whole-repo floor at 99.98% on CI. The tests below force
each branch deterministically regardless of the host so the 100% floor holds on
every platform:

- adapters/repo/git.py `git_common_dir` line 88->90: `git rev-parse
  --git-common-dir` returns an ABSOLUTE path on linux (skipping the
  ``root / path`` join) but a RELATIVE ``.git`` on macOS. Forced here by stubbing
  ``git_stdout`` to return an absolute path.
- adapters/store/state.py `active_leases` line 260: the expired-lease ``continue``
  arc depends on wall-clock timing. Forced here with a lease acquired at a
  negative TTL so it is already expired when listed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo import git
from ethos.adapters.store.state.lease import acquire_lease
from ethos.adapters.store.state.lease import active_leases

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_git_common_dir_keeps_absolute_path_unjoined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An absolute --git-common-dir is returned as-is; the root/path join at line 89
    # is skipped (branch 88->90), which is the arc linux takes but macOS does not.
    absolute_common = tmp_path / "shared" / ".git"
    absolute_common.mkdir(parents=True)
    monkeypatch.setattr(git, "git_stdout", lambda root, *args: str(absolute_common))

    result = git.git_common_dir(tmp_path)

    assert result == absolute_common.resolve().as_posix()


def test_git_common_dir_joins_relative_path_to_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A relative --git-common-dir is joined onto root (line 89, branch 88->89), which
    # is the arc macOS takes but linux does not. Both arcs are pinned so the branch is
    # covered on every platform regardless of what the host git emits.
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(git, "git_stdout", lambda root, *args: ".git")

    result = git.git_common_dir(tmp_path)

    assert result == (tmp_path / ".git").resolve().as_posix()


def test_active_leases_skips_already_expired(tmp_path: Path) -> None:
    # A lease acquired with a negative TTL is already expired, so active_leases hits
    # the `expires_at <= now: continue` arc (line 260) and omits it.
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    acquire_lease(
        db_path,
        subject="work/expired",
        holder_ref="agent:test:case:owner",
        ttl_seconds=-10,
    )

    assert active_leases(db_path) == []


def test_active_leases_returns_live_lease(tmp_path: Path) -> None:
    # A live lease is returned, proving the skip above is selective, not blanket.
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    acquire_lease(
        db_path,
        subject="work/live",
        holder_ref="agent:test:case:owner",
        ttl_seconds=3600,
    )

    leases = active_leases(db_path)

    assert [lease["subject"] for lease in leases] == ["work/live"]
