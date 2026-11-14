"""A hosted release is admitted by its signed tag and published from the archives it qualified."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.support.fixture_signer import configure_fixture_signer
from tests.support.release_legs import HEAD
from tests.support.release_legs import qualified_leg
from tools.ci.delivery import pipeline
from tools.ci.delivery import release_assets

_ROOT = Path(__file__).resolve().parents[4]

_TAG = "v0.2.0-alpha.5"
_ENTRY = "## [0.2.0-alpha.5] - 2026-10-21\n\n### Added\n\n- Hosted release.\n"
_CHANGELOG = f"# Changelog\n\n## [Unreleased]\n\n{_ENTRY}\n## [0.2.0-alpha.2] - 2026-08-30\n\n"
_CHANGELOG += "### Changed\n\n- Earlier.\n"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(("git", *args), cwd=repo, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _release_repository(tmp_path: Path, *, entry: bool = True) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    configure_fixture_signer(repo)
    _git(repo, "config", "user.name", "ETHOS Test")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "VERSION").write_text("0.2.0-alpha.5\n", encoding="ascii")
    changelog = _CHANGELOG if entry else "# Changelog\n\n## [Unreleased]\n"
    (repo / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "release source")
    return repo, _git(repo, "rev-parse", "HEAD")


def _unproven(*_args) -> None:
    pytest.fail("a hosted release consulted the local repository proof")


def test_hosted_release_source_is_admitted_by_its_trusted_signed_tag(tmp_path, monkeypatch):
    """A runner holds no repository proof: the tag `land --release` signed carries it."""
    repo, head = _release_repository(tmp_path)
    monkeypatch.setattr(pipeline, "accepted_release_source", _unproven)
    monkeypatch.setattr(pipeline, "proof_for_repository_transition", _unproven)
    _git(repo, "tag", "-s", "-m", f"Release {_TAG}", _TAG)
    with pipeline.release_build_source(repo, tmp_path / "work", head=head, tag=_TAG) as prepared:
        carried = pipeline.build_input_identity(prepared)
    assert (carried.distribution_version, carried.source_commit) == ("0.2.0a5", head)
    arguments = ("--release", "--expect-head", head, "--tag", _TAG)
    assert (pipeline.release_build_head(arguments), pipeline.release_build_tag(arguments)) == (
        head,
        _TAG,
    )
    assert pipeline.release_build_tag(arguments[:3]) == ""
    for invalid in (arguments[:1] + arguments[3:], (*arguments[:4], "0.2.0"), (*arguments, "-x")):
        with pytest.raises(ValueError, match="release_build_arguments_invalid"):
            pipeline.release_build_tag(invalid)


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("unsigned", "release_tag_source_untrusted"),
        ("elsewhere", "release_tag_source_untrusted"),
        ("version", "release_tag_version_mismatch"),
        ("entry", "release_changelog_target_missing:0.2.0-alpha.5"),
    ],
)
def test_hosted_release_source_refuses_every_other_tag(tmp_path, monkeypatch, case, gap):
    """Unsigned, misplaced or mismatched tags admit nothing before any build effect."""
    repo, head = _release_repository(tmp_path, entry=case != "entry")
    monkeypatch.setattr(pipeline, "proof_for_repository_transition", _unproven)
    tag = "v0.2.0-alpha.6" if case == "version" else _TAG
    _git(repo, "tag", "-a" if case == "unsigned" else "-s", "-m", f"Release {tag}", tag)
    if case == "elsewhere":
        _git(repo, "commit", "--quiet", "--allow-empty", "-m", "later source")
        head = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match=gap):
        pipeline.prepare_release_candidate(repo, head, tag=tag)


_SUFFIXES = (".tar.gz", ".spdx.json", ".syft.json")
_NATIVE = {
    "linux-x64": ("linux", "x86_64", "linux_x86_64"),
    "linux-arm64": ("linux", "arm64", "linux_aarch64"),
    "macos-arm64": ("darwin", "arm64", "macosx_14_0_arm64"),
    "windows-x64": ("windows", "x86_64", "win_amd64"),
}


def _options(changelog: Path, *, optional: set[str]) -> dict:
    return {
        "tag": _TAG,
        "base_url": "https://example.invalid/v",
        "changelog": changelog,
        "required": frozenset({"linux-x64", "linux-arm64", "macos-arm64"}),
        "optional": frozenset(optional),
        "expect_head": HEAD,
    }


def test_release_assets_publish_only_the_qualified_bytes(tmp_path):
    """Each platform publishes the wheel it built and the archive its smoke qualified.

    Windows is optional: its qualified leg publishes, and its absence leaves the others.
    """
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG, encoding="utf-8")
    qualified = {host: qualified_leg(inputs, host, *leg) for host, leg in _NATIVE.items()}
    options = _options(changelog, optional={"windows-x64"})
    unreleased = tmp_path / "UNRELEASED.md"
    unreleased.write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    for change, gap in (
        ({"tag": "v0.2.0"}, "release_assets_prerelease_required"),
        ({"changelog": unreleased}, "release_assets_changelog_entry_missing:0.2.0-alpha.5"),
    ):
        with pytest.raises(ValueError, match=gap):
            release_assets.assemble(inputs, tmp_path / "refused", **(options | change))
    for tampered in qualified["windows-x64"]:
        original = tampered.read_bytes()
        tampered.write_bytes(b"changed")
        with pytest.raises(ValueError, match="release_assets_distribution_mismatch:windows-x64"):
            release_assets.assemble(inputs, tmp_path / "refused", **options)
        tampered.write_bytes(original)
    assert not (tmp_path / "refused").exists()
    sums = release_assets.assemble(inputs, tmp_path / "out", **options)
    assets = tmp_path / "out/assets"
    published = {f"ethos-0.2.0-alpha.5-{host}{suffix}" for host in _NATIVE for suffix in _SUFFIXES}
    wheels = {f"ethos-0.2.0a5-py3-none-{leg[2]}.whl" for leg in _NATIVE.values()}
    expected = {"SHA256SUMS", "ethos-0.2.0-alpha.5.mise.toml", *published, *wheels}
    assert {path.name for path in assets.iterdir()} == expected
    wheel = hashlib.sha256(b"wheel linux-x64").hexdigest()
    assert sums["ethos-0.2.0a5-py3-none-linux_x86_64.whl"] == wheel
    declared = tomllib.loads((assets / "ethos-0.2.0-alpha.5.mise.toml").read_text())
    linux = declared["tools"]["http:ethos"]["platforms"]["linux-x64"]
    assert linux["url"] == "https://example.invalid/v/ethos-0.2.0-alpha.5-linux-x64.tar.gz"
    assert linux["checksum"] == f"sha256:{sums['ethos-0.2.0-alpha.5-linux-x64.tar.gz']}"
    platforms = declared["tools"]["http:ethos"]["platforms"].values()
    assert {platform["bin_path"] for platform in platforms} == {"ethos/bin"}
    assert (tmp_path / "out/notes.md").read_text() == "### Added\n\n- Hosted release.\n"
    shutil.rmtree(inputs / "release-runtime-windows-x64")
    assert "ethos-0.2.0a5-py3-none-win_amd64.whl" not in release_assets.assemble(
        inputs, tmp_path / "optional", **options
    )
    shutil.rmtree(inputs / "release-runtime-linux-arm64")
    with pytest.raises(ValueError, match="release_assets_platform_missing:linux-arm64"):
        release_assets.assemble(inputs, tmp_path / "partial", **options)


def test_an_emulating_host_publishes_the_archive_itqualified_leg(tmp_path):
    """Windows on Arm serves its platform with the x64 runtime it built, but no wheel of its own.

    Only a native leg publishes a wheel or stands in for a required platform, and a leg's
    runtime runs the operating system its host declares.
    """
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG, encoding="utf-8")
    for host, leg in (_NATIVE | {"windows-arm64": ("windows", "x86_64", "win_amd64")}).items():
        qualified_leg(inputs, host, *leg)
    options = _options(changelog, optional={"windows-x64", "windows-arm64"})
    sums = release_assets.assemble(inputs, tmp_path / "out", **options)
    declared = tomllib.loads((tmp_path / "out/assets/ethos-0.2.0-alpha.5.mise.toml").read_text())
    platforms = declared["tools"]["http:ethos"]["platforms"]
    emulated = hashlib.sha256(b"windows-arm64").hexdigest()
    assert set(platforms) == {*_NATIVE, "windows-arm64"}
    assert sums["ethos-0.2.0-alpha.5-windows-arm64.tar.gz"] == emulated
    assert platforms["windows-arm64"]["checksum"] == f"sha256:{emulated}"
    native = hashlib.sha256(b"wheel windows-x64").hexdigest()
    assert sums["ethos-0.2.0a5-py3-none-win_amd64.whl"] == native
    assert len([name for name in sums if name.endswith(".whl")]) == 4
    shutil.rmtree(inputs / "release-runtime-windows-arm64")
    qualified_leg(inputs, "windows-arm64", "linux", "x86_64", "linux_x86_64")
    with pytest.raises(ValueError, match="release_assets_distribution_mismatch:windows-arm64"):
        release_assets.assemble(inputs, tmp_path / "foreign", **options)
    shutil.rmtree(inputs / "release-runtime-windows-arm64")
    shutil.rmtree(inputs / "release-runtime-linux-arm64")
    qualified_leg(inputs, "linux-arm64", "linux", "x86_64", "linux_x86_64")
    with pytest.raises(ValueError, match="release_assets_platform_missing:linux-arm64"):
        release_assets.assemble(inputs, tmp_path / "emulated", **options)


def test_each_release_leg_declares_the_host_its_runner_provides():
    """A leg's host is declared, since Windows reports its CPU to an emulated interpreter.

    Host conformance's tiers and their legs are declared, and every leg names its platform.
    """
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    release = jobs["release-platforms"]
    included = release["strategy"]["matrix"]["include"]
    legs = {leg["host"]: (leg["os"], leg["python"]) for leg in included}
    emulated = ("windows-11-arm", "cpython-3.14-windows-x86_64-none")
    assert legs == {
        "linux-x64": ("ubuntu-latest", "3.14"),
        "linux-arm64": ("ubuntu-24.04-arm", "3.14"),
        "macos-arm64": ("macos-latest", "3.14"),
        "windows-x64": ("windows-latest", "3.14"),
        "windows-arm64": emulated,
    }
    steps = release["steps"]
    uploads = [step["with"]["name"] for step in steps if "upload-artifact" in step.get("uses", "")]
    assert uploads == ["release-runtime-${{ matrix.host }}"]
    # Host conformance runs in three tiers: every leg for a batch-head dispatch or the drift
    # schedule, the push legs with the Windows legs when the lane owner asks, and the push legs
    # for every other event, a proposal push included.
    selection = re.fullmatch(
        r"\$\{\{ fromJSON\(\((.+)\) && '(\[.*?\])' \|\| inputs\.windows_legs && '(.*?)'"
        r" \|\| '(\[.*\])'\) \}\}",
        jobs["host-conformance"]["strategy"]["matrix"]["include"],
        re.S,
    )
    assert selection is not None
    full_run = "github.event_name == 'schedule'"
    assert full_run in selection[1]
    push_legs = json.loads(selection[4])
    assert [leg["platform"] for leg in push_legs] == ["linux-x64"] * 3 + ["macos-arm64"]
    assert [leg["python"] for leg in push_legs] == ["3.12", "3.13", "3.14", "3.12"]
    windows = {"platform": "windows-arm64", "runner": emulated[0], "python": emulated[1]}
    assert len(json.loads(selection[2])) > len(push_legs)
    with_windows = json.loads(selection[3])
    assert with_windows[: len(push_legs)] == push_legs
    assert any(
        {key: leg[key] for key in ("platform", "runner", "python")} == windows
        for leg in with_windows
    )


def test_the_release_attests_its_archives_and_wheels_before_it_exists():
    """Mise's github backend verifies these attestations, so no release may lack them."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    publish = jobs["release-publish"]
    steps = [step.get("name", "") for step in publish["steps"]]
    attests = [
        step for step in publish["steps"] if "attest-build-provenance" in step.get("uses", "")
    ]

    assert len(attests) == 1
    assert attests[0]["with"]["subject-path"].split() == [
        f"build/release/out/assets/ethos-*{suffix}"
        for suffix in (".tar.gz", ".whl", ".spdx.json", ".syft.json")
    ]
    assert steps.index(attests[0]["name"]) < steps.index("Publish the signed pre-release")
    assert publish["permissions"] == {
        "contents": "write",
        "id-token": "write",
        "attestations": "write",
    }
