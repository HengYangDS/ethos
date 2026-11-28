"""Assemble one hosted pre-release from the platform artifacts its release smokes qualified.

The ETHOS wheel carries its platform's Node and Vale, so each platform job builds its own
release wheel from the signed tag, and its release install smoke qualifies that wheel and
retains the runtime archive it built. The smoke evidence records the archive's SHA-256,
runtime, wheel and platform. Each job uploads that qualification as `release-runtime-<host>`
for the one host platform its leg declares. This module checks those records against each
job's bytes, names each archive for its host's Mise platform, and writes the checksums, the
Mise declaration and the release notes that publication uploads. Each archive travels with the two
inventories its leg cataloged, an SPDX SBOM and a Syft JSON inventory, admitted only when both
name its published file and digest. It uses only the standard library, so the publication job
runs it with uv's Python and without the project environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable

_SYSTEMS = {"darwin": "macos", "linux": "linux"}
_MACHINES = {"arm64": "arm64", "x86_64": "x64"}
_HOSTS = frozenset(f"{os}-{cpu}" for os in _SYSTEMS.values() for cpu in _MACHINES.values())
_JOB = "release-runtime-"
_PRERELEASE = re.compile(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+")
_HEAD = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_STAGES = {"alpha": "a", "beta": "b", "rc": "rc"}
_INVENTORIES = (".spdx.json", ".syft.json")
# GitHub's attestation tooling reads at most 16 MB, so a larger inventory is not admitted.
INVENTORY_LIMIT = 16 * 1024 * 1024


def inventory_gaps(spdx: object, syft: object, *, name: str, digest: str) -> tuple[str, ...]:
    """Name what keeps two inventories from declaring one archive's bytes and components."""
    gaps = []
    spdx = spdx if isinstance(spdx, dict) else {}
    described = {
        relation.get("relatedSpdxElement")
        for relation in spdx.get("relationships") or ()
        if isinstance(relation, dict)
        and relation.get("spdxElementId") == "SPDXRef-DOCUMENT"
        and relation.get("relationshipType") == "DESCRIBES"
    }
    packages = [package for package in spdx.get("packages") or () if isinstance(package, dict)]
    roots = [package for package in packages if package.get("SPDXID") in described]
    sums = {
        (checksum.get("algorithm"), checksum.get("checksumValue"))
        for root in roots
        for checksum in root.get("checksums") or ()
        if isinstance(checksum, dict)
    }
    if (
        spdx.get("spdxVersion") != "SPDX-2.3"
        or len(roots) != 1
        or roots[0].get("name") != name
        or ("SHA256", digest) not in sums
    ):
        gaps.append("spdx_subject")
    if len(packages) < 2:
        gaps.append("spdx_components")
    inventory = syft if isinstance(syft, dict) else {}
    source = _table(inventory, "source")
    digests = {
        (item.get("algorithm"), item.get("value"))
        for item in _table(source, "metadata").get("digests") or ()
        if isinstance(item, dict)
    }
    if source.get("name") != name or ("sha256", digest) not in digests:
        gaps.append("syft_subject")
    if not inventory.get("artifacts"):
        gaps.append("syft_components")
    return tuple(gaps)


def distribution_version(version: str) -> str:
    """Return the PEP 440 version that a build of this prerelease product version records."""
    match = re.fullmatch(r"(\d+\.\d+\.\d+)-(alpha|beta|rc)\.(\d+)", version)
    if match is None:
        message = "release_assets_prerelease_required"
        raise ValueError(message)
    return f"{match[1]}{_STAGES[match[2]]}{match[3]}"


def declared_hosts(text: str) -> frozenset[str]:
    """Read the pipeline's comma-separated release hosts."""
    return frozenset(host.strip() for host in text.split(",") if host.strip())


def assemble(
    source: Path,
    output: Path,
    *,
    tag: str,
    base_url: str,
    changelog: Path,
    hosts: frozenset[str],
    expect_head: str,
) -> dict[str, str]:
    """Verify every qualified archive of the declared legs and write the publication's assets."""
    if _PRERELEASE.fullmatch(tag) is None:
        message = "release_assets_prerelease_required"
        raise ValueError(message)
    if not hosts or not hosts <= _HOSTS:
        message = "release_assets_hosts_invalid"
        raise ValueError(message)
    if _HEAD.fullmatch(expect_head) is None:
        message = "release_assets_head_invalid"
        raise ValueError(message)
    version = tag.removeprefix("v")
    identity = (expect_head, distribution_version(version))
    archives = _admitted_legs(source, version, hosts=hosts, identity=identity)
    notes = _release_notes(changelog, version)
    assets = output / "assets"
    assets.mkdir(parents=True)
    sums = {}
    declaration = [f'[tools."http:ethos"]\nversion = "{version}"\n\n[tools."http:ethos".platforms]']
    for platform, (archive, wheel, inventories) in sorted(archives.items()):
        shutil.copy2(wheel, assets / wheel.name)
        sums[wheel.name] = _sha256(assets / wheel.name)
        published = f"ethos-{version}-{platform}.tar.gz"
        shutil.copy2(archive, assets / published)
        sums[published] = _sha256(assets / published)
        for suffix, inventory in zip(_INVENTORIES, inventories, strict=True):
            shutil.copy2(inventory, assets / f"ethos-{version}-{platform}{suffix}")
            sums[f"ethos-{version}-{platform}{suffix}"] = _sha256(inventory)
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


