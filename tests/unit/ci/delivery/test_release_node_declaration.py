"""A locked executable that the catalog misses is declared from its supply, bound to its bytes."""

from __future__ import annotations

import copy
import hashlib
import tarfile

import pytest

from tests.support.release_legs import inventory_documents
from tools.ci import release_supply_chain

_VERSION = "26.13.0"
_RUNTIME = "ethos/runtime/0123456789abcdef/"
_NODE = "python/Lib/site-packages/ethos/resources/node/node.exe"
_MEMBER = _RUNTIME + _NODE
_DIGEST = hashlib.sha256(b"node.exe").hexdigest()


def _documents(*, cataloged: bool = False) -> tuple[dict, dict]:
    """Return a Windows archive's inventories as Syft writes them, with or without Node."""
    spdx, syft = inventory_documents("ethos-x-windows-x64.tar.gz", "a" * 64)
    syft["source"]["id"] = "source-id"
    syft["artifactRelationships"] = []
    if cataloged:
        syft["artifacts"].append(
            {"name": "node", "version": _VERSION, "locations": [{"path": "/" + _MEMBER}]}
        )
    return spdx, syft


def _declare(documents: tuple[dict, dict], *, locked: str = _DIGEST):
    return release_supply_chain.declare_locked_node(
        documents, member=_MEMBER, digest=_DIGEST, locked=locked, version=_VERSION
    )


def test_a_locked_node_that_the_catalog_misses_is_declared_in_both_inventories():
    """Both inventories name Node as Syft would, marked as declared from the locked supply."""
    spdx, syft = documents = _documents()
    record = _declare(documents)
    assert record == {
        "name": "node",
        "version": _VERSION,
        "path": _MEMBER,
        "sha256": _DIGEST,
        "source": "locked Node supply",
    }
    artifact = next(item for item in syft["artifacts"] if item["name"] == "node")
    assert artifact["type"] == "binary"
    assert artifact["foundBy"] == "ethos-locked-supply"
    assert artifact["purl"] == f"pkg:generic/node@{_VERSION}"
    assert [cpe["cpe"] for cpe in artifact["cpes"]] == [
        f"cpe:2.3:a:nodejs:node.js:{_VERSION}:*:*:*:*:*:*:*"
    ]
    assert [location["path"] for location in artifact["locations"]] == ["/" + _MEMBER]
    assert {"parent": "source-id", "child": artifact["id"], "type": "contains"} in syft[
        "artifactRelationships"
    ]
    package = next(item for item in spdx["packages"] if item["name"] == "node")
    assert package["versionInfo"] == _VERSION
    assert package["checksums"] == [{"algorithm": "SHA256", "checksumValue": _DIGEST}]
    assert "locked Node supply" in package["sourceInfo"]
    assert {
        "spdxElementId": "SPDXRef-DocumentRoot-File-archive",
        "relatedSpdxElement": package["SPDXID"],
        "relationshipType": "CONTAINS",
    } in spdx["relationships"]
    manifest = {"runtime_files": {_NODE: ""}}
    assert release_supply_chain.missing_components(syft, manifest, native={}, node=_VERSION) == []


def test_a_shipped_node_that_differs_from_its_supply_refuses():
    """A declaration vouches only for the locked bytes; any other executable stops the leg."""
    documents = _documents()
    before = copy.deepcopy(documents)
    with pytest.raises(RuntimeError, match="release_inventory_component_unverified:node"):
        _declare(documents, locked="0" * 64)
    assert documents == before


def test_a_cataloged_node_is_not_declared_again():
    """Once the catalog finds Node at the shipped path, the declaration lapses."""
    documents = _documents(cataloged=True)
    before = copy.deepcopy(documents)
    assert _declare(documents) is None
    assert documents == before


def test_the_shipped_node_is_read_from_the_runtime_inside_the_archive(tmp_path):
    """Only the runtime's Node executable counts; its digest is taken from the archive bytes."""
    archive = tmp_path / "runtime.tar.gz"
    payload = tmp_path / "node.exe"
    payload.write_bytes(b"node.exe")
    with tarfile.open(archive, "w:gz") as packed:
        packed.add(payload, arcname="elsewhere/ethos/resources/node/node.exe")
        packed.add(payload, arcname=_MEMBER)
    assert release_supply_chain.shipped_node(archive) == (_MEMBER, _DIGEST)
    empty = tmp_path / "empty.tar.gz"
    with tarfile.open(empty, "w:gz") as packed:
        packed.add(payload, arcname="elsewhere/ethos/resources/node/node.exe")
    assert release_supply_chain.shipped_node(empty) is None
