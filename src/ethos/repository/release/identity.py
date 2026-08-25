"""Product, distribution, source, and package build identity."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import zipfile
from importlib import resources
from pathlib import Path
from typing import Literal
from typing import NamedTuple
from typing import cast

from packaging.version import InvalidVersion
from packaging.version import Version

_BUILD_IDENTITY_RESOURCE = "data/build/identity.json"
_SOURCE_BUILD_IDENTITY = Path("src/ethos/data/build/identity.json")
_HEX = frozenset("0123456789abcdef")


class BuildIdentity(NamedTuple):
    """One immutable package build identity without artifact-self hashes."""

    product_version: str
    distribution_version: str
    source_commit: str
    source_tree: str
    channel: Literal["development", "accepted"]
    acceptance_state: Literal["unaccepted", "accepted"]

    def projection(self) -> dict[str, str | int]:
        """Return the package-resource projection."""
        return {
            "schema_version": 1,
            "product_version": self.product_version,
            "distribution_version": self.distribution_version,
            "source_commit": self.source_commit,
            "source_tree": self.source_tree,
            "channel": self.channel,
            "acceptance_state": self.acceptance_state,
        }


def product_version(root: Path) -> str:
    """Read and validate the sole tracked SemVer product-version authority."""
    try:
        raw = (root / "VERSION").read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        message = "product_version_missing:VERSION"
        raise ValueError(message) from error
    if raw != raw.strip() + "\n":
        message = "product_version_invalid:VERSION"
        raise ValueError(message)
    value = raw.strip()
    try:
        parsed = Version(value)
    except InvalidVersion as error:
        message = "product_version_invalid:VERSION"
        raise ValueError(message) from error
    if value != _canonical_semver(parsed):
        message = "product_version_invalid:VERSION"
        raise ValueError(message)
    return value


def pep440_product_version(product: str) -> str:
    """Map one canonical SemVer product version to PEP 440."""
    try:
        parsed = Version(product)
    except InvalidVersion as error:
        message = "product_version_invalid"
        raise ValueError(message) from error
    if product != _canonical_semver(parsed):
        message = "product_version_invalid"
        raise ValueError(message)
    return str(parsed)


def build_identity(
    *,
    product: str,
    source_commit: str,
    source_tree: str,
    channel: Literal["development", "accepted"],
    acceptance_state: Literal["unaccepted", "accepted"],
) -> BuildIdentity:
    """Compile one exact source and channel into a package build identity."""
    if not _valid_git_identity(source_commit) or not _valid_git_identity(source_tree):
        message = "build_source_identity_invalid"
        raise ValueError(message)
    if (channel, acceptance_state) not in {
        ("development", "unaccepted"),
        ("accepted", "accepted"),
    }:
        message = "build_acceptance_identity_invalid"
        raise ValueError(message)
    base = pep440_product_version(product)
    distribution = (
        base
        if acceptance_state == "accepted"
        else f"{base}.dev0+g{source_commit[:12]}.t{source_tree[:12]}"
    )
    return BuildIdentity(
        product_version=product,
        distribution_version=str(Version(distribution)),
        source_commit=source_commit,
        source_tree=source_tree,
        channel=channel,
        acceptance_state=acceptance_state,
    )


def source_build_identity(root: Path, *, channel: str | None = None) -> BuildIdentity:
    """Compile the current Git checkout into its exact build identity."""
    commit, tree = source_git_identity(root)
    selected = channel or _source_channel(root, commit=commit, tree=tree)
    if selected not in {"development", "accepted"}:
        message = "build_channel_invalid"
        raise ValueError(message)
    return build_identity(
        product=product_version(root),
        source_commit=commit,
        source_tree=tree,
        channel=selected,
        acceptance_state="accepted" if selected == "accepted" else "unaccepted",
    )


def source_distribution_version() -> str:
    """Hatch dynamic-version source for the current checkout."""
    return build_input_identity(Path(__file__).resolve().parents[4]).distribution_version


def build_input_identity(root: Path) -> BuildIdentity:
    """Resolve a Git checkout or its carried sdist build identity."""
    if (root / ".git").exists():
        return source_build_identity(root)
    try:
        return load_build_identity_bytes((root / _SOURCE_BUILD_IDENTITY).read_bytes())
    except OSError as error:
        message = "package_build_identity_missing"
        raise ValueError(message) from error


def invoking_build_identity() -> BuildIdentity:
    """Resolve the invoking source checkout or installed package identity."""
    source = Path(__file__).resolve().parents[4]
    if (source / "pyproject.toml").is_file() and (source / "VERSION").is_file():
        return source_build_identity(source)
    return packaged_build_identity()


def build_identity_bytes(identity: BuildIdentity) -> bytes:
    """Serialize one build identity as canonical UTF-8 JSON bytes."""
    return (
        json.dumps(identity.projection(), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def load_build_identity_bytes(raw: bytes) -> BuildIdentity:
    """Load one canonical package build identity."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (TypeError, UnicodeError, ValueError) as error:
        message = "package_build_identity_invalid"
        raise ValueError(message) from error
    return _build_identity_from_projection(payload)