def _admitted_legs(
    source: Path, version: str, *, hosts: frozenset[str], identity: tuple[str, str]
) -> dict[str, tuple[Path, Path, tuple[Path, ...]]]:
    """Admit each declared leg's qualified upload; every declared host must publish."""
    archives: dict[str, tuple[Path, Path, tuple[Path, ...]]] = {}
    for evidence in sorted(source.glob(f"{_JOB}*/evidence/local-install/release-smoke.json")):
        job = evidence.parents[2]
        platform = job.name.removeprefix(_JOB)
        if platform not in hosts:
            message = f"release_assets_host_undeclared:{platform}"
            raise ValueError(message)
        distribution = json.loads(evidence.read_text(encoding="utf-8"))["distribution"]
        # Only the tagged commit's build of the tag's version may publish, whatever else matches.
        if (
            distribution.get("source_commit"),
            distribution.get("distribution_version"),
        ) != identity:
            message = f"release_assets_identity_mismatch:{platform}"
            raise ValueError(message)
        runtime = f"{_SYSTEMS[distribution['platform']]}-{_MACHINES[distribution['architecture']]}"
        name = Path(distribution["path"]).name
        wheel = _single(
            job.glob("artifacts/release/python/ethos-*.whl"),
            f"release_assets_wheel_invalid:{platform}",
        )
        archive = _single(
            job.glob(f"artifacts/native/{distribution['runtime_digest']}/{name}"),
            f"release_assets_archive_invalid:{platform}",
        )
        if (
            runtime != platform
            or wheel.name in {other.name for _archive, other, _ in archives.values()}
            or _sha256(archive) != distribution["sha256"]
            or _sha256(wheel) != distribution["wheel_sha256"]
            or distribution["product_version"] != version
        ):
            message = f"release_assets_distribution_mismatch:{platform}"
            raise ValueError(message)
        published = f"ethos-{version}-{platform}.tar.gz"
        inventories = _inventories(job, platform, name=published, digest=distribution["sha256"])
        archives[platform] = (archive, wheel, inventories)
    if missing := sorted(hosts - set(archives)):
        message = "release_assets_platform_missing:" + ",".join(missing)
        raise ValueError(message)
    return archives


def _inventories(job: Path, platform: str, *, name: str, digest: str) -> tuple[Path, ...]:
    """Return a leg's two admitted inventories."""
    directory = job / "evidence/release"
    paths = tuple(directory / f"runtime{suffix}" for suffix in _INVENTORIES)
    declared = {path for suffix in _INVENTORIES for path in directory.glob(f"*{suffix}")}
    # A second declaration is a pipeline defect or tampering.
    if declared - set(paths):
        message = f"release_assets_inventory_mismatch:{platform}"
        raise ValueError(message)
    try:
        selected = tuple(
            _single((path,), f"release_assets_inventory_invalid:{platform}") for path in paths
        )
        if any(path.stat().st_size > INVENTORY_LIMIT for path in selected):
            message = f"release_assets_inventory_invalid:{platform}"
            raise ValueError(message)
        documents = [json.loads(path.read_text(encoding="utf-8")) for path in selected]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        message = f"release_assets_inventory_invalid:{platform}"
        raise ValueError(message) from error
    if gaps := inventory_gaps(*documents, name=name, digest=digest):
        kind = "mismatch" if any(gap.endswith("_subject") for gap in gaps) else "components_missing"
        message = f"release_assets_inventory_{kind}:{platform}"
        raise ValueError(message)
    return selected


def _table(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    return value if isinstance(value, dict) else {}


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


def _single(paths: Iterable[Path], gap: str) -> Path:
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
    named = parser.add_mutually_exclusive_group(required=True)
    named.add_argument("--tag")
    # A rehearsal's tag does not exist yet: it is the version file's version, read here so that
    # the step stays one command.
    named.add_argument("--version-file", type=Path)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    # The release's download prefix; the tag is appended here, so a step names the tag once. It
    # is not `--base-url`, which held the tag: the publication runs a tag's copy of this file from
    # the default branch's workflow, and a renamed flag refuses that skew in either direction.
    parser.add_argument("--download-prefix", required=True)
    parser.add_argument("--changelog", type=Path, required=True)
    parser.add_argument("--hosts", required=True)
    parser.add_argument("--expect-head", required=True)
    options = parser.parse_args(arguments)
    # Only the line ending is dropped, as the shell's read did; any other padding fails the
    # prerelease form in `assemble`.
    tag = options.tag
    if tag is None:
        tag = "v" + options.version_file.read_text(encoding="utf-8").rstrip("\n")
    sums = assemble(
        options.source,
        options.output,
        tag=tag,
        base_url=f"{options.download_prefix.rstrip('/')}/{tag}",
        changelog=options.changelog,
        hosts=declared_hosts(options.hosts),
        expect_head=options.expect_head,
    )
    print(json.dumps({"sums": sums}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
