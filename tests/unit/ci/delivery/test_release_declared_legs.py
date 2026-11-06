"""A release names each declared platform it does not publish, and refuses an undeclared one."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path

import pytest
import yaml

from tests.support.release_legs import VERSION
from tests.support.release_legs import qualified_leg
from tools.ci.delivery import release_assets

_ROOT = Path(__file__).resolve().parents[4]
_REQUIRED = frozenset({"linux-x64", "linux-arm64", "macos-arm64"})
_LEGS = {
    "linux-x64": ("linux", "x86_64", "linux_x86_64"),
    "linux-arm64": ("linux", "arm64", "linux_aarch64"),
    "macos-arm64": ("darwin", "arm64", "macosx_14_0_arm64"),
    "windows-x64": ("windows", "x86_64", "win_amd64"),
}
_ENTRY = f"# Changelog\n\n## [{VERSION}] - 2026-10-21\n\n### Added\n\n- Hosted release.\n"


def _assemble(tmp_path: Path, *, required=_REQUIRED, optional=frozenset({"windows-x64"})):
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    if not inputs.exists():
        changelog.write_text(_ENTRY, encoding="utf-8")
        for host, leg in _LEGS.items():
            qualified_leg(inputs, host, *leg)
    output = tmp_path / "out"
    shutil.rmtree(output, ignore_errors=True)
    options = {"tag": f"v{VERSION}", "base_url": "https://example.invalid/v"}
    release_assets.assemble(
        inputs, output, changelog=changelog, required=required, optional=optional, **options
    )
    return output


def test_an_optional_leg_that_uploaded_nothing_is_left_out_and_named(tmp_path):
    """A failed optional leg leaves no artifact; the release still names it and its rule."""
    out = _assemble(tmp_path, optional=frozenset({"windows-x64", "windows-arm64"}))
    assert json.loads((out / "left-out.json").read_text(encoding="utf-8")) == [
        {"host": "windows-arm64", "reason": "leg_incomplete"}
    ]
    notes = (out / "notes.md").read_text(encoding="utf-8")
    assert "Not published: windows-arm64." in notes
    assert "keeps its current release" in notes
    assert "windows-arm64" not in (out / f"assets/ethos-{VERSION}.mise.toml").read_text()


def test_a_release_with_every_declared_leg_names_nothing(tmp_path):
    """When every declared leg publishes, no host is left out and the notes add nothing."""
    out = _assemble(tmp_path)
    assert json.loads((out / "left-out.json").read_text(encoding="utf-8")) == []
    assert "Not published" not in (out / "notes.md").read_text(encoding="utf-8")


def test_an_artifact_of_an_undeclared_platform_refuses(tmp_path):
    """A stray or renamed leg cannot publish a platform that no release leg declares."""
    with pytest.raises(ValueError, match="release_assets_host_undeclared:windows-x64"):
        _assemble(tmp_path, optional=frozenset({"windows-arm64"}))
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    ("required", "optional"),
    [
        (frozenset(), frozenset({"windows-x64"})),
        (_REQUIRED | {"windows-x64"}, frozenset({"windows-x64"})),
        (_REQUIRED | {"solaris-x64"}, frozenset({"windows-x64"})),
    ],
    ids=["no-required", "both", "unknown"],
)
def test_invalid_declarations_refuse(tmp_path, required, optional):
    """The declared hosts are known host names, at least one required, none declared twice."""
    with pytest.raises(ValueError, match="release_assets_hosts_invalid"):
        _assemble(tmp_path, required=required, optional=optional)


def test_the_command_line_takes_the_declared_hosts():
    """The workflow passes each list once, comma-separated, as the pipeline declares it."""
    hosts = release_assets.declared_hosts("linux-arm64,linux-x64", "windows-x64,")
    assert hosts == (frozenset({"linux-arm64", "linux-x64"}), frozenset({"windows-x64"}))


def test_the_workflow_reads_one_declaration_of_the_release_legs():
    """Failure tolerance and the assembler's hosts both follow each leg's declared requirement."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    legs = jobs["release-platforms"]["strategy"]["matrix"]["include"]
    assert jobs["release-platforms"]["continue-on-error"] == "${{ !matrix.required }}"
    declared = {leg["host"]: leg["required"] for leg in legs}
    assert declared == {
        "linux-x64": True,
        "linux-arm64": True,
        "macos-arm64": True,
        "windows-x64": False,
        "windows-arm64": False,
    }
    step = next(
        step["run"]
        for step in jobs["release-publish"]["steps"]
        if "release_assets.py" in step.get("run", "")
    )
    words = shlex.split(step)
    hosts = (words[words.index("--required") + 1], words[words.index("--optional") + 1])
    required = frozenset(host for host, needed in declared.items() if needed)
    assert release_assets.declared_hosts(*hosts) == (required, frozenset(declared) - required)
