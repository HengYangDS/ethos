"""A release publishes every declared platform and refuses an undeclared one."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
import yaml

from tests.support.release_legs import HOSTS
from tests.support.release_legs import assemble_release
from tools.ci.delivery import release_assets

_ROOT = Path(__file__).resolve().parents[4]


def test_an_artifact_of_an_undeclared_platform_refuses(tmp_path):
    """A stray or renamed leg cannot publish a platform that no release leg declares."""
    with pytest.raises(ValueError, match="release_assets_host_undeclared:macos-arm64"):
        assemble_release(tmp_path, hosts=HOSTS - {"macos-arm64"})
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("hosts", [frozenset(), HOSTS | {"solaris-x64"}], ids=["none", "unknown"])
def test_invalid_declarations_refuse(tmp_path, hosts):
    """The declared hosts are known host names, and at least one."""
    with pytest.raises(ValueError, match="release_assets_hosts_invalid"):
        assemble_release(tmp_path, hosts=hosts)


def test_the_command_line_takes_the_declared_hosts():
    """The workflow passes the list once, comma-separated, as the pipeline declares it."""
    hosts = release_assets.declared_hosts("linux-arm64,linux-x64,")
    assert hosts == frozenset({"linux-arm64", "linux-x64"})


def test_the_workflow_reads_one_declaration_of_the_release_legs():
    """No leg tolerates a failure, and the assembler's hosts are the legs that the matrix runs."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    legs = jobs["release-platforms"]["strategy"]["matrix"]["include"]
    assert "continue-on-error" not in jobs["release-platforms"]
    declared = frozenset(leg["host"] for leg in legs)
    assert declared == HOSTS
    step = next(
        step["run"]
        for step in jobs["release-publish"]["steps"]
        if "release_assets.py" in step.get("run", "")
    )
    assert "--expect-head ${{ inputs.release_head }}" in step
    words = shlex.split(step)
    assert release_assets.declared_hosts(words[words.index("--hosts") + 1]) == declared
