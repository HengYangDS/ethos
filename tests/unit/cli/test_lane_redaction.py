"""`ethos lane redact private-addresses` previews, applies and verifies, never printing a value."""

from __future__ import annotations

import hashlib
import io
import json
import sys
from typing import TYPE_CHECKING
from typing import Any

import pytest

from ethos.application import redaction
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    from pathlib import Path

# A reserved name that the owner opts in as private, so the fixture names no private-class literal.
H1 = "forge.example.invalid"
F1 = "team/infra/tools"
KEY = "ab" * 32 + "\n"
ARCHIVE = "openspec/changes/archive/2026-01-01-old"
RECORD, INDEX = f"{ARCHIVE}/design.md", f"{ARCHIVE}/index.json"
TEXT = f"origin ssh://git@{H1}:2222/{F1}.git\nproject 123456789 on port 2222\nplain line\n"
_APPLY = ("--apply", "--key-stdin")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _held(text: str) -> str:
    return json.dumps({"sha256": hashlib.sha256(text.encode()).hexdigest()}) + "\n"


def _command(lane: Path, monkeypatch: pytest.MonkeyPatch, *arguments: str, key: str = "") -> Any:
    monkeypatch.setattr(sys, "stdin", io.StringIO(key))
    args = ("lane", "redact", "private-addresses", *arguments, "--root", str(lane), "--json")
    completed = run_ethos_raw(*args, cwd=lane)
    assert completed.stdout.startswith("{"), completed.stderr
    assert H1 not in completed.stdout
    assert "123456789" not in completed.stdout
    return completed.returncode, json.loads(completed.stdout)


@pytest.fixture
def lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Provide a lane whose protected peer is named in one archived record and one other file.

    A binary and a non-UTF-8 file name it too; neither is read, so neither is counted.
    """
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    worktree = prepared_work_lane(tmp_path, name="redact").worktree
    git(worktree, "config", "remote.gitlab.url", f"ssh://git@{H1}:2222/{F1}.git")
    git(worktree, "config", "remote.gitlab.forgePrivate", "true")
    git(worktree, "config", "remote.gitlab.forgeProjectId", "123456789")
    for name, lead in (("docs/peer.bin", b"\0"), ("docs/peer.txt", b"\xff")):
        (worktree / name).parent.mkdir(parents=True, exist_ok=True)
        (worktree / name).write_bytes(lead + f" ssh://git@{H1}\n".encode())
        git(worktree, "add", name)
    commit_fixture_file(worktree, "docs/notes.md", f"see https://{H1}/{F1}\n", "docs: note a peer")
    commit_fixture_file(worktree, INDEX, _held(TEXT), "docs: index the record")
    return worktree, commit_fixture_file(worktree, RECORD, TEXT, "docs: record a peer")


def test_a_redaction_is_previewed_applied_and_verified(
    lane: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record in the roots is redacted, its digest followed and verified; others are counted."""
    worktree, base = lane
    code, preview = _command(worktree, monkeypatch)
    assert (code, preview["data"]["count"], preview["data"]["outside_roots"]) == (0, 4, 1)
    code, applied = _command(
        worktree,
        monkeypatch,
        "--apply",
        "--key-stdin",
        "--authorize",
        "--expect-head",
        base,
        key=KEY,
    )
    changed = [RECORD, INDEX]
    assert (code, applied["state"], applied["data"]["changed_paths"]) == (0, "redacted", changed)
    redacted = (worktree / RECORD).read_text(encoding="utf-8")
    assert (worktree / INDEX).read_text(encoding="utf-8") == _held(redacted)
    assert redacted.endswith("plain line\n")
    assert H1 not in redacted
    assert "123456789" not in redacted
    assert H1 in (worktree / "docs/notes.md").read_text(encoding="utf-8")
    commit_fixture_file(worktree, INDEX, _held(redacted), "docs: follow the redacted digest")
    head = commit_fixture_file(worktree, RECORD, redacted, "docs: redact a peer")
    verify = ("--verify", "--key-stdin", "--base", base, "--head", head)
    code, verified = _command(worktree, monkeypatch, *verify, key=KEY)
    assert (code, verified["state"]) == (0, "verified"), verified["required_gaps"]
    assert verified["data"]["count"] == 3
    code, rotated = _command(worktree, monkeypatch, *verify, key="cd" * 32)
    assert (code, rotated["required_gaps"]) == (1, ["redaction_key_generation_changed"])
    code, missing = _command(
        worktree, monkeypatch, "--verify", "--key-stdin", "--head", head, key=KEY
    )
    assert (missing["verdict"], missing["required_gaps"]) == ("unknown", ["redaction_base_missing"])


