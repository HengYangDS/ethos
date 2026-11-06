"""Runtime inventories owned by the repository Nox graph: one Syft run over the kept archive.

The install smoke keeps each runtime archive it qualified and records its SHA-256. One Syft run
reads that archive's bytes under its published name and writes two inventories: an SPDX 2.3 SBOM,
which consumers read, and a Syft JSON inventory that captures Go symbols, which binary scans
read. Both must name the archive and its digest, and hold every component that the runtime's
owners declare: the bundled Go tools, uv, Node and each shipped Python distribution. Syft finds Node
only in a file named `node`, so when it misses a Windows `node.exe`, the locked Node supply declares
it in both inventories, bound to the shipped bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.runtime.materialization.native_supply import NATIVE_BACKENDS
from ethos.adapters.repo.runtime.materialization.native_supply import NativeSupply
from ethos.adapters.repo.runtime.materialization.native_supply import materialize_tool
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from tools.ci.delivery.release_assets import inventory_gaps

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    import nox

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".config/release/release-sbom/policy.toml"
_SYSTEMS = {"darwin": "macos", "linux": "linux", "windows": "windows"}
_MACHINES = {"arm64": "arm64", "x86_64": "x64"}
_RUNTIME = re.compile(r"^/?ethos/runtime/[0-9a-f]{16}/")
_MANIFEST = re.compile(r"ethos/runtime/[0-9a-f]{16}/manifest\.json")
_DIST = re.compile(r"site-packages/([^/]+?)-([^/-]+)\.dist-info/METADATA$")
_NATIVE = re.compile(r"ethos/resources/native/([^/]+)/\1(?:\.exe)?$")
_UV = re.compile(r"(?:^|/)(?:bin/uv|Scripts/uv\.exe)$")
_NODE = re.compile(r"ethos/resources/node/(?:bin/node|node\.exe)$")
_DECLARER = "ethos-locked-supply"
_UNIDENTIFIED = "no package identified in executable file"


def native_syft(executable: Path) -> Callable[[tuple[str, ...]], None]:
    """Run the locked Syft with no inherited `SYFT_` setting, so only its config file applies."""

    def run(arguments: tuple[str, ...]) -> None:
        run_command(
            ROOT,
            (str(executable), *arguments),
            check=True,
            remove_env_prefixes=("GIT_", "SYFT_"),
        )

    return run


def catalog(
    archive: Path,
    *,
    name: str,
    outputs: tuple[Path, Path],
    config: Path,
    run: Callable[[tuple[str, ...]], None],
) -> tuple[dict, dict]:
    """Catalog the archive's bytes once and return its two inventories, bound to its digest."""
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
    spdx, syft = outputs
    run(
        (
            "scan",
            f"file:{archive}",
            "--source-name",
            name,
            "--config",
            str(config),
            "--quiet",
            "--output",
            f"spdx-json={spdx}",
            "--output",
            f"syft-json={syft}",
        )
    )
    documents = tuple(json.loads(path.read_text(encoding="utf-8")) for path in outputs)
    if gaps := inventory_gaps(*documents, name=name, digest=_sha256(archive)):
        subject = any(gap.endswith("_subject") for gap in gaps)
        message = (
            f"release_inventory_{'subject_mismatch' if subject else 'components_missing'}:"
            + ",".join(gaps)
        )
        raise ValueError(message)
    return documents[0], documents[1]


def missing_components(
    inventory: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    native: Mapping[str, str],
    node: str,
) -> list[str]:
    """Name each component that the runtime's owners declare and the inventory lacks."""
    artifacts = [item for item in _sequence(inventory, "artifacts") if isinstance(item, dict)]
    located: dict[str, set[tuple[object, object, object]]] = {}
    for artifact in artifacts:
        for location in artifact.get("locations") or ():
            path = _RUNTIME.sub("", str(location.get("path", "")))
            located.setdefault(path, set()).add(
                (artifact.get("type"), artifact.get("name"), artifact.get("version"))
            )
    python = {
        (_normal(str(item.get("name", ""))), item.get("version"))
        for item in artifacts
        if item.get("type") == "python"
    }
    files = [str(path) for path in _sequence(manifest, "runtime_files")]
    shipped = {_normal(match[1]): match[2] for path in files if (match := _DIST.search(path))}
    missing = [
        f"python:{name}@{version}"
        for name, version in shipped.items()
        if (name, version) not in python
    ]
    for path in files:
        found = located.get(path, set())
        if (tool := _NATIVE.search(path)) and tool[1] in native:
            version = f"v{native[tool[1]]}"
            if not any(kind == "go-module" and seen == version for kind, _name, seen in found):
                missing.append(f"go:{tool[1]}@{version}")
        elif _UV.search(path) and "uv" in shipped:
            if ("rust-crate", "uv", shipped["uv"]) not in found:
                missing.append(f"rust:uv@{shipped['uv']}")
        elif _NODE.search(path) and not any(
            name == "node" and seen == node for _kind, name, seen in found
        ):
            missing.append(f"node:node@{node}")
    return sorted(f"release_inventory_component_missing:{item}" for item in missing)


