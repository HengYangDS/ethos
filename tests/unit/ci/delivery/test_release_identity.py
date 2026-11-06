"""Release assembly admits only the bytes that the tagged commit built at the tag's version."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.support.release_legs import HEAD
from tests.support.release_legs import VERSION
from tests.support.release_legs import qualified_leg
from tools.ci.delivery import release_assets

_ROOT = Path(__file__).resolve().parents[4]
_LEGS = {
    "linux-x64": ("linux", "x86_64", "linux_x86_64"),
    "linux-arm64": ("linux", "arm64", "linux_aarch64"),
    "macos-arm64": ("darwin", "arm64", "macosx_14_0_arm64"),
}
_ENTRY = f"# Changelog\n\n## [{VERSION}] - 2026-10-21\n\n### Added\n\n- Hosted release.\n"


def _assemble(tmp_path: Path, *, expect_head: str = HEAD, change=None):
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    changelog.write_text(_ENTRY, encoding="utf-8")
    for host, leg in _LEGS.items():
        qualified_leg(inputs, host, *leg)
    if change is not None:
        evidence = inputs / "release-runtime-linux-x64/evidence/local-install/release-smoke.json"
        record = json.loads(evidence.read_text(encoding="utf-8"))
        record["distribution"].update(change)
        evidence.write_text(json.dumps(record), encoding="utf-8")
    return release_assets.assemble(
        inputs,
        tmp_path / "out",
        tag=f"v{VERSION}",
        base_url="https://example.invalid/v",
        changelog=changelog,
        required=frozenset(_LEGS),
        optional=frozenset(),
        expect_head=expect_head,
    )


def test_legs_built_from_the_tagged_commit_are_admitted(tmp_path):
    """Every leg records the release head and the tag's distribution version."""
    assert f"ethos-{VERSION}-linux-x64.tar.gz" in _assemble(tmp_path)


@pytest.mark.parametrize(
    "change",
    [{"source_commit": "f" * 40}, {"distribution_version": "0.2.0a5.dev0"}],
    ids=["another-commit", "another-version"],
)
def test_a_leg_with_another_identity_refuses(tmp_path, change):
    """A leg from another commit, or at another version, stops the release and names its host."""
    with pytest.raises(ValueError, match="release_assets_identity_mismatch:linux-x64"):
        _assemble(tmp_path, change=change)
    assert not (tmp_path / "out").exists()


def test_an_invalid_release_head_refuses(tmp_path):
    """The expected head is a full commit ID, never a prefix or a ref."""
    with pytest.raises(ValueError, match="release_assets_head_invalid"):
        _assemble(tmp_path, expect_head="main")


def test_the_tag_maps_to_its_distribution_version():
    """The tag's prerelease stage maps to the PEP 440 form that the build records."""
    assert release_assets.distribution_version("0.2.0-alpha.5") == "0.2.0a5"
    assert release_assets.distribution_version("0.2.0-beta.4") == "0.2.0b4"
    assert release_assets.distribution_version("1.0.0-rc.2") == "1.0.0rc2"


def test_the_publish_step_passes_the_release_head():
    """The workflow hands the assembler the head that every release leg verified."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    run = next(
        step["run"]
        for step in jobs["release-publish"]["steps"]
        if "release_assets.py" in step.get("run", "")
    )
    assert "--expect-head ${{ inputs.release_head }}" in run
