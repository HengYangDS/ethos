"""Export the ETHOS terminal architecture input from one exact Git tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath
from types import ModuleType
from typing import Any
from typing import NoReturn

DEFAULT_DECLARATION = "system/projections/terminal-architecture/declaration.json"


class ProjectionExportError(ValueError):
    """Signal an invalid or stale projection export input."""


def _fail(message: str) -> NoReturn:
    raise ProjectionExportError(message)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        _fail(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.decode().strip()


def _repository_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        _fail(f"projection path must be repository-relative: {value}")
    return path.as_posix()


def _tree_bytes(root: Path, commit: str, path: str) -> bytes:
    relative = _repository_path(path)
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        _fail(f"{relative} does not exist in the selected Git tree {commit}")
    return result.stdout


def _json(bytes_value: bytes, *, path: str) -> dict[str, Any]:
    try:
        value = json.loads(bytes_value)
    except json.JSONDecodeError as error:
        message = f"{path} is not valid JSON: {error}"
        raise ProjectionExportError(message) from error
    if not isinstance(value, dict):
        _fail(f"{path} must contain a JSON object")
    return value


def _canonical_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{text}\n".encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _required_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be non-empty text")
    return value


def _validate_source_alignment(
    root: Path,
    commit: str,
    declaration: dict[str, Any],
    semantic_graph: dict[str, Any],
    quality_contract: str,
) -> list[dict[str, str]]:
    """Use the selected tree's pure owner, even in an isolated stdlib consumer."""
    owner_path = "src/ethos/repository/policy/projections.py"
    code = _tree_bytes(root, commit, owner_path)
    name = f"_ethos_projection_owner_{commit}"
    owner = ModuleType(name)
    previous = sys.modules.get(name)
    sys.modules[name] = owner
    try:
        exec(compile(code, f"{commit}:{owner_path}", "exec"), owner.__dict__)
        _output, bindings = owner.source_binding_inputs(_canonical_bytes(declaration))
        sources = {
            binding["path"]: _tree_bytes(root, commit, binding["path"])
            for binding in bindings.values()
        }
        owner.validate_source_bindings(semantic_graph, bindings, sources)
        validate_assurance = getattr(owner, "validate_projection_assurance", None)
        if not callable(validate_assurance):
            _fail("projection_assurance_owner_missing")
        validate_assurance(quality_contract, semantic_graph, bindings)
        return [
            {"id": identity, **binding, "sha256": _sha256(sources[binding["path"]])}
            for identity, binding in sorted(bindings.items())
        ]
    except (TypeError, ValueError) as error:
        raise ProjectionExportError(str(error)) from error
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


