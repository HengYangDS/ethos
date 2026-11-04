"""Runtime inventories owned by the repository Nox graph: one Syft run over the kept archive.

The install smoke keeps each runtime archive it qualified and records its SHA-256. One Syft run
reads that archive's bytes under its published name and writes two inventories: an SPDX 2.3 SBOM,
which consumers read, and a Syft JSON inventory that captures Go symbols, which binary scans
read. Both must name the archive and its digest, and hold every component that the runtime's
owners declare: the bundled Go tools, uv, Node and each shipped Python distribution.
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
    host = options.host or (
        f"{_SYSTEMS[distribution['platform']]}-{_MACHINES[distribution['architecture']]}"
    )
    name = f"ethos-{distribution['product_version']}-{host}.tar.gz"
    outputs = (ROOT / str(policy["spdx"]), ROOT / str(policy["syft"]))
    config = ROOT / "build/runtime/work/release-sbom/syft.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    # YAML is a superset of JSON, so the policy's table is Syft's whole explicit configuration.
    config.write_text(json.dumps(policy["syft_config"], indent=2) + "\n", encoding="utf-8")
    supply = NativeSupply.read(ROOT, "syft")
    syft = native_syft(materialize_tool(ROOT, "syft") / supply.executable_name)
    _spdx, inventory = catalog(archive, name=name, outputs=outputs, config=config, run=syft)
    manifest = _manifest(archive)
    tools = {
        match[1]
        for path in _sequence(manifest, "runtime_files")
        if (match := _NATIVE.search(str(path)))
    }
    native = {tool: NativeSupply.read(ROOT, tool).version for tool in tools & set(NATIVE_BACKENDS)}
    node = NodeSupply.read(ROOT).version
    if missing := missing_components(inventory, manifest, native=native, node=node):
        raise RuntimeError(",".join(missing[:20]))
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
        "generator": {"tool": "syft", "version": supply.version, "config": policy["syft_config"]},
        "not_claimed": policy["boundary"]["not_claimed"],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output = ROOT / str(policy["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    session.log(rendered)


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
