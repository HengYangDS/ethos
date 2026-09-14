"""Exercise archive projection closure without turning derived bytes into authority."""

import hashlib
import json
from pathlib import Path

import pytest

from ethos.adapters.openspec.archive_projection import archive_projection_updates
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.archive_projection import refresh_archive_projections
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.repository.policy.projections import render_source_bindings
from ethos.repository.policy.projections import source_binding_inputs
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_normalize_projected_specs_changes_only_terminal_newlines(tmp_path: Path) -> None:
    root = tmp_path
    projected = root / "openspec/specs/contracts/spec.md"
    projected.parent.mkdir(parents=True)
    original = b"## Purpose\n\nKeep interior spacing.  \n\n## Requirements\n\nBody.\n\n\n"
    projected.write_bytes(original)
    archived = root / "openspec/changes/archive/2026-08-08-change/spec.md"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"archived carrier\n\n")
    binary = root / "openspec/specs/contracts/fixture.bin"
    binary.write_bytes(b"\xff\x00\n\n")

    normalized = normalize_projected_specs(
        root,
        paths=(
            "openspec/specs/contracts/spec.md",
            "openspec/changes/archive/2026-08-08-change/spec.md",
            "openspec/specs/contracts/fixture.bin",
        ),
    )

    assert normalized == ("openspec/specs/contracts/spec.md",)
    assert projected.read_bytes() == original.rstrip(b"\n") + b"\n"
    assert archived.read_bytes() == b"archived carrier\n\n"
    assert binary.read_bytes() == b"\xff\x00\n\n"


def _bound_projection(root: Path) -> tuple[Path, Path, Path]:
    source = root / "openspec/specs/contracts/spec.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"before\n")
    declaration = root / "system/projections/terminal-architecture/declaration.json"
    declaration.parent.mkdir(parents=True)
    graph = declaration.with_name("semantic-graph.json")
    binding = {"path": source.relative_to(root).as_posix(), "authority": "contract"}
    declaration.write_text(
        json.dumps(
            {
                "schema": "ethos.projection-declaration/v1",
                "sources": [{"id": "contract", **binding}],
                "documents": {"semantic_graph": graph.relative_to(root).as_posix()},
            }
        )
        + "\n"
    )
    graph.write_text(
        json.dumps(
            {
                "sources": {
                    "contract": {**binding, "sha256": hashlib.sha256(b"before\n").hexdigest()}
                },
                "nodes": {"intent": {"label": "Preserve authored meaning"}},
            },
            indent=2,
        )
        + "\n"
    )
    return source, declaration, graph


@pytest.mark.parametrize(
    "state", ["valid", "no_change", "stale", "missing", "declaration", "overlay"]
)
def test_archive_binding_update_is_exact_and_preserves_preexisting_content(
    tmp_path: Path, state: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    source, declaration, graph = _bound_projection(root)
    if state == "stale":
        graph.write_text(
            graph.read_text().replace(hashlib.sha256(b"before\n").hexdigest(), "0" * 64)
        )
    head = commit_fixture(root, "declare projection")
    original_graph = graph.read_bytes()
    if state != "no_change":
        source.write_bytes(b"after\n")
    if state == "missing":
        source.unlink()
    elif state == "declaration":
        declaration.write_bytes(declaration.read_bytes() + b"\n")
    elif state == "overlay":
        graph.write_text(graph.read_text().replace("Preserve authored meaning", "author's edit"))
    overlay = graph.read_bytes()
    expected = {
        "stale": "source digest mismatch",
        "missing": "archive_projection_input_unavailable",
        "declaration": "archive_projection_declaration_changed",
        "overlay": "archive_projection_preimage_changed",
    }
    if state in expected:
        with pytest.raises(ValueError, match=expected[state]):
            refresh_archive_projections(root, source_head=head)
        assert graph.read_bytes() == overlay
    else:
        refresh_archive_projections(root, source_head=head)
        actual = graph.read_bytes()
        if state == "no_change":
            assert actual == original_graph
        else:
            assert (
                json.loads(actual)["sources"]["contract"]["sha256"]
                == hashlib.sha256(b"after\n").hexdigest()
            )
            assert json.loads(actual)["nodes"] == json.loads(original_graph)["nodes"]


@pytest.mark.parametrize(
    "fault", ["schema", "sources", "entry", "id", "duplicate", "authority", "path", "output"]
)
def test_source_binding_declaration_rejects_ambiguous_or_uncontained_inputs(
    tmp_path: Path, fault: str
) -> None:
    _source, declaration, _graph = _bound_projection(tmp_path)
    value = json.loads(declaration.read_bytes())
    if fault == "schema":
        value["schema"] = "unrecognized"
    elif fault == "sources":
        value["sources"] = []
    elif fault == "entry":
        value["sources"] = [None]
    elif fault == "duplicate":
        value["sources"].append(value["sources"][0])
    elif fault in {"id", "authority"}:
        value["sources"][0][fault] = ""
    elif fault == "output":
        value["sources"][0]["path"] = value["documents"]["semantic_graph"]
    else:
        value["sources"][0]["path"] = "../outside"
    with pytest.raises((TypeError, ValueError)):
        source_binding_inputs(json.dumps(value).encode())


@pytest.mark.parametrize(
    "fault", ["graph", "row", "missing-before", "missing-after", "authority", "digest", "noop"]
)
def test_source_binding_renderer_fails_closed_without_certifying_meaning(
    tmp_path: Path, fault: str
) -> None:
    source, declaration, graph = _bound_projection(tmp_path)
    _output, bindings = source_binding_inputs(declaration.read_bytes())
    before = {source.relative_to(tmp_path).as_posix(): b"before\n"}
    after = dict(before)
    content = graph.read_bytes()
    value = json.loads(content)
    if fault == "graph":
        value["sources"] = {}
    elif fault == "row":
        value["sources"]["contract"] = None
    elif fault == "missing-before":
        before = {}
    elif fault == "missing-after":
        after = {}
    elif fault in {"authority", "digest"}:
        value["sources"]["contract"]["authority" if fault == "authority" else "sha256"] = (
            "different"
        )
    if fault == "noop":
        assert render_source_bindings(content, bindings, before, after) == content
    else:
        with pytest.raises((TypeError, ValueError)):
            render_source_bindings(json.dumps(value).encode(), bindings, before, after)


def test_archive_projection_does_not_admit_a_nonarchive_source_change(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    source, declaration, graph = _bound_projection(root)
    outside = root / "README.md"
    value = json.loads(declaration.read_text())
    value["sources"][0]["path"] = outside.relative_to(root).as_posix()
    declaration.write_text(json.dumps(value))
    value = json.loads(graph.read_text())
    value["sources"]["contract"].update(
        path=outside.relative_to(root).as_posix(),
        sha256=hashlib.sha256(outside.read_bytes()).hexdigest(),
    )
    graph.write_text(json.dumps(value))
    head = commit_fixture(root, "declare nonarchive source")
    source.write_bytes(b"after\n")
    outside.write_bytes(b"unrelated change\n")
    with (
        observe_worktree_postimage(root, previous=head) as image,
        pytest.raises(ValueError, match="archive_projection_input_outside_effect"),
    ):
        archive_projection_updates(
            root,
            source_head=head,
            tree=image.tree,
            changed_paths=image.changed_paths,
            environment=image.environment,
        )


def test_absent_projection_is_a_noop_but_unobservable_git_is_not(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    refresh_archive_projections(root, source_head=head)
    with pytest.raises(ValueError, match="archive_projection_declaration_unavailable"):
        refresh_archive_projections(root, source_head="unavailable")