def complete_inventory(
    documents: tuple[dict, dict],
    manifest: Mapping[str, object],
    *,
    native: Mapping[str, str],
    node: str,
    shipped: Callable[[], tuple[str, str] | None],
    locked: Callable[[], str],
    creator: str,
) -> tuple[list[dict[str, str]], list[str]]:
    """Declare a locked Node that the catalog misses, then name each component still missing."""
    missing = missing_components(documents[1], manifest, native=native, node=node)
    member = (
        shipped() if f"release_inventory_component_missing:node:node@{node}" in missing else None
    )
    if member is None:
        return [], missing
    record = declare_locked_node(
        documents,
        member=member[0],
        digest=member[1],
        locked=locked(),
        version=node,
        creator=creator,
    )
    return [record], missing_components(documents[1], manifest, native=native, node=node)


def declare_locked_node(
    documents: tuple[dict, dict],
    *,
    member: str,
    digest: str,
    locked: str,
    version: str,
    creator: str,
) -> dict[str, str]:
    """Declare the shipped Node in both inventories from the locked supply that vouches for it.

    The record carries Syft's identity fields, so Grype matches it by the same CPE, and names its
    declarer. The shipped file is no longer an unidentified executable, as Syft marks one it found.
    """
    if digest != locked:
        message = "release_inventory_component_unverified:node"
        raise RuntimeError(message)
    spdx, inventory = documents
    path = "/" + member
    identity = hashlib.sha256(f"{_DECLARER}/node/{version}/{member}".encode()).hexdigest()[:16]
    cpe = f"cpe:2.3:a:nodejs:node.js:{version}:*:*:*:*:*:*:*"
    purl = f"pkg:generic/node@{version}"
    inventory.setdefault("artifacts", []).append(
        {
            "id": identity,
            "name": "node",
            "version": version,
            "type": "binary",
            "foundBy": _DECLARER,
            "locations": [
                {"path": path, "accessPath": path, "annotations": {"evidence": "primary"}}
            ],
            "licenses": [],
            "language": "",
            "cpes": [{"cpe": cpe, "source": "nvd-cpe-dictionary"}],
            "purl": purl,
        }
    )
    edges = inventory.setdefault("artifactRelationships", [])
    if parent := (inventory.get("source") or {}).get("id"):
        edges.append({"parent": parent, "child": identity, "type": "contains"})
    for item in _sequence(inventory, "files"):
        if isinstance(item, dict) and (item.get("location") or {}).get("path") == path:
            notes = [note for note in item.get("unknowns") or () if _UNIDENTIFIED not in note]
            item.pop("unknowns", None)
            item.update({"unknowns": notes} if notes else {})
            evidence = {"kind": "primary"}
            edges.append(
                {
                    "parent": identity,
                    "child": item["id"],
                    "type": "evident-by",
                    "metadata": evidence,
                }
            )
    package = f"SPDXRef-Package-binary-node-{identity}"
    spdx.setdefault("packages", []).append(
        {
            "name": "node",
            "SPDXID": package,
            "versionInfo": version,
            "supplier": "NOASSERTION",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
            "sourceInfo": f"declared by ETHOS from its locked Node supply: {path}",
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "SECURITY",
                    "referenceType": "cpe23Type",
                    "referenceLocator": cpe,
                },
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": purl,
                },
            ],
        }
    )
    relationships = spdx.setdefault("relationships", [])
    roots = [
        relation.get("relatedSpdxElement")
        for relation in relationships
        if relation.get("spdxElementId") == "SPDXRef-DOCUMENT"
        and relation.get("relationshipType") == "DESCRIBES"
    ]
    relationships.extend(
        {"spdxElementId": root, "relatedSpdxElement": package, "relationshipType": "CONTAINS"}
        for root in roots
    )
    relationships.extend(
        {
            "spdxElementId": package,
            "relatedSpdxElement": item["SPDXID"],
            "relationshipType": "OTHER",
            "comment": "evident-by: indicates the package's existence is evident by the given file",
        }
        for item in _sequence(spdx, "files")
        if isinstance(item, dict) and item.get("fileName") == member
    )
    creators = spdx.setdefault("creationInfo", {}).setdefault("creators", [])
    if f"Tool: {creator}" not in creators:
        creators.append(f"Tool: {creator}")
    return {
        "name": "node",
        "version": version,
        "path": member,
        "sha256": digest,
        "source": "locked Node supply",
    }


