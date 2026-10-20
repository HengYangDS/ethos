"""Bounded no-follow reads refuse members that are not stable aliases."""

import os

import pytest

import ethos.adapters.repo.content.observation as observation
from ethos.adapters.repo.content.observation import read_link_target
from ethos.adapters.repo.content.observation import read_regular_bytes
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
                rewritten.append((root / "docs/member.md").write_bytes(b"# CHANGE\n"))
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
