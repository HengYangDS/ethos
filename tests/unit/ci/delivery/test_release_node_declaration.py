"""A locked executable that the catalog misses is declared from its supply, bound to its bytes."""

from __future__ import annotations

import copy
import hashlib
import tarfile

import pytest

from ethos.adapters.repo.runtime.materialization.native_supply import NativeSupply
from tests.support.release_legs import inventory_documents
from tools.ci import release_supply_chain

_VERSION = "26.13.0"
_RUNTIME = "ethos/runtime/0123456789abcdef/"
_NODE = "python/Lib/site-packages/ethos/resources/node/node.exe"
_MEMBER = _RUNTIME + _NODE
_DIGEST = hashlib.sha256(b"node.exe").hexdigest()
_UNKNOWN = "unknowns-labeler: no package identified in executable file"
_CREATOR = "ethos-0.2.0-beta.4"


def _documents(*, cataloged: bool = False) -> tuple[dict, dict]:
    """Return a Windows archive's inventories as Syft writes them, with or without Node."""
    spdx, syft = inventory_documents("ethos-x-windows-x64.tar.gz", "a" * 64)
    spdx["creationInfo"] = {"creators": ["Tool: syft-1.56.0"]}
    spdx["files"] = [{"fileName": _MEMBER, "SPDXID": "SPDXRef-File-node-exe"}]
    syft["source"]["id"] = "source-id"
    syft["artifactRelationships"] = []
    location = {"path": "/" + _MEMBER}
    syft["files"] = [{"id": "file-id", "location": location, "unknowns": [_UNKNOWN]}]
    if cataloged:
        node = {"name": "node", "version": _VERSION, "type": "binary", "locations": [location]}
        syft["artifacts"].append(node)
        syft["files"][0].pop("unknowns")
    return spdx, syft


def _unexpected() -> str:
    pytest.fail("a cataloged Node consulted the archive or the locked supply")


def _complete(
    documents, manifest=None, *, locked=lambda: _DIGEST, shipped=lambda: (_MEMBER, _DIGEST)
):
    return release_supply_chain.complete_inventory(
        documents,
        manifest or {"runtime_files": {_NODE: ""}},
        native={},
        node=_VERSION,
        shipped=shipped,
        locked=locked,
        creator=_CREATOR,
    )


def test_a_locked_node_that_the_catalog_misses_is_declared_in_both_inventories():
    """Both inventories name Node by Syft's identity fields, and the file is identified."""
    spdx, syft = documents = _documents()
    record = {
        "name": "node",
        "version": _VERSION,
        "path": _MEMBER,
        "sha256": _DIGEST,
        "source": "locked Node supply",
    }
    assert _complete(documents) == ([record], [])
    artifact = next(item for item in syft["artifacts"] if item["name"] == "node")
    assert (artifact["type"], artifact["foundBy"]) == ("binary", "ethos-locked-supply")
    assert artifact["purl"] == f"pkg:generic/node@{_VERSION}"
    cpe = f"cpe:2.3:a:nodejs:node.js:{_VERSION}:*:*:*:*:*:*:*"
    assert artifact["cpes"] == [{"cpe": cpe, "source": "nvd-cpe-dictionary"}]
    assert [location["path"] for location in artifact["locations"]] == ["/" + _MEMBER]
    edges = syft["artifactRelationships"]
    assert {"parent": "source-id", "child": artifact["id"], "type": "contains"} in edges
    evident = {"parent": artifact["id"], "child": "file-id", "type": "evident-by"}
    assert evident | {"metadata": {"kind": "primary"}} in edges
    assert "unknowns" not in syft["files"][0]
    package = next(item for item in spdx["packages"] if item["name"] == "node")
    assert package["checksums"] == [{"algorithm": "SHA256", "checksumValue": _DIGEST}]
    assert "locked Node supply" in package["sourceInfo"]
    pairs = {(edge["spdxElementId"], edge["relatedSpdxElement"]) for edge in spdx["relationships"]}
    assert ("SPDXRef-DocumentRoot-File-archive", package["SPDXID"]) in pairs
    assert (package["SPDXID"], "SPDXRef-File-node-exe") in pairs
    assert f"Tool: {_CREATOR}" in spdx["creationInfo"]["creators"]


def test_a_shipped_node_that_differs_from_its_supply_refuses():
    """A declaration vouches only for the locked bytes; any other executable stops the leg."""
    documents = _documents()
    before = copy.deepcopy(documents)
    with pytest.raises(RuntimeError, match="release_inventory_component_unverified:node"):
        _complete(documents, locked=lambda: "0" * 64)
    assert documents == before


def test_a_cataloged_node_is_not_declared_again():
    """Once the catalog finds Node, neither the archive nor the locked supply is consulted."""
    documents = _documents(cataloged=True)
    before = copy.deepcopy(documents)
    assert _complete(documents, locked=_unexpected, shipped=_unexpected) == ([], [])
    assert documents == before


def test_another_missing_component_still_refuses_without_a_declaration():
    """Only Node has a locked supply that vouches for it; any other gap is named as before."""
    ruff = "python/Lib/site-packages/ruff-0.15.2.dist-info/METADATA"
    manifest = {"runtime_files": {_NODE: "", ruff: ""}}
    found = _complete(_documents(cataloged=True), manifest, locked=_unexpected, shipped=_unexpected)
    assert found == ([], ["release_inventory_component_missing:python:ruff@0.15.2"])


def test_the_locked_node_must_serve_the_archives_runtime(monkeypatch):
    """The supply that vouches is the one for the archive's platform, never another host's."""

    class Supply:
        target = "linux-x64"

    def read(_cls, _root):
        return Supply()

    monkeypatch.setattr(release_supply_chain.NodeSupply, "read", classmethod(read))
    with pytest.raises(RuntimeError, match="release_inventory_component_unverified:node"):
        release_supply_chain.locked_node_digest("windows-x64")


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


def test_the_declaration_is_rechecked_when_syft_changes():
    """Syft 1.56.0 matches Node only in a file named `node`, so a new Syft must be checked again.

    When the locked Syft classifies `node.exe`, `complete_inventory` never declares, and its
    declaration path is removed in that supply move; otherwise this version moves with it.
    """
    assert NativeSupply.read(release_supply_chain.ROOT, "syft").version == "1.56.0"