def _provenance(value: object, known: set[str], *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        _fail(f"{label} must carry source provenance")
    result = [_required_text(item, f"{label} provenance") for item in value]
    if any(item not in known for item in result):
        _fail(f"{label} references an undeclared source")
    return result


def _disposition(identity: str, projected: object, omitted: object, *, kind: str) -> dict[str, Any]:
    if (projected is None) == (omitted is None):
        _fail(f"{kind} {identity} must have exactly one projection disposition")
    if projected is not None:
        return {"project": _required_mapping(projected, f"{kind} {identity} projection")}
    omission = _required_mapping(omitted, f"{kind} {identity} omission")
    reason = _required_text(omission.get("reason"), f"{kind} {identity} absence reason")
    return {"omit": True, "reason": reason}


def _nodes(
    semantic_graph: dict[str, Any],
    view_profile: dict[str, Any],
    known_sources: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    graph_nodes = _required_mapping(semantic_graph.get("nodes"), "semantic nodes")
    projected = _required_mapping(view_profile.get("node_projection"), "node projection")
    omitted = _required_mapping(view_profile.get("omitted_nodes"), "omitted nodes")
    nodes: dict[str, dict[str, Any]] = {}
    owners: dict[str, dict[str, Any]] = {}
    for identity, value in graph_nodes.items():
        node = _required_mapping(value, f"semantic node {identity}")
        nodes[identity] = {
            "label": _required_text(node.get("label"), f"node {identity} label"),
            "kind": _required_text(node.get("kind"), f"node {identity} kind"),
            "provenance": _provenance(
                node.get("evidence"), known_sources, label=f"node {identity}"
            ),
            "attributes": {
                key: item for key, item in node.items() if key not in {"label", "kind", "evidence"}
            },
        }
        owners[identity] = _disposition(
            identity, projected.get(identity), omitted.get(identity), kind="node"
        )
    return nodes, owners


def _relations(
    semantic_graph: dict[str, Any],
    view_profile: dict[str, Any],
    known_sources: set[str],
    node_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    graph_edges = semantic_graph.get("edges")
    if not isinstance(graph_edges, list):
        _fail("semantic graph edges must be an array")
    projected = _required_mapping(view_profile.get("edge_projection"), "edge projection")
    omitted = _required_mapping(view_profile.get("omitted_edges"), "omitted edges")
    relations: list[dict[str, Any]] = []
    owners: dict[str, dict[str, Any]] = {}
    for value in graph_edges:
        edge = _required_mapping(value, "semantic relation")
        identity = _required_text(edge.get("id"), "semantic relation identity")
        if identity in owners:
            _fail(f"duplicate relation identity: {identity}")
        from_identity = _required_text(edge.get("from"), f"relation {identity} source")
        to_identity = _required_text(edge.get("to"), f"relation {identity} target")
        if from_identity not in node_ids or to_identity not in node_ids:
            _fail(f"relation {identity} references an unknown endpoint")
        relations.append(
            {
                "id": identity,
                "from": from_identity,
                "to": to_identity,
                "kind": _required_text(edge.get("kind"), f"relation {identity} kind"),
                "provenance": _provenance(
                    edge.get("source_ids"), known_sources, label=f"relation {identity}"
                ),
                "attributes": {
                    key: item
                    for key, item in edge.items()
                    if key not in {"id", "from", "to", "kind", "source_ids"}
                },
            }
        )
        owners[identity] = _disposition(
            identity, projected.get(identity), omitted.get(identity), kind="relation"
        )
    return relations, owners


def _validate_required_witnesses(
    graph: dict[str, Any], profile: dict[str, Any], copy: dict[str, Any]
) -> None:
    """Validate declared static obligations, not renderer visibility or meaning."""
    assertions = _required_mapping(copy.get("assertions", {}), "copy assertions")
    for identity in profile.get("meta", {}).get("required_visible_copy", []):
        _static_witness(assertions, identity, f"view {identity}")
    groups = (
        ("node", graph["nodes"].items(), "node_projection", "omitted_nodes"),
        (
            "relation",
            ((item["id"], item) for item in graph["edges"]),
            "edge_projection",
            "omitted_edges",
        ),
        (
            "invariant",
            ((item["id"], item) for item in graph.get("invariants", [])),
            "invariant_projection",
            "omitted_invariants",
        ),
    )
    for kind, items, projected_key, omitted_key in groups:
        projected = _required_mapping(profile.get(projected_key, {}), projected_key)
        omitted = _required_mapping(profile.get(omitted_key, {}), omitted_key)
        for identity, item in items:
            if not item.get("required_visible", False):
                continue
            projection = projected.get(identity, {})
            if identity in omitted or not isinstance(projection, dict):
                _fail(f"required {kind} {identity} needs a main-static copy witness")
            _static_witness(assertions, projection.get("witness"), f"{kind} {identity}")


def _static_witness(assertions: dict[str, Any], identity: object, label: str) -> None:
    witness = assertions.get(identity) if isinstance(identity, str) else None
    if (
        not isinstance(witness, dict)
        or witness.get("surface") != "main-static"
        or not isinstance(witness.get("text"), str)
        or not witness["text"].strip()
    ):
        _fail(f"required {label} needs a main-static copy witness")


def _projection_input(
    declaration: dict[str, Any],
    semantic_graph: dict[str, Any],
    view_profile: dict[str, Any],
    *,
    commit: str,
    tree: str,
    bindings: list[dict[str, str]],
    documents: list[dict[str, str]],
    copy: dict[str, Any],
    quality_contract: str,
) -> dict[str, Any]:
    authority = _required_mapping(declaration.get("authority"), "projection authority")
    if authority.get("effect_authority") is not False:
        _fail("projection declaration cannot own repository effect authority")
    known_sources = {item["id"] for item in bindings}
    _validate_required_witnesses(semantic_graph, view_profile, copy)
    nodes, node_owners = _nodes(semantic_graph, view_profile, known_sources)
    relations, relation_owners = _relations(semantic_graph, view_profile, known_sources, set(nodes))
    return {
        "schema": "projection.input/v2",
        "title": _required_text(declaration.get("title"), "projection title"),
        "authority": {
            "semantic_owner": _required_text(
                authority.get("semantic_owner"), "projection semantic owner"
            ),
            "scope": _required_text(authority.get("scope"), "projection authority scope"),
            "effect_authority": False,
        },
        "source": {
            "id": _required_text(declaration.get("id"), "projection identity"),
            "revision": commit,
            "git": {"commit": commit, "tree": tree},
            "bindings": bindings,
            "documents": documents,
        },
        "documents": {
            "copy": copy,
            "view_profile": view_profile,
            "quality_contract": quality_contract,
        },
        "semantics": {
            "nodes": nodes,
            "relations": relations,
            "contracts": {
                key: item
                for key, item in semantic_graph.items()
                if key not in {"schema", "sources", "nodes", "edges"}
            },
        },
        "view": {"nodes": node_owners, "relations": relation_owners},
    }


def _documents(
    repository: Path, commit: str, declaration: dict[str, Any]
) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    document_map = _required_mapping(
        declaration.get("documents"), "projection declaration documents"
    )
    required = {"semantic_graph", "copy", "view_profile", "quality_contract"}
    if set(document_map) != required:
        _fail("projection declaration must select the closed document set")
    contents: dict[str, bytes] = {}
    bindings: list[dict[str, str]] = []
    for identity, value in sorted(document_map.items()):
        path = _repository_path(_required_text(value, f"projection document {identity} path"))
        content = _tree_bytes(repository, commit, path)
        contents[identity] = content
        bindings.append({"id": identity, "path": path, "sha256": _sha256(content)})
    return contents, bindings


def export_projection_input(
    *, root: Path, revision: str = "HEAD", declaration_path: str = DEFAULT_DECLARATION
) -> dict[str, Any]:
    """Return a deterministic ProjectionInput bound to one exact Git tree."""
    repository = root.resolve()
    commit = _git(repository, "rev-parse", f"{revision}^{{commit}}")
    tree = _git(repository, "rev-parse", f"{commit}^{{tree}}")
    declaration_relative = _repository_path(declaration_path)
    declaration = _json(
        _tree_bytes(repository, commit, declaration_relative), path=declaration_relative
    )
    if declaration.get("schema") != "ethos.projection-declaration/v1":
        _fail("unsupported projection declaration schema")
    document_bytes, documents = _documents(repository, commit, declaration)
    document_paths = {item["id"]: item["path"] for item in documents}
    semantic_graph = _json(document_bytes["semantic_graph"], path=document_paths["semantic_graph"])
    view_profile = _json(document_bytes["view_profile"], path=document_paths["view_profile"])
    copy = _json(document_bytes["copy"], path=document_paths["copy"])
    quality_contract = document_bytes["quality_contract"].decode("utf-8")
    bindings = _validate_source_alignment(
        repository, commit, declaration, semantic_graph, quality_contract
    )
    output = _projection_input(
        declaration,
        semantic_graph,
        view_profile,
        commit=commit,
        tree=tree,
        bindings=bindings,
        documents=documents,
        copy=copy,
        quality_contract=quality_contract,
    )
    output["digest"] = _sha256(_canonical_bytes(output))
    return output


def main(argv: list[str] | None = None) -> int:
    """Run the exact-tree exporter."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--declaration", default=DEFAULT_DECLARATION)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    try:
        projection_input = export_projection_input(
            root=options.root,
            revision=options.revision,
            declaration_path=options.declaration,
        )
    except ProjectionExportError as error:
        print(str(error), file=sys.stderr)
        return 2
    encoded = _canonical_bytes(projection_input)
    if options.output is None:
        sys.stdout.buffer.write(encoded)
    else:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
