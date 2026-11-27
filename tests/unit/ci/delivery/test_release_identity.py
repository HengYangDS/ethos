"""Release assembly admits only the bytes that the tagged commit built at the tag's version."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.support.release_legs import VERSION
from tests.support.release_legs import assemble_release
from tools.ci.delivery import release_assets

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _restamp(change: dict[str, str]) -> Callable[[Path, str], None]:
    """Rewrite a leg's smoke record as a build of another identity would have written it."""

    def apply(job: Path, _host: str) -> None:
        evidence = job / "evidence/local-install/release-smoke.json"
        record = json.loads(evidence.read_text(encoding="utf-8"))
        record["distribution"].update(change)
        evidence.write_text(json.dumps(record), encoding="utf-8")

    return apply


def test_legs_built_from_the_tagged_commit_are_admitted(tmp_path):
    """Every leg records the release head and the tag's distribution version."""
    assert f"ethos-{VERSION}-linux-x64.tar.gz" in assemble_release(tmp_path)[1]


@pytest.mark.parametrize(
    "change",
    [{"source_commit": "f" * 40}, {"distribution_version": "0.2.0a5.dev0"}],
    ids=["another-commit", "another-version"],
)
def test_a_leg_with_another_identity_refuses(tmp_path, change):
    """A leg from another commit, or at another version, stops the release and names its host."""
    with pytest.raises(ValueError, match="release_assets_identity_mismatch:linux-x64"):
        assemble_release(tmp_path, alter=_restamp(change))
    assert not (tmp_path / "out").exists()


def test_an_invalid_release_head_refuses(tmp_path):
    """The expected head is a full commit ID, never a prefix or a ref."""
    with pytest.raises(ValueError, match="release_assets_head_invalid"):
        assemble_release(tmp_path, expect_head="main")


def test_the_tag_maps_to_its_distribution_version():
    """The tag's prerelease stage maps to the PEP 440 form that the build records."""
    assert release_assets.distribution_version("0.2.0-alpha.5") == "0.2.0a5"
    assert release_assets.distribution_version("0.2.0-beta.4") == "0.2.0b4"
    assert release_assets.distribution_version("1.0.0-rc.2") == "1.0.0rc2"