def _build_identity_from_projection(payload: object) -> BuildIdentity:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        message = "package_build_identity_invalid"
        raise ValueError(message)
    try:
        channel = cast("Literal['development', 'accepted']", str(payload["channel"]))
        acceptance_state = cast(
            "Literal['unaccepted', 'accepted']", str(payload["acceptance_state"])
        )
        identity = build_identity(
            product=str(payload["product_version"]),
            source_commit=str(payload["source_commit"]),
            source_tree=str(payload["source_tree"]),
            channel=channel,
            acceptance_state=acceptance_state,
        )
    except (KeyError, TypeError, ValueError) as error:
        message = "package_build_identity_invalid"
        raise ValueError(message) from error
    if payload != identity.projection():
        message = "package_build_identity_invalid"
        raise ValueError(message)
    return identity


def packaged_build_identity() -> BuildIdentity:
    """Read the immutable identity carried by an installed wheel."""
    try:
        raw = resources.files("ethos").joinpath(_BUILD_IDENTITY_RESOURCE).read_bytes()
    except (FileNotFoundError, OSError) as error:
        message = "package_build_identity_missing"
        raise ValueError(message) from error
    return load_build_identity_bytes(raw)


def wheel_build_identity(wheel: Path) -> BuildIdentity:
    """Read the complete immutable build identity carried by one wheel."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            raw = archive.read(f"ethos/{_BUILD_IDENTITY_RESOURCE}")
    except (KeyError, OSError, zipfile.BadZipFile) as error:
        message = "hook_runtime_wheel_build_identity_missing"
        raise ValueError(message) from error
    try:
        return load_build_identity_bytes(raw)
    except ValueError as error:
        message = "hook_runtime_wheel_build_identity_invalid"
        raise ValueError(message) from error


def accepted_version_reuse_gaps(
    candidate: BuildIdentity,
    prior: tuple[BuildIdentity, ...],
) -> tuple[str, ...]:
    """Reject one accepted product identity reused for different source."""
    if candidate.acceptance_state != "accepted":
        message = "accepted_version_candidate_invalid"
        raise ValueError(message)
    for existing in prior:
        if existing.acceptance_state != "accepted":
            continue
        if existing.product_version != candidate.product_version:
            continue
        if (
            existing.source_commit != candidate.source_commit
            or existing.source_tree != candidate.source_tree
        ):
            return (f"accepted_version_source_conflict:{candidate.product_version}",)
    return ()


def projected_package_versions(root: Path) -> dict[str, str]:
    """Validate tracked npm projections against the product-version owner."""
    expected = product_version(root)
    paths = {
        "distributions/npm/package.json": ("version",),
        "package-lock.json#packages/distributions/npm": (
            "packages",
            "distributions/npm",
            "version",
        ),
    }
    projected: dict[str, str] = {}
    for label, keys in paths.items():
        path = root / label.partition("#")[0]
        try:
            value: object = json.loads(path.read_text(encoding="utf-8"))
            for key in keys:
                value = _projection_mapping(value)[key]
        except (KeyError, OSError, TypeError, UnicodeError, ValueError) as error:
            message = f"package_version_projection_invalid:{label}"
            raise ValueError(message) from error
        if value != expected:
            message = f"package_version_projection_drift:{label}"
            raise ValueError(message)
        projected[label] = expected
    try:
        root_package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        message = "package_version_projection_invalid:root"
        raise ValueError(message) from error
    if not isinstance(root_package, dict) or "version" in root_package:
        message = "package_version_parallel_owner:package.json"
        raise ValueError(message)
    lock_root = lock.get("packages", {}).get("") if isinstance(lock, dict) else None
    if not isinstance(lock_root, dict) or "version" in lock or "version" in lock_root:
        message = "package_version_parallel_owner:package-lock.json"
        raise ValueError(message)
    return projected


def _projection_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        message = "package_version_projection_structure_invalid"
        raise TypeError(message)
    return value


def source_git_identity(root: Path) -> tuple[str, str]:
    """Return exact HEAD and effective source tree, including tracked overlay."""
    commit = _git(root, "rev-parse", "HEAD")
    with tempfile.TemporaryDirectory(prefix="ethos-source-index-") as directory:
        environment = {**os.environ, "GIT_INDEX_FILE": str(Path(directory) / "index")}
        _git(root, "read-tree", "HEAD", env=environment)
        _git(root, "add", "-A", env=environment)
        tree = _git(root, "write-tree", env=environment)
    if not _valid_git_identity(commit) or not _valid_git_identity(tree):
        message = "build_source_identity_invalid"
        raise ValueError(message)
    return commit, tree


def _source_channel(root: Path, *, commit: str, tree: str) -> Literal["development", "accepted"]:
    requested = (os.environ.get("ETHOS_BUILD_CHANNEL") or "").strip()
    if requested:
        if requested not in {"development", "accepted"}:
            message = "build_channel_invalid"
            raise ValueError(message)
        if requested == "accepted":
            _require_accepted_source(root, commit, tree)
        return requested  # type: ignore[return-value]
    try:
        _require_accepted_source(root, commit, tree)
    except ValueError:
        return "development"
    return "accepted"


def _require_accepted_source(root: Path, commit: str, tree: str) -> None:
    try:
        workspace = tomllib.loads((root / ".ethos/workspace.toml").read_text(encoding="utf-8"))
        accepted = str(workspace.get("branch_roles", {}).get("accepted_branch") or "dev")
    except (OSError, UnicodeError, ValueError) as error:
        message = "accepted_build_policy_unavailable"
        raise ValueError(message) from error
    if _git(root, "rev-parse", f"refs/heads/{accepted}") != commit:
        message = "accepted_build_source_mismatch"
        raise ValueError(message)
    if _git(root, "rev-parse", f"{commit}^{{tree}}") != tree:
        message = "accepted_build_tree_dirty"
        raise ValueError(message)


def _canonical_semver(version: Version) -> str:
    if version.epoch or version.post is not None or version.dev is not None or version.local:
        return ""
    if len(version.release) != 3:
        return ""
    value = ".".join(map(str, version.release))
    if version.pre is None:
        return value
    label = {"a": "alpha", "b": "beta", "rc": "rc"}.get(version.pre[0])
    return f"{value}-{label}.{version.pre[1]}" if label else ""


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ("git", *args), cwd=root, env=env, capture_output=True, text=True, check=False
    )
    if completed.returncode:
        message = "build_source_identity_unavailable"
        raise ValueError(message)
    return completed.stdout.strip()


def _valid_git_identity(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - _HEX
