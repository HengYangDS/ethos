"""Exercise archive projection closure without turning derived bytes into authority."""

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.openspec.relocation as relocation
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
    original = b"## Purpose\n\nKeep interior spacing.  \n\n## Requirements\n\nBody.\n\n\n"
    contents = {
        "openspec/specs/contracts/spec.md": original,
        "openspec/changes/archive/2026-08-08-change/spec.md": b"archived carrier\n\n",
        "openspec/specs/contracts/fixture.bin": b"\xff\x00\n\n",
    }
    for relative, content in contents.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    assert normalize_projected_specs(tmp_path, paths=tuple(contents)) == (
        "openspec/specs/contracts/spec.md",
    )
    contents["openspec/specs/contracts/spec.md"] = original.rstrip(b"\n") + b"\n"
    assert {path: (tmp_path / path).read_bytes() for path in contents} == contents


def _bound_projection(root: Path) -> tuple[Path, Path, Path]:
    source = root / "openspec/specs/contracts/spec.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"before\n")
    declaration = root / "system/projections/terminal-architecture/declaration.json"
    declaration.parent.mkdir(parents=True)
    graph = declaration.with_name("semantic-graph.json")
    binding = {"path": source.relative_to(root).as_posix(), "authority": "contract"}
    documents = {
        declaration: {
            "schema": "ethos.projection-declaration/v1",
            "sources": [{"id": "contract", **binding}],
            "documents": {"semantic_graph": graph.relative_to(root).as_posix()},
        },
        graph: {
            "sources": {"contract": {**binding, "sha256": hashlib.sha256(b"before\n").hexdigest()}},
            "nodes": {"intent": {"label": "Preserve authored meaning"}},
        },
    }
    for path, content in documents.items():
        path.write_text(json.dumps(content, indent=2) + "\n")
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
            expected_graph = json.loads(original_graph)
            expected_graph["sources"]["contract"]["sha256"] = hashlib.sha256(b"after\n").hexdigest()
            assert json.loads(actual) == expected_graph


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
        field = "authority" if fault == "authority" else "sha256"
        value["sources"]["contract"][field] = "different"
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
    with pytest.raises(ValueError, match="archive_reference_tree_unavailable"):
        relocation.archive_relocation(
            root,
            source_head=head,
            tree="unavailable",
            changed_paths=("openspec/changes/archive/2026-09-18-missing/tasks.md",),
        )


@pytest.mark.parametrize(
    ("body", "expected", "fault"),
    [
        ("[x](../../../docs/target.md?q=1#title)", "[x](../../../../docs/target.md?q=1#title)", ""),
        (
            "![x][asset]\n\n[asset]: <../../../docs/target.md> 'Title'\n",
            "![x][asset]\n\n[asset]: <../../../../docs/target.md> 'Title'\n",
            "",
        ),
        (
            "🎯 [x](../../../docs/file\\(x\\).md)\r\n",
            "🎯 [x](../../../../docs/file%28x%29.md)\r\n",
            "",
        ),
        ("[self](design.md#self) [peer](peer.md)", "[self](design.md#self) [peer](peer.md)", ""),
        ("`[x](../../../missing)`\n\n```md\n[x](../../../missing)\n```\n", None, ""),
        ("[web](https://example.invalid/a) [root](/docs/target.md) [anchor](#a)", None, ""),
        ("[x](../../../docs/missing.md)", None, "target_missing"),
        ("[x](../../../../outside.md)", None, "target_outside_repository"),
        ("[x](../../../docs/%ZZ.md)", None, "encoding_invalid"),
        ("[x](../../../docs/target.md)", None, "postimage_target_missing"),
        ("<img src='../outside.png'>", None, "html_unsupported"),
        ("[x](../../../docs/target.md)", None, "target_kind_unsupported"),
        ("[x](peer.md)", None, "source_kind_unsupported"),
        ("transport", [], "projection_invalid"),
        ("transport", {"documents": "invalid", "canonical": []}, "projection_invalid"),
        ("transport", {"documents": [], "canonical": []}, "projection_invalid"),
        (
            "transport",
            {"documents": [{"path": "outside", "content": ""}], "canonical": []},
            "projection_invalid",
        ),
        ("transport", None, "observation_timeout"),
        ("transport", 1, "observation_failed"),
        ("[x](peer.md)", None, "members_changed"),
        ("[x](peer.md)", None, "content_changed"),
        ("[x](peer.md)", None, "missing_cli"),
    ],
)
def test_archive_reference_destinations_preserve_other_bytes(
    tmp_path, monkeypatch, body, expected, fault
):
    """Real Git projection preserves concrete syntax or rejects the exact missing target."""
    root = init_git_repo(tmp_path / "repo")
    active = root / "openspec/changes/links"
    archived = root / "openspec/changes/archive/2026-09-18-links"
    for relative, content in {
        "docs/target.md": "# Target\n",
        "docs/file(x).md": "# Escaped\n",
        "openspec/changes/links/design.md": body,
        "openspec/changes/links/peer.md": "# Peer\n",
        "openspec/changes/links/note.txt": "Stable bytes\n",
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode())
    if fault.endswith("kind_unsupported"):
        link = root / "docs/target.md" if fault.startswith("target") else active / "peer.md"
        link.unlink()
        link.symlink_to("file(x).md" if fault.startswith("target") else "../../../docs/target.md")
    head = commit_fixture(root, "declare reference source")
    archived.parent.mkdir(parents=True)
    active.rename(archived)
    if fault == "postimage_target_missing":
        (root / "docs/target.md").unlink()
    if fault == "members_changed":
        (archived / "note.txt").unlink()
    if fault == "content_changed":
        (archived / "note.txt").write_bytes(b"unrelated edit")
    if fault == "missing_cli":
        monkeypatch.setattr(relocation, "openspec_base_command", lambda: None)
        fault = "openspec_official_cli_missing"
    if body == "transport":
        bridge = (
            Mock(side_effect=subprocess.TimeoutExpired(("node",), 60))
            if expected is None
            else Mock(
                return_value=subprocess.CompletedProcess(
                    (), int(expected == 1), json.dumps(expected), ""
                )
            )
        )
        monkeypatch.setattr(relocation, "run_command", bridge)
    if fault:
        with pytest.raises(ValueError, match=fault):
            refresh_archive_projections(root, source_head=head)
        assert (archived / "design.md").read_bytes() == body.encode()
    else:
        for _ in range(2):
            refresh_archive_projections(root, source_head=head)
            assert (archived / "design.md").read_bytes() == (expected or body).encode()
    assert git(root, "rev-parse", "HEAD") == head
