"""Bounded no-follow reads refuse members that are not stable aliases."""

import pytest

from ethos.adapters.repo.content.observation import read_link_target


def test_link_target_refuses_a_directory_or_missing_member(tmp_path):
    """A directory or a missing member is unsafe input, never an alias to follow."""
    for root, relative in ((tmp_path.parent, tmp_path.name), (tmp_path, "missing")):
        with pytest.raises(ValueError, match=r"^unsafe$"):
            read_link_target(root, relative, unsafe_gap="unsafe", unstable_gap="unstable")
