"""A release run reports the binary-level advisories of the inventories it published."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tests.support.release_legs import inventory_documents
from tools.ci import release_binary_scan

_ROOT = Path(__file__).resolve().parents[3]
_VERSION = "0.2.0-beta.3"
_DATABASE = {
    "built": "2026-11-04T06:20:59Z",
    "from": "https://db.invalid/v6.tar.zst?checksum=sha256%3Aab",
}


def _match(name: str, version: str, kind: str, advisory: str) -> dict:
    fix = {"state": "fixed", "versions": ["9.9.9"]}
    where = [{"path": _LOCK}] if kind == "npm" else []
    return {
        "artifact": {"name": name, "version": version, "type": kind, "locations": where},
        "vulnerability": {"id": advisory, "severity": "High", "fix": fix},
    }


def _published(directory: Path, hosts: tuple[str, ...]) -> dict[str, str]:
    """Write the archives' sums and each host's Syft inventory, as the release publishes them."""
    directory.mkdir(parents=True, exist_ok=True)
    sums = {}
    for host in hosts:
        archive = f"ethos-{_VERSION}-{host}.tar.gz"
        sums[archive] = hashlib.sha256(host.encode()).hexdigest()
        _spdx, inventory = inventory_documents(archive, sums[archive])
        inventory["files"] = [
            {"location": {"path": "/ethos/runtime/python/bin/ruff"}, "unknowns": [_UNKNOWN]},
            {"location": {"path": "/ethos/runtime/python/bin/uv"}},
            {"location": {"path": _LOCK}, "digests": [{"algorithm": "sha256", "value": _SHIPPED}]},
        ]
        path = directory / f"ethos-{_VERSION}-{host}.syft.json"
        path.write_text(json.dumps(inventory), encoding="utf-8")
        sums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    sums["ethos-0.2.0-beta.3-linux-arm64.tar.gz"] = "0" * 64
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(sums.items())), encoding="utf-8"
    )
    return sums


_UNKNOWN = "unknowns-labeler: no package identified in executable file"
_LOCK = "/ethos/runtime/python/lib/site-packages/ethos/resources/package-lock.json"
_SHIPPED = "5" * 64


def _grype(_inventory: Path, report: Path) -> None:
    matches = [
        _match("stdlib", "go1.25.7", "go-module", "GO-2026-1"),
        _match("stdlib", "go1.25.7", "go-module", "GO-2026-1"),
        _match("undici", "6.29.0", "npm", "GHSA-xjj6"),
    ]
    descriptor = {"name": "grype", "version": "0.121.1", "db": {"status": _DATABASE}}
    report.write_text(json.dumps({"descriptor": descriptor, "matches": matches}), encoding="utf-8")


def test_the_report_keys_rows_and_names_what_it_could_not_scan(tmp_path):
    """Rows compare between releases; npm rows defer to npm's audit; no host is silently clean."""
    sums = _published(tmp_path / "release", ("linux-x64", "macos-arm64"))
    scan = release_binary_scan.scan_release
    report = scan(tmp_path / "release", version=_VERSION, grype=_grype, audited_lock=_SHIPPED)
    assert report["scanner"] == {"name": "grype", "version": "0.121.1"}
    assert report["database"] == {"built": _DATABASE["built"], "source": _DATABASE["from"]}
    assert report["archives"]["linux-arm64"] == {
        "archive": "ethos-0.2.0-beta.3-linux-arm64.tar.gz",
        "sha256": "0" * 64,
        "state": "not_scanned",
        "reason": "inventory_missing",
    }
    scanned = report["archives"]["macos-arm64"]
    assert scanned["state"] == "scanned"
    assert scanned["inventory_sha256"] == sums["ethos-0.2.0-beta.3-macos-arm64.syft.json"]
    keys = [(row["archive"], row["package"], row["advisory"]) for row in report["rows"]]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys)) == 4
    audited = {row["package"]: row["audited_by"] for row in report["rows"]}
    assert audited == {"stdlib": None, "undici": "npm audit"}
    other = scan(tmp_path / "release", version=_VERSION, grype=_grype, audited_lock="6" * 64)
    assert {row["package"]: row["audited_by"] for row in other["rows"]}["undici"] is None
    assert {item["path"] for item in report["unidentified_executables"]} == {
        "/ethos/runtime/python/bin/ruff"
    }


@pytest.mark.parametrize(
    ("tamper", "gap"),
    [
        ("inventory", "release_binary_scan_inventory_digest_mismatch:linux-x64"),
        ("subject", "release_binary_scan_inventory_subject_mismatch:linux-x64"),
    ],
)
def test_a_tampered_inventory_refuses_the_scan(tmp_path, tamper, gap):
    """An inventory that is not the published one, or names another archive, is never scanned."""
    _published(tmp_path / "release", ("linux-x64",))
    path = tmp_path / "release" / f"ethos-{_VERSION}-linux-x64.syft.json"
    if tamper == "inventory":
        path.write_text(path.read_text() + "\n", encoding="utf-8")
    else:
        sums = (tmp_path / "release/SHA256SUMS").read_text()
        _spdx, foreign = inventory_documents("ethos-other.tar.gz", "1" * 64)
        path.write_text(json.dumps(foreign), encoding="utf-8")
        listed = hashlib.sha256(path.read_bytes()).hexdigest()
        lines = [line for line in sums.splitlines() if not line.endswith(path.name)]
        (tmp_path / "release/SHA256SUMS").write_text(
            "\n".join([*lines, f"{listed}  {path.name}"]) + "\n", encoding="utf-8"
        )
    with pytest.raises(ValueError, match=gap):
        release_binary_scan.scan_release(
            tmp_path / "release", version=_VERSION, grype=_grype, audited_lock=_SHIPPED
        )


def test_the_scan_job_reads_only_and_never_blocks_the_release():
    """The scan follows publication with read permission, and its failure cannot fail the run."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    scan = jobs["release-binary-scan"]
    assert scan["needs"] == "release-publish"
    assert scan["permissions"] == {"contents": "read"}
    assert scan["continue-on-error"] is True
    runs = [step.get("run", "") for step in scan["steps"]]
    assert any(
        "nox -s release_binary_scan -- --tag ${{ inputs.release_tag }}" in run for run in runs
    )
    upload = next(step for step in scan["steps"] if "upload-artifact" in step.get("uses", ""))
    assert upload["with"]["path"] == "build/evidence/release-binary-scan/"
    assert upload["if"] == "always()"
