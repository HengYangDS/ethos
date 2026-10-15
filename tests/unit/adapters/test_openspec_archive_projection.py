"""Exercise archive projection closure without turning derived bytes into authority."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.openspec.archive_projection as projection
import ethos.adapters.openspec.relocation as relocation
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.archive_projection import refresh_archive_projections
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_normalize_projected_specs_formats_only_canonical_markdown(tmp_path: Path) -> None:
    original = b"## Purpose\nKeep the authored purpose.\n\n## Requirements\n\nBody.\n\n\n"
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
    contents["openspec/specs/contracts/spec.md"] = (
        b"## Purpose\n\nKeep the authored purpose.\n\n## Requirements\n\nBody.\n"
    )
    assert {path: (tmp_path / path).read_bytes() for path in contents} == contents
    assert normalize_projected_specs(tmp_path, paths=tuple(contents)) == ()


def test_absent_archive_is_a_noop_but_unobservable_postimage_is_not(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    head = git(root, "rev-parse", "HEAD")
    refresh_archive_projections(root, source_head=head)
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
    with (root / ".gitattributes").open("a", encoding="utf-8") as attributes:
        attributes.write("openspec/** -text\n")
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
    resolver = Mock(wraps=relocation.openspec_base_command)
    monkeypatch.setattr(relocation, "openspec_base_command", resolver)
    if fault == "missing_cli":
        monkeypatch.setattr(relocation, "openspec_base_command", lambda **_kwargs: None)
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
        with observe_worktree_postimage(root, previous=head) as observed:
            arguments = {
                "source_head": head,
                "tree": observed.tree,
                "changed_paths": observed.changed_paths,
                "environment": observed.environment,
            }
            updates = projection.archive_projection_updates(root, **arguments)
            assert projection.archive_projection_scope(root, **arguments, allow_pending=True) == (
                tuple(updates),
                tuple(updates),
            )
            assert projection.archive_projection_scope(root, **arguments, allow_pending=False) == (
                None if updates else ((), ())
            )
        for _ in range(2):
            refresh_archive_projections(root, source_head=head)
            assert (archived / "design.md").read_bytes() == (expected or body).encode()
        with observe_worktree_postimage(root, previous=head) as observed:
            assert projection.archive_projection_scope(
                root,
                source_head=head,
                tree=observed.tree,
                changed_paths=observed.changed_paths,
                environment=observed.environment,
                allow_pending=False,
            ) == (tuple(updates), ())
    assert all(
        not observed.args and observed.kwargs == {"execution_probe": False}
        for observed in resolver.call_args_list
    )
    assert git(root, "rev-parse", "HEAD") == head


def test_normalization_preserves_canonical_unavailable_and_nonlocal_carriers(
    tmp_path: Path,
) -> None:
    """Canonical bytes are stable; unavailable or nonlocal paths are not written."""
    relative = "openspec/specs/contracts/spec.md"
    canonical = tmp_path / relative
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"# Contract\n")
    assert (
        normalize_projected_specs(
            tmp_path,
            paths=(
                relative,
                relative,
                "openspec/specs/missing/spec.md",
                "/outside/spec.md",
                "../spec.md",
            ),
        )
        == ()
    )
    assert canonical.read_bytes() == b"# Contract\n"


def test_archive_refresh_rechecks_preimage_before_writing(tmp_path: Path, monkeypatch) -> None:
    """A concurrent edit survives instead of being overwritten by stale relocation."""
    root = init_git_repo(tmp_path / "repo")
    relative = "openspec/changes/archive/2026-10-14-links/design.md"
    target = root / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"original\n")
    head = commit_fixture(root, "declare exact preimage")
    newer = b"concurrent owner edit\n"

    def mutate_after_observation(*_args, **_kwargs):
        target.write_bytes(newer)
        return {relative: b"relocated\n"}, {relative: b"original\n"}

    monkeypatch.setattr(projection, "archive_relocation", mutate_after_observation)
    with pytest.raises(ValueError, match="archive_projection_preimage_changed"):
        refresh_archive_projections(root, source_head=head)
    assert target.read_bytes() == newer
    assert git(root, "rev-parse", "HEAD") == head


def test_archive_scope_requires_an_observable_declared_output(tmp_path: Path, monkeypatch) -> None:
    """Unavailable output cannot acquire archive scope from an asserted identity."""
    root = init_git_repo(tmp_path / "repo")
    relative = "openspec/changes/archive/2026-10-14-links/design.md"
    monkeypatch.setattr(
        projection,
        "archive_relocation",
        lambda *_args, **_kwargs: ({relative: b"relocated\n"}, {relative: b"original\n"}),
    )
    with pytest.raises(ValueError, match="archive_projection_input_unavailable"):
        projection.archive_projection_scope(
            root,
            source_head=git(root, "rev-parse", "HEAD"),
            tree="unavailable",
            changed_paths=(relative,),
            environment=None,
            allow_pending=True,
        )


@pytest.mark.parametrize(
    ("members", "reason"),
    [
        (("ghost",), ""),
        (("left", "right"), "archive_reference_change_ambiguous"),
        (("binary",), ""),
    ],
)
def test_archive_selection_requires_one_original_document_owner(tmp_path: Path, members, reason):
    """Absent and non-document moves are inert; competing Changes cannot share a relocation."""
    root = init_git_repo(tmp_path / "repo")
    (root / "README.md").write_bytes(b"# Independent product\n")
    for name in set(members) - {"ghost"}:
        file = root / "openspec/changes" / name / "note.txt"
        file.parent.mkdir(parents=True)
        file.write_bytes(b"original\n")
    head = commit_fixture(root, "declare original archive owners")
    for name in members:
        source = root / "openspec/changes" / name
        target = root / "openspec/changes/archive" / f"2026-10-14-{name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "ghost":
            target.mkdir()
            (target / "note.txt").write_bytes(b"unbound\n")
        else:
            source.rename(target)
    with observe_worktree_postimage(root, previous=head) as observed:
        arguments = {
            "source_head": head,
            "tree": observed.tree,
            "changed_paths": observed.changed_paths,
            "environment": observed.environment,
        }
        if reason:
            with pytest.raises(ValueError, match=reason):
                projection.archive_projection_updates(root, **arguments)
        else:
            assert projection.archive_projection_updates(root, **arguments) == {}
    assert git(root, "rev-parse", "HEAD") == head
