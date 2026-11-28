"""Bounded no-follow reads refuse members that are not stable aliases."""

import os
from pathlib import Path

import pytest

import ethos.adapters.repo.content.observation as observation
from ethos.adapters.repo.content.observation import read_link_target
from ethos.adapters.repo.content.observation import read_regular_bytes

GAPS = {"unsafe_gap": "unsafe", "unstable_gap": "unstable", "size_gap": "size"}


def test_link_target_refuses_a_directory_or_missing_member(tmp_path):
    """A directory or a missing member is unsafe input, never an alias to follow."""
    for root, relative in ((tmp_path.parent, tmp_path.name), (tmp_path, "missing")):
        with pytest.raises(ValueError, match=r"^unsafe$"):
            read_link_target(root, relative, unsafe_gap="unsafe", unstable_gap="unstable")


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
def test_a_descriptor_chain_reads_one_stable_member(tmp_path, monkeypatch, *, member, gap):
    """A read binds one member's identity and refuses every alias."""
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


@pytest.mark.parametrize("replaced", ["root", "parent"])
def test_a_root_or_parent_replaced_by_an_alias_never_supplies_outside_bytes(
    tmp_path, monkeypatch, *, replaced
):
    """Swapping the root while it resolves, or a parent before the open, is refused."""
    root, outside = tmp_path / "repository", tmp_path / "outside"
    for directory, content in ((root, b"# stable\n"), (outside, b"# OUTSIDE\n")):
        (directory / "docs").mkdir(parents=True)
        (directory / "docs/member.md").write_bytes(content)
    if replaced == "root":
        owner, name, trigger = Path, "resolve", root
    else:
        owner, name, trigger = observation.os, "open", "member.md"
    original, swapped = getattr(owner, name), root if replaced == "root" else root / "docs"

    def replace_with_alias(target, *args, **kwargs):
        if target == trigger and not swapped.is_symlink():
            swapped.rename(swapped.with_name("moved"))
            swapped.symlink_to(outside / swapped.relative_to(root), target_is_directory=True)
        return original(target, *args, **kwargs)

    monkeypatch.setattr(owner, name, replace_with_alias)
    with pytest.raises(ValueError, match=r"^unstable$"):
        read_regular_bytes(root, "docs/member.md", **GAPS)


def test_posix_literal_backslash_keeps_its_native_member_identity(tmp_path):
    """A POSIX filename's backslash is literal, not an escape or a directory separator."""
    relative = 'native "quote" \\ member.md'
    (tmp_path / relative).write_bytes(b"# stable\n")
    assert read_regular_bytes(tmp_path, relative, **GAPS) == b"# stable\n"
