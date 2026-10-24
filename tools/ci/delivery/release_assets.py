"""Assemble one hosted pre-release from the platform artifacts its release smokes qualified.

The ETHOS wheel carries its platform's Node and Vale, so each platform job builds its own
release wheel from the signed tag, and its release install smoke qualifies that wheel and
retains the runtime archive it built. The smoke evidence records the archive's SHA-256,
runtime, wheel and platform. This module checks those records against each job's bytes,
names each archive for its Mise platform, and writes the checksums, the Mise declaration
and the release notes that publication uploads. It uses only the standard library, so the
publication job runs it with uv's Python and without the project environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from pathlib import PureWindowsPath

_SYSTEMS = {"darwin": "macos", "linux": "linux", "windows": "windows"}
_MACHINES = {"arm64": "arm64", "x86_64": "x64"}
_REQUIRED = frozenset({"linux-arm64", "linux-x64", "macos-arm64"})
_PRERELEASE = re.compile(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+")


def assemble(
    source: Path, output: Path, *, tag: str, base_url: str, changelog: Path
) -> dict[str, str]:
    """Verify every qualified archive and write the publication's exact assets."""
    if _PRERELEASE.fullmatch(tag) is None:
        message = "release_assets_prerelease_required"
        raise ValueError(message)
    version = tag.removeprefix("v")
    archives = {}
    for evidence in sorted(source.glob("*/evidence/local-install/release-smoke.json")):
        job = evidence.parents[2]
        distribution = json.loads(evidence.read_text(encoding="utf-8"))["distribution"]
        platform = f"{_SYSTEMS[distribution['platform']]}-{_MACHINES[distribution['architecture']]}"
        # Each runner records its own path syntax; Windows rules read both separators.
        name = PureWindowsPath(distribution["path"]).name
        wheel = _single(
            job.glob("artifacts/release/python/ethos-*.whl"),
            f"release_assets_wheel_invalid:{platform}",
        )
        archive = _single(
            job.glob(f"artifacts/native/{distribution['runtime_digest']}/{name}"),
            f"release_assets_archive_invalid:{platform}",
        )
        if (
            platform in archives
            or any(wheel.name == other.name for _archive, other in archives.values())
            or _sha256(archive) != distribution["sha256"]
            or _sha256(wheel) != distribution["wheel_sha256"]
            or distribution["product_version"] != version
        ):
            message = f"release_assets_distribution_mismatch:{platform}"
            raise ValueError(message)
        archives[platform] = (archive, wheel)
    if missing := sorted(_REQUIRED - set(archives)):
        message = "release_assets_platform_missing:" + ",".join(missing)
        raise ValueError(message)
    notes = _release_notes(changelog, version)
    assets = output / "assets"
    assets.mkdir(parents=True)
    sums = {}
    declaration = [f'[tools."http:ethos"]\nversion = "{version}"\n\n[tools."http:ethos".platforms]']
    for platform, (archive, wheel) in sorted(archives.items()):
        shutil.copy2(wheel, assets / wheel.name)
        sums[wheel.name] = _sha256(assets / wheel.name)
        published = f"ethos-{version}-{platform}.tar.gz"
        shutil.copy2(archive, assets / published)
        sums[published] = _sha256(assets / published)
        # The archive's console directory, not the runtime's scripts: adopters get `ethos` alone.
        declaration.append(
            f'{platform} = {{ url = "{base_url}/{published}", checksum = "sha256:'
            f'{sums[published]}", bin_path = "ethos/bin" }}'
        )
    (assets / f"ethos-{version}.mise.toml").write_text(
        "\n".join(declaration) + "\n", encoding="utf-8"
    )
    (assets / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(sums.items())), encoding="utf-8"
    )
    (output / "notes.md").write_text(notes, encoding="utf-8")
    return sums


def _release_notes(changelog: Path, version: str) -> str:
    """Return the curated entry for this version, without the history around it."""
    lines = changelog.read_text(encoding="utf-8").splitlines()
    heading = f"## [{version}] - "
    start = next((index for index, line in enumerate(lines) if line.startswith(heading)), None)
    if start is None:
        message = f"release_assets_changelog_entry_missing:{version}"
        raise ValueError(message)
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip() + "\n"


def _single(paths, gap: str) -> Path:
    selected = tuple(path for path in paths if path.is_file() and not path.is_symlink())
    if len(selected) != 1:
        raise ValueError(gap)
    return selected[0]


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(arguments: list[str] | None = None) -> int:
    """Assemble the assets of one hosted pre-release from downloaded job artifacts."""
    parser = argparse.ArgumentParser(description="Assemble one hosted ETHOS pre-release.")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--changelog", type=Path, required=True)
    options = parser.parse_args(arguments)
    sums = assemble(
        options.source,
        options.output,
        tag=options.tag,
        base_url=options.base_url.rstrip("/"),
        changelog=options.changelog,
    )
    print(json.dumps(sums, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