def locked_node_digest(runtime: str) -> str:
    """Return the SHA-256 of the locked Node executable for the archive's runtime platform."""
    supply = NodeSupply.read(ROOT)
    if supply.target != runtime:
        message = "release_inventory_component_unverified:node"
        raise RuntimeError(message)
    directory = materialize_tool(ROOT, "node")
    return _sha256(directory / ("node.exe" if runtime.startswith("windows-") else "node"))


def run(session: nox.Session) -> None:
    """Catalog the archive the install smoke kept and record the inventories' bounded claims."""
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--host")
    options, _ = parser.parse_known_args(tuple(session.posargs))
    policy = tomllib.loads(POLICY.read_text(encoding="utf-8"))
    smoke = ROOT / str(policy["release_smoke" if options.host else "smoke"])
    distribution = json.loads(smoke.read_text(encoding="utf-8"))["distribution"]
    archive = (
        ROOT
        / "build/artifacts/native"
        / str(distribution["runtime_digest"])
        / PureWindowsPath(str(distribution["path"])).name
    )
    digest = _sha256(archive)
    if digest != distribution["sha256"]:
        message = "release_inventory_archive_mismatch"
        raise RuntimeError(message)
    runtime = f"{_SYSTEMS[distribution['platform']]}-{_MACHINES[distribution['architecture']]}"
    host = options.host or runtime
    name = f"ethos-{distribution['product_version']}-{host}.tar.gz"
    outputs = (ROOT / str(policy["spdx"]), ROOT / str(policy["syft"]))
    config = ROOT / "build/runtime/work/release-sbom/syft.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    # YAML is a superset of JSON, so the policy's table is Syft's whole explicit configuration.
    config.write_text(json.dumps(policy["syft_config"], indent=2) + "\n", encoding="utf-8")
    supply = NativeSupply.read(ROOT, "syft")
    syft = native_syft(materialize_tool(ROOT, "syft") / supply.executable_name)
    spdx, inventory = catalog(archive, name=name, outputs=outputs, config=config, run=syft)
    manifest = _manifest(archive)
    tools = {
        match[1]
        for path in _sequence(manifest, "runtime_files")
        if (match := _NATIVE.search(str(path)))
    }
    native = {tool: NativeSupply.read(ROOT, tool).version for tool in tools & set(NATIVE_BACKENDS)}
    node = NodeSupply.read(ROOT).version
    declared, missing = complete_inventory(
        (spdx, inventory),
        manifest,
        native=native,
        node=node,
        shipped=lambda: shipped_node(archive),
        locked=lambda: locked_node_digest(runtime),
        creator=f"ethos-{distribution['product_version']}",
    )
    if missing:
        raise RuntimeError(",".join(missing[:20]))
    if declared:
        for path, document in zip(outputs, (spdx, inventory), strict=True):
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    payload = {
        "schema_version": 2,
        "kind": "ethos_release_supply_chain_evidence",
        "verdict": "pass",
        "head": current_tracked_head(ROOT),
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact": {"name": name, "sha256": digest},
        "inventories": {
            path.name: {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
            for path in outputs
        },
        "expected": {
            "native": native,
            "node": node,
            "python": sum(
                1 for path in _sequence(manifest, "runtime_files") if _DIST.search(str(path))
            ),
        },
        "declared": declared,
        "generator": {"tool": "syft", "version": supply.version, "config": policy["syft_config"]},
        "not_claimed": policy["boundary"]["not_claimed"],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output = ROOT / str(policy["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    session.log(rendered)


def shipped_node(archive: Path) -> tuple[str, str] | None:
    """Return the archive's Node executable and its SHA-256, if the runtime ships one."""
    with tarfile.open(archive) as packed:
        for member in packed:
            if member.isfile() and _RUNTIME.match(member.name) and _NODE.search(member.name):
                stream = packed.extractfile(member)
                if stream is not None:
                    return member.name, hashlib.file_digest(stream, "sha256").hexdigest()
    return None


def _manifest(archive: Path) -> dict:
    with tarfile.open(archive) as packed:
        names = [name for name in packed.getnames() if _MANIFEST.fullmatch(name)]
        member = packed.extractfile(names[0]) if len(names) == 1 else None
        if member is None:
            message = "release_inventory_manifest_missing"
            raise RuntimeError(message)
        return json.load(member)


def _sequence(document: Mapping[str, object], key: str) -> list[object]:
    value = document.get(key)
    return list(value) if isinstance(value, (dict, list, tuple)) else []


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
