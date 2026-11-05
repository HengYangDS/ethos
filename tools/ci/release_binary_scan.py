"""Report the binary-level advisories of the runtime inventories one release published.

`release-inventory` publishes a symbol-capturing Syft JSON inventory beside each runtime archive,
covered by `SHA256SUMS`. This read-only scan downloads only those inventories, checks each against
its sums entry and the archive it names, and runs the locked Grype on it. Every listed archive is
either scanned or named as not scanned; none is silently clean. The report never blocks the
release: enforcement belongs to the dependency acceptance policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import ethos.repository.paradigm.parameters as parameters
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.native_supply import NativeSupply
from ethos.adapters.repo.runtime.materialization.native_supply import materialize_tool
from ethos.adapters.toolchain.mise import native_tool_cache

if TYPE_CHECKING:
    from collections.abc import Callable

    import nox

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "build/runtime/work/release-binary-scan"
EVIDENCE = ROOT / "build/evidence/release-binary-scan/report.json"
REPOSITORY = "HengYangDS/ethos"
_UNIDENTIFIED = "no package identified in executable file"


def scan_release(
    directory: Path, *, version: str, grype: Callable[[Path, Path], None], audited_lock: str
) -> dict[str, object]:
    """Scan each published inventory in `directory` and return the release's report."""
    sums: dict[str, str] = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        listed, _, name = line.partition("  ")
        if name:
            sums[name] = listed
    prefix, suffix = f"ethos-{version}-", ".tar.gz"
    hosts = sorted(
        name.removeprefix(prefix).removesuffix(suffix)
        for name in sums
        if name.startswith(prefix) and name.endswith(suffix)
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "kind": "ethos_release_binary_scan",
        "version": version,
        "scanner": {},
        "database": {},
        "archives": {},
        "not_claimed": ["blocking", "reachability beyond Go symbols", "fixes available upstream"],
    }
    rows: dict[tuple[object, ...], dict[str, object]] = {}
    unidentified: set[tuple[str, str]] = set()
    for host in hosts:
        archive = f"{prefix}{host}{suffix}"
        entry = {"archive": archive, "sha256": sums[archive]}
        report["archives"][host] = entry  # type: ignore[index]
        inventory = directory / f"{prefix}{host}.syft.json"
        if not inventory.is_file():
            entry |= {"state": "not_scanned", "reason": "inventory_missing"}
            continue
        if _sha256(inventory) != sums.get(inventory.name):
            message = f"release_binary_scan_inventory_digest_mismatch:{host}"
            raise ValueError(message)
        document = json.loads(inventory.read_text(encoding="utf-8"))
        source = document.get("source") or {}
        digests = {
            (item.get("algorithm"), item.get("value"))
            for item in (source.get("metadata") or {}).get("digests") or ()
        }
        if source.get("name") != archive or ("sha256", sums[archive]) not in digests:
            message = f"release_binary_scan_inventory_subject_mismatch:{host}"
            raise ValueError(message)
        result_path = inventory.with_name(f"grype-{host}.json")
        grype(inventory, result_path)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        descriptor = result.get("descriptor") or {}
        status = (descriptor.get("db") or {}).get("status") or {}
        report["scanner"] = {"name": descriptor.get("name"), "version": descriptor.get("version")}
        source_url = str(status.get("from") or "")
        checksum = parse_qs(urlsplit(source_url).query).get("checksum") or [None]
        report["database"] = {
            "built": status.get("built"),
            "source": status.get("from"),
            "checksum": checksum[0],
        }
        audited = _audited_locks(document, audited_lock)
        for match in result.get("matches") or ():
            artifact, advisory = match.get("artifact") or {}, match.get("vulnerability") or {}
            key = (archive, artifact.get("name"), artifact.get("version"), advisory.get("id"))
            fix = advisory.get("fix") or {}
            paths = {location.get("path") for location in artifact.get("locations") or ()}
            rows[key] = {
                "archive": archive,
                "package": key[1],
                "version": key[2],
                "type": artifact.get("type"),
                "advisory": key[3],
                "severity": advisory.get("severity"),
                "fix_state": fix.get("state"),
                "fixed_in": fix.get("versions") or [],
                "audited_by": "npm audit"
                if artifact.get("type") == "npm" and paths and paths <= audited
                else None,
            }
        unidentified.update(
            (archive, item["location"]["path"])
            for item in document.get("files") or ()
            if any(_UNIDENTIFIED in note for note in item.get("unknowns") or ())
        )
        entry |= {"state": "scanned", "inventory_sha256": _sha256(inventory)}
    report["rows"] = [rows[key] for key in sorted(rows, key=lambda key: tuple(map(str, key)))]
    report["unidentified_executables"] = [
        {"archive": archive, "path": path} for archive, path in sorted(unidentified)
    ]
    return report


def run(session: nox.Session) -> None:
    """Download one published release's inventories, scan them and keep the report."""
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--tag", required=True)
    tag = parser.parse_args(tuple(session.posargs)).tag
    work = WORK / tag
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    patterns = ("--pattern", "*.syft.json", "--pattern", "SHA256SUMS")
    command = ("gh", "release", "download", tag, "--repo", REPOSITORY, "--dir", str(work))
    run_command(ROOT, (*command, *patterns), check=True, timeout=parameters.seconds("download"))
    report = scan_release(
        work,
        version=tag.removeprefix("v"),
        grype=_native_grype(),
        audited_lock=_audited_lock(tag),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(rendered, encoding="utf-8")
    archives = cast("dict[str, dict[str, object]]", report["archives"])
    scanned = [host for host, entry in archives.items() if entry["state"] == "scanned"]
    session.log(f"scanned {len(scanned)} of {len(archives)} archives: {scanned}")
    rows = cast("list[object]", report["rows"])
    session.log(f"{len(rows)} advisory rows; report {EVIDENCE.relative_to(ROOT)}")


def _native_grype() -> Callable[[Path, Path], None]:
    supply = NativeSupply.read(ROOT, "grype")
    executable = materialize_tool(ROOT, "grype") / supply.executable_name
    database = native_tool_cache(ROOT) / "grype-db"

    def scan(inventory: Path, output: Path) -> None:
        run_command(
            ROOT,
            (str(executable), f"sbom:{inventory}", "--output", "json", "--file", str(output), "-q"),
            check=True,
            # The scan may fetch Grype's database first, so it takes the gate wait.
            timeout=parameters.seconds("gate"),
            env={"GRYPE_CHECK_FOR_APP_UPDATE": "false", "GRYPE_DB_CACHE_DIR": str(database)},
            remove_env_prefixes=("GIT_", "GRYPE_", "SYFT_"),
        )

    return scan


def _audited_lock(tag: str) -> str:
    """Digest the lock at the scanned tag, the one that release's audit checked."""
    accept = ("-H", "Accept: application/vnd.github.raw")
    path = f"repos/{REPOSITORY}/contents/package-lock.json?ref={tag}"
    completed = run_command(
        ROOT,
        ("gh", "api", *accept, path),
        text=False,
        check=True,
        timeout=parameters.seconds("request"),
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _audited_locks(document: dict, audited_lock: str) -> set[str]:
    """Return the shipped lock paths whose bytes equal the lock that the release audit checked."""
    return {
        item["location"]["path"]
        for item in document.get("files") or ()
        if ("sha256", audited_lock)
        in {(digest.get("algorithm"), digest.get("value")) for digest in item.get("digests") or ()}
    }


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
