"""Validate supplied wheel provenance against the observer loaded in this child."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path

import ethos
from ethos.contracts.evidence.observer import ObserverIdentity


def observer_identity() -> ObserverIdentity:
    """Read only attempt supply; neither source nor ambient metadata selects it."""
    requirement = os.environ.get("ETHOS_NATIVE_OBSERVER_REQUIREMENT")
    if not requirement:
        msg = "python_native_observer_requirement_missing"
        raise ValueError(msg)
    identity = ObserverIdentity.from_requirement(
        requirement, os.environ.get("ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST", "")
    )
    wheel = identity.wheel
    if wheel.is_symlink() or not wheel.is_file():
        msg = "python_native_observer_wheel_missing"
        raise ValueError(msg)
    with wheel.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != identity.wheel_sha256:
        msg = "python_native_observer_wheel_changed"
        raise ValueError(msg)
    try:
        metadata = distribution("ethos")
        direct = json.loads(metadata.read_text("direct_url.json") or "")
        archive = direct["archive_info"]
        hashes = archive.get("hashes", {})
        recorded = hashes.get("sha256", archive.get("hash", "").removeprefix("sha256="))
        loaded = ObserverIdentity.from_requirement(
            f"ethos @ {direct['url']}#sha256={recorded}", identity.runtime_digest
        )
        valid = (
            "dir_info" not in direct
            and "vcs_info" not in direct
            and loaded.wheel.resolve() == wheel.resolve()
            and loaded.wheel_sha256 == identity.wheel_sha256
            and archive.get("hash", f"sha256={recorded}") == f"sha256={recorded}"
            and Path(ethos.__file__).resolve().parent
            == Path(str(metadata.locate_file("ethos"))).resolve()
        )
    except (
        AttributeError,
        KeyError,
        OSError,
        PackageNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        msg = "python_native_observer_provenance_invalid"
        raise ValueError(msg) from error
    if not valid:
        msg = "python_native_observer_provenance_mismatch"
        raise ValueError(msg)
    return identity


def runtime_identity() -> dict[str, object]:
    """Record the actual loaded child's interpreter and supplied observer together."""
    return {
        "executable": sys.executable,
        "version": list(sys.version_info[:3]),
        "prefix": sys.prefix,
        "observer": observer_identity().to_payload(),
    }
