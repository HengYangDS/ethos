from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPORTER_PATH = REPOSITORY_ROOT / "tools/projection/export_terminal_architecture.py"
SCHEMA_PATH = REPOSITORY_ROOT / "system/schemas/projection-input.schema.json"


def _load_exporter():
    spec = importlib.util.spec_from_file_location("terminal_projection_exporter", EXPORTER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _fixture_repository(tmp_path: Path, *, effect_authority: bool = False) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "projection@example.invalid")
    _git(root, "config", "user.name", "Projection Fixture")

    source_path = root / "docs/source.md"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("bounded source assertion\n", encoding="utf-8")
    source_digest = _sha256(source_path.read_bytes())

    semantic_graph = {
        "schema": "ethos.terminal-semantic-graph/v1",
        "sources": {
            "source": {
                "path": "docs/source.md",
                "authority": "fixture semantic authority",
                "sha256": source_digest,
            }
        },
        "nodes": {
            "intent": {
                "kind": "semantic_root",
                "label": "Intent",
                "evidence": ["source"],
            },
            "effect": {
                "kind": "effect",
                "label": "Effect",
                "evidence": ["source"],
            },
        },
        "edges": [
            {
                "id": "intent-to-effect",
                "from": "intent",
                "to": "effect",
                "kind": "constrains",
                "source_ids": ["source"],
            }
        ],
    }
    view_profile = {
        "node_projection": {
            "intent": {"view_id": "intent", "mode": "direct"},
        },
        "omitted_nodes": {
            "effect": {"reason": "The fixture renderer intentionally omits effects."},
        },
        "edge_projection": {},
        "omitted_edges": {
            "intent-to-effect": {"reason": "The omitted endpoint makes the edge absent."},
        },
    }
    declaration = {
        "schema": "ethos.projection-declaration/v1",
        "id": "fixture-terminal",
        "title": "Fixture Terminal",
        "authority": {
            "semantic_owner": "docs/source.md",
            "scope": "lossless visual assertion selection",
            "effect_authority": effect_authority,
        },
        "sources": [
            {
                "id": "source",
                "path": "docs/source.md",
                "authority": "fixture semantic authority",
            }
        ],
        "documents": {
            "semantic_graph": "system/projections/terminal-architecture/semantic-graph.json",
            "copy": "system/projections/terminal-architecture/copy.json",
            "view_profile": "system/projections/terminal-architecture/view-profile.json",
            "quality_contract": "system/projections/terminal-architecture/quality-contract.yaml",
        },
    }
    projection_root = root / "system/projections/terminal-architecture"
    _write_json(projection_root / "declaration.json", declaration)
    _write_json(projection_root / "semantic-graph.json", semantic_graph)
    _write_json(
        projection_root / "copy.json", {"schema": "fixture.copy/v1", "title": "Fixture Terminal"}
    )
    _write_json(projection_root / "view-profile.json", view_profile)
    (projection_root / "quality-contract.yaml").write_text(
        "schema: fixture.quality/v1\n", encoding="utf-8"
    )

    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root, _git(root, "rev-parse", "HEAD")


def test_export_is_exact_tree_bound_deterministic_and_host_path_free(tmp_path: Path) -> None:
    exporter = _load_exporter()
    root, commit = _fixture_repository(tmp_path)
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}")
    committed_source = subprocess.run(
        ["git", "show", f"{commit}:docs/source.md"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    (root / "docs/source.md").write_text("uncommitted drift\n", encoding="utf-8")

    first = exporter.export_projection_input(root=root, revision=commit)
    second = exporter.export_projection_input(root=root, revision=commit)

    assert first == second
    assert first["source"]["revision"] == commit
    assert first["source"]["git"] == {"commit": commit, "tree": tree}
    assert first["source"]["bindings"][0]["sha256"] == _sha256(committed_source)
    assert str(tmp_path) not in json.dumps(first)
    digest = first.pop("digest")
    assert digest == _sha256(_canonical_bytes(first))


def test_export_validates_the_projection_input_schema(tmp_path: Path) -> None:
    exporter = _load_exporter()
    root, commit = _fixture_repository(tmp_path)
    exported = exporter.export_projection_input(root=root, revision=commit)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(exported)
    assert exported["documents"]["copy"]["title"] == "Fixture Terminal"
    assert exported["documents"]["quality_contract"] == "schema: fixture.quality/v1\n"
    assert "assertion" not in exported["semantics"]["nodes"]["intent"]
    assert "assertion" not in exported["semantics"]["relations"][0]


def test_export_fails_closed_on_stale_or_missing_exact_tree_sources(tmp_path: Path) -> None:
    exporter = _load_exporter()
    root, commit = _fixture_repository(tmp_path)
    graph_path = root / "system/projections/terminal-architecture/semantic-graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["sources"]["source"]["sha256"] = "0" * 64
    _write_json(graph_path, graph)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "stale binding")

    with pytest.raises(ValueError, match="source digest mismatch"):
        exporter.export_projection_input(root=root, revision="HEAD")

    with pytest.raises(ValueError, match="does not exist in the selected Git tree"):
        exporter.export_projection_input(
            root=root, revision=commit, declaration_path="missing.json"
        )


def test_projection_declaration_cannot_own_repository_effect_authority(tmp_path: Path) -> None:
    exporter = _load_exporter()
    root, _commit = _fixture_repository(tmp_path, effect_authority=True)

    with pytest.raises(ValueError, match="effect authority"):
        exporter.export_projection_input(root=root, revision="HEAD")
