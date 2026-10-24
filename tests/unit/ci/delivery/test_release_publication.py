"""A hosted release is admitted by its signed tag and published from the archives it qualified."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
from typing import TYPE_CHECKING

import pytest

from tests.support.fixture_signer import configure_fixture_signer
from tools.ci.delivery import pipeline
from tools.ci.delivery import release_assets

if TYPE_CHECKING:
    from pathlib import Path

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


def _qualified(inputs: Path, job: str, platform: str, machine: str, tag: str) -> tuple[Path, ...]:
    """Lay out one platform job's artifact as its upload roots it: wheel, archive, evidence."""
    runtime = hashlib.sha256(job.encode()).hexdigest()
    wheel = inputs / job / "artifacts/release/python" / f"ethos-0.2.0a5-py3-none-{tag}.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(f"wheel {job}".encode())
    archive = inputs / job / "artifacts/native" / runtime / "ethos-0.2.0a5.tar.gz"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(job.encode())
    evidence = inputs / job / "evidence/local-install/release-smoke.json"
    evidence.parent.mkdir(parents=True)
    # Each runner records the archive in its own path syntax; Windows separates with backslashes.
    separator = "\\" if platform == "windows" else "/"
    runner = separator.join(("D:" if platform == "windows" else "", "a", "build/artifacts/native"))
    distribution = {
        "path": separator.join((runner, runtime, archive.name)),
        "sha256": hashlib.sha256(job.encode()).hexdigest(),
        "runtime_digest": runtime,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "platform": platform,
        "architecture": machine,
        "product_version": "0.2.0-alpha.5",
    }
    evidence.write_text(json.dumps({"distribution": distribution}), encoding="utf-8")
    return wheel, archive


def test_release_assets_publish_only_the_qualified_bytes(tmp_path):
    """Each platform publishes the wheel it built and the archive its smoke qualified.

    Windows is optional: its qualified leg publishes, and its absence leaves the others.
    """
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG, encoding="utf-8")
    jobs = {
        "ubuntu-latest": ("linux", "x86_64", "linux_x86_64"),
        "ubuntu-24.04-arm": ("linux", "arm64", "linux_aarch64"),
        "macos-latest": ("darwin", "arm64", "macosx_14_0_arm64"),
        "windows-latest": ("windows", "x86_64", "win_amd64"),
    }
    qualified = {job: _qualified(inputs, job, *platform) for job, platform in jobs.items()}
    options = {"tag": _TAG, "base_url": "https://example.invalid/v", "changelog": changelog}
    unreleased = tmp_path / "UNRELEASED.md"
    unreleased.write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    for change, gap in (
        ({"tag": "v0.2.0"}, "release_assets_prerelease_required"),
        ({"changelog": unreleased}, "release_assets_changelog_entry_missing:0.2.0-alpha.5"),
    ):
        with pytest.raises(ValueError, match=gap):
            release_assets.assemble(inputs, tmp_path / "refused", **(options | change))
    for tampered in qualified["windows-latest"]:
        original = tampered.read_bytes()
        tampered.write_bytes(b"changed")
        with pytest.raises(ValueError, match="release_assets_distribution_mismatch:windows-x64"):
            release_assets.assemble(inputs, tmp_path / "refused", **options)
        tampered.write_bytes(original)
    assert not (tmp_path / "refused").exists()
    sums = release_assets.assemble(inputs, tmp_path / "out", **options)
    assets = tmp_path / "out/assets"
    assert sorted(path.name for path in assets.iterdir()) == [
        "SHA256SUMS",
        "ethos-0.2.0-alpha.5-linux-arm64.tar.gz",
        "ethos-0.2.0-alpha.5-linux-x64.tar.gz",
        "ethos-0.2.0-alpha.5-macos-arm64.tar.gz",
        "ethos-0.2.0-alpha.5-windows-x64.tar.gz",
        "ethos-0.2.0-alpha.5.mise.toml",
        "ethos-0.2.0a5-py3-none-linux_aarch64.whl",
        "ethos-0.2.0a5-py3-none-linux_x86_64.whl",
        "ethos-0.2.0a5-py3-none-macosx_14_0_arm64.whl",
        "ethos-0.2.0a5-py3-none-win_amd64.whl",
    ]
    wheel = hashlib.sha256(b"wheel ubuntu-latest").hexdigest()
    assert sums["ethos-0.2.0a5-py3-none-linux_x86_64.whl"] == wheel
    declared = tomllib.loads((assets / "ethos-0.2.0-alpha.5.mise.toml").read_text())
    linux = declared["tools"]["http:ethos"]["platforms"]["linux-x64"]
    assert linux["url"] == "https://example.invalid/v/ethos-0.2.0-alpha.5-linux-x64.tar.gz"
    assert linux["checksum"] == f"sha256:{sums['ethos-0.2.0-alpha.5-linux-x64.tar.gz']}"
    platforms = declared["tools"]["http:ethos"]["platforms"].values()
    assert {platform["bin_path"] for platform in platforms} == {"ethos/bin"}
    assert (tmp_path / "out/notes.md").read_text() == "### Added\n\n- Hosted release.\n"
    shutil.rmtree(inputs / "windows-latest")
    assert "ethos-0.2.0a5-py3-none-win_amd64.whl" not in release_assets.assemble(
        inputs, tmp_path / "optional", **options
    )
    shutil.rmtree(inputs / "ubuntu-24.04-arm")
    with pytest.raises(ValueError, match="release_assets_platform_missing:linux-arm64"):
        release_assets.assemble(inputs, tmp_path / "partial", **options)
