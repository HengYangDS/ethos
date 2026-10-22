"""Bounded no-follow reads refuse members that are not stable aliases."""

import os
from pathlib import Path

import pytest

import ethos.adapters.repo.content.observation as observation
from ethos.adapters.repo.content.observation import read_link_target
from ethos.adapters.repo.content.observation import read_regular_bytes
from tests.support.windows_host import with_creation_time_path_ctime
from tests.support.windows_host import without_descriptor_chain

GAPS = {"unsafe_gap": "unsafe", "unstable_gap": "unstable", "size_gap": "size"}


def test_link_target_refuses_a_directory_or_missing_member(tmp_path):
    """A directory or a missing member is unsafe input, never an alias to follow."""
    for root, relative in ((tmp_path.parent, tmp_path.name), (tmp_path, "missing")):
        with pytest.raises(ValueError, match=r"^unsafe$"):
            read_link_target(root, relative, unsafe_gap="unsafe", unstable_gap="unstable")


@pytest.mark.parametrize("descriptor_chain", [True, False])
@pytest.mark.parametrize(
    ("member", "gap"),
    [
        ("docs/member.md", ""),
        ("linked-member", "unsafe"),
        ("linked-parent", "unsafe"),
        ("docs", "unsafe"),
        ("docs/absent.md", "unsafe"),
        ("../outside/member.md", "unsafe"),
        ("oversized", "size"),
        ("rewritten", "unstable"),
    ],
)
def test_hosts_with_and_without_descriptor_chains_read_one_stable_member(
    tmp_path, monkeypatch, *, descriptor_chain, member, gap
):
    """Hosts without descriptor-relative opens bind one identity and refuse every alias."""
    if not descriptor_chain:
        without_descriptor_chain(monkeypatch)
    root, outside = tmp_path / "repository", tmp_path / "outside"
    for directory in (root / "docs", outside):
        directory.mkdir(parents=True)
        (directory / "member.md").write_bytes(b"# stable\n")
    if member == "linked-member":
        (root / "docs/member.md").unlink()
        (root / "docs/member.md").symlink_to(outside / "member.md")
    elif member == "linked-parent":
        (root / "docs/member.md").unlink()
        (root / "docs").rmdir()
        (root / "docs").symlink_to(outside, target_is_directory=True)
    elif member == "rewritten":
        fstat, rewritten = os.fstat, []

        def rewrite_once(descriptor):
            observed = fstat(descriptor)
            if not rewritten:
                rewritten.append((root / "docs/member.md").write_bytes(b"# NEW\n"))
            return observed

        monkeypatch.setattr(observation.os, "fstat", rewrite_once)
    relative = member if "/" in member or member == "docs" else "docs/member.md"
    limit = {"max_bytes": 3} if member == "oversized" else {}
    if not gap:
        assert read_regular_bytes(root, relative, **GAPS, **limit) == b"# stable\n"
        return
    with pytest.raises(ValueError, match=f"^{gap}$"):
        read_regular_bytes(root, relative, **GAPS, **limit)


def test_hosts_without_descriptor_chains_cannot_judge_native_modes(tmp_path, monkeypatch):
    """A requested mode stays a refusal where the host cannot bind the member's mode bits."""
    without_descriptor_chain(monkeypatch)
    (tmp_path / "member.py").write_bytes(b"value = 1\n")
    with pytest.raises(ValueError, match=r"^unsafe$"):
        read_regular_bytes(tmp_path, "member.py", **GAPS, expected_mode=0o644)


@pytest.mark.parametrize("descriptor_chain", [True, False])
@pytest.mark.parametrize("replaced", ["root", "parent"])
def test_a_root_or_parent_replaced_by_an_alias_never_supplies_outside_bytes(
    tmp_path, monkeypatch, *, descriptor_chain, replaced
):
    """Swapping the root while it resolves, or a parent before the open, is refused."""
    if not descriptor_chain:
        without_descriptor_chain(monkeypatch)
    root, outside = tmp_path / "repository", tmp_path / "outside"
    for directory, content in ((root, b"# stable\n"), (outside, b"# OUTSIDE\n")):
        (directory / "docs").mkdir(parents=True)
        (directory / "docs/member.md").write_bytes(content)
    if replaced == "root":
        owner, name, trigger = Path, "resolve", root
    else:
        owner = observation.os if descriptor_chain else Path
        name, trigger = "open", "member.md" if descriptor_chain else root / "docs/member.md"
    original, swapped = getattr(owner, name), root if replaced == "root" else root / "docs"

    def replace_with_alias(target, *args, **kwargs):
        if target == trigger and not swapped.is_symlink():
            swapped.rename(swapped.with_name("moved"))
            swapped.symlink_to(outside / swapped.relative_to(root), target_is_directory=True)
        return original(target, *args, **kwargs)

    monkeypatch.setattr(owner, name, replace_with_alias)
    with pytest.raises(ValueError, match=r"^unstable$"):
        read_regular_bytes(root, "docs/member.md", **GAPS)


def test_path_and_handle_stats_compare_only_the_fields_both_report(tmp_path, monkeypatch):
    """A path stat reporting creation time as st_ctime still reads its stable member."""
    without_descriptor_chain(monkeypatch)
    with_creation_time_path_ctime(monkeypatch)
    (tmp_path / "member.md").write_bytes(b"# stable\n")
    assert read_regular_bytes(tmp_path, "member.md", **GAPS) == b"# stable\n"


@pytest.mark.skipif(os.name == "nt", reason="Backslash is a path separator on Windows.")
@pytest.mark.parametrize("descriptor_chain", [True, False])
def test_posix_literal_backslash_keeps_its_native_member_identity(
    tmp_path, monkeypatch, descriptor_chain
):
    """A POSIX filename's backslash is literal, not an escape or a directory separator."""
    if not descriptor_chain:
        without_descriptor_chain(monkeypatch)
    relative = 'native "quote" \\ member.md'
    (tmp_path / relative).write_bytes(b"# stable\n")
    assert read_regular_bytes(tmp_path, relative, **GAPS) == b"# stable\n"