@pytest.mark.parametrize(
    ("arguments", "key", "gap"),
    [
        ((*_APPLY, "--expect-head", "HEAD"), KEY, "authorization_required"),
        ((*_APPLY, "--authorize", "--expect-head", "0" * 40), KEY, "expect_head_mismatch"),
        ((*_APPLY, "--authorize", "--expect-head", "HEAD"), "0" * 64, "redaction_key_invalid"),
        ((*_APPLY, "--authorize", "--expect-head", "HEAD"), KEY, "peer_occurrence_unclassified"),
    ],
)
def test_an_apply_refuses_and_writes_nothing(
    lane: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
    key: str,
    gap: str,
) -> None:
    """No authorization, a stale head, a key that cannot key or a manual mention refuses."""
    worktree, base = lane
    if gap == "peer_occurrence_unclassified":
        # An unfed path after a fed host cannot be replaced.
        base = commit_fixture_file(worktree, f"{ARCHIVE}/notes.md", f"see https://{H1}/x/y\n", "m")
        gap = f"{gap}:{ARCHIVE}/notes.md:1"
    resolved = tuple(base if word == "HEAD" else word for word in arguments)
    code, refused = _command(worktree, monkeypatch, *resolved, key=key)
    assert (code, refused["required_gaps"]) == (1, [gap])
    assert (worktree / RECORD).read_text(encoding="utf-8") == TEXT


@pytest.mark.parametrize(("roots", "outside"), [('["docs/"]', 0), ('["docs/notes.md"]', None)])
def test_record_roots_extend_the_effective_roots(
    lane: tuple[Path, str], monkeypatch: pytest.MonkeyPatch, roots: str, outside: int | None
) -> None:
    """A declared directory joins the roots; a declared file makes the profile invalid."""
    worktree, _base = lane
    profile = worktree / ".ethos/profile.toml"
    text = profile.read_text(encoding="utf-8")
    profile.write_text(text.replace("\n", f"\nrecord_roots = {roots}\n", 1), encoding="utf-8")
    code, preview = _command(worktree, monkeypatch)
    if outside is None:
        assert (code, preview["required_gaps"]) == (0, ["repository_profile_invalid"])
    else:
        assert (code, preview["data"]["outside_roots"]) == (0, outside)


def _admitted(**_arguments: object) -> dict[str, object]:
    return {"verdict": "pass", "required_gaps": []}


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("unfed", ""),
        ("dirty", "redaction_preimage_changed"),
        ("unadmitted", "openspec_requested_change_missing:absent-change"),
        ("raced", "redaction_preimage_changed"),
        ("unapplied", "redaction_postimage_mismatch"),
        ("cyclic", "redaction_digest_cycle"),
    ],
)
def test_an_apply_proves_each_step_and_never_overwrites(
    lane: tuple[Path, str], monkeypatch: pytest.MonkeyPatch, case: str, gap: str
) -> None:
    """No fed peer is unchanged; a moved preimage, a refused admission or a failed apply blocks."""
    worktree, base = lane
    edited = TEXT + "edited\n"
    if case == "unfed":
        git(worktree, "config", "--unset", "remote.gitlab.forgePrivate")
    elif case == "dirty":
        (worktree / RECORD).write_text(edited, encoding="utf-8")
    elif case == "unadmitted":
        monkeypatch.setenv("ETHOS_CHANGE", "absent-change")
    elif case == "raced":

        def racing(**arguments: object) -> dict[str, object]:
            (worktree / RECORD).write_text(edited, encoding="utf-8")
            return _admitted(**arguments)

        monkeypatch.setattr(redaction, "prewrite_guard", racing)
    elif case == "unapplied":
        monkeypatch.setattr(redaction, "prewrite_guard", _admitted)
        monkeypatch.setattr(redaction, "unified_patch", lambda _changes: "")
    else:
        # Content addresses form no cycle; a follower that always moves stands for a damaged tree.
        monkeypatch.setattr(redaction, "follow_digests", lambda text, _renamed: text + "x")
    report = redaction.redact_private_addresses(
        worktree, apply=True, key=KEY, authorize=True, expect_head=base
    )
    expected = ("unchanged", []) if not gap else ("blocked", [gap])
    assert (report["state"], report["required_gaps"]) == expected
    kept = edited if case in {"dirty", "raced"} else TEXT
    assert (worktree / RECORD).read_text(encoding="utf-8") == kept


@pytest.mark.parametrize("case", ["edited", "empty"])
def test_a_verify_refuses_a_head_its_base_does_not_derive(
    lane: tuple[Path, str], case: str
) -> None:
    """A head that edits beyond the redaction, or a base without the records, is unverified."""
    worktree, base = lane
    if case == "edited":
        head = commit_fixture_file(worktree, RECORD, TEXT.replace("plain", "edited"), "docs: edit")
    else:
        head, base = base, git(worktree, "commit-tree", EMPTY_TREE, "-m", "docs: an empty base")
    report = redaction.redact_private_addresses(
        worktree, verify=True, key=KEY, base=base, head=head
    )
    unverified = [f"redaction_unverified:{path}" for path in (RECORD, INDEX)]
    assert (report["state"], report["required_gaps"]) == ("blocked", unverified)
