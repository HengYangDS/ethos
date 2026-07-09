from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.shadow.execution as shadow_execution
import ethos.adapters.shadow.identity as shadow_identity
import ethos.adapters.shadow.semantics as shadow_semantics
from tests.unit.product.parity.snapshots import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_shadow_identity_evidence_roots_follow_generic_profile(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ethos").mkdir()
    (repo / ".ethos" / "profile.toml").write_text(
        """schema_version = 1
[roots]
rules = "policy/rules"
claims = "records/claims"
openspec = "planning/specs"
durable_evidence = "records/evidence"
docs = "manuals"
[evidence]
durable_roots = ["audit/evidence"]
generated_roots = ["build/evidence"]
host_local_roots = [".ethos/state"]
""",
        encoding="utf-8",
    )
    for rel in (
        "policy/rules",
        "records/claims",
        "planning/specs",
        "records/evidence",
        "manuals",
        "audit/evidence",
        "build/evidence",
        ".ethos/state",
    ):
        path = repo / rel
        path.mkdir(parents=True)
        (path / "item.txt").write_text(rel, encoding="utf-8")

    paths = {item["path"] for item in shadow_identity.evidence_inputs(repo)}

    assert {
        ".ethos/profile.toml",
        "policy/rules",
        "records/claims",
        "planning/specs",
        "records/evidence",
        "manuals",
        "audit/evidence",
        "build/evidence",
        ".ethos/state",
    } <= paths


def test_shadow_identity_evidence_roots_ignore_invalid_profile(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ethos").mkdir()
    (repo / ".ethos" / "profile.toml").write_text("[", encoding="utf-8")
    (repo / "rules").mkdir()

    paths = {item["path"] for item in shadow_identity.evidence_inputs(repo)}

    assert ".ethos/profile.toml" in paths
    assert "rules" in paths


def test_shadow_identity_changed_paths_handles_rename_and_untracked(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "old.txt").write_text("old", encoding="utf-8")
    subprocess.run(["git", "add", "old.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "add old"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "mv", "old.txt", "new.txt"], cwd=repo, check=True)
    (repo / "untracked.txt").write_text("new", encoding="utf-8")

    paths = shadow_identity.changed_paths(repo)

    assert paths == ["new.txt", "untracked.txt"]


def test_shadow_identity_helpers_fail_closed_for_subprocess_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_error(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        message = "boom"
        raise OSError(message)

    monkeypatch.setattr(shadow_identity.subprocess, "run", raise_error)

    assert shadow_identity.git_head(tmp_path) == ""
    assert shadow_identity.changed_paths(tmp_path) == []


def test_shadow_identity_embedded_labels_fallback_to_backend_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    def fake_backend(target: Path, command: tuple[str, ...]) -> dict[str, object]:
        return {"command": "backend " + " ".join(command)}

    monkeypatch.setattr(shadow_identity, "embedded_backend", fake_backend)

    assert shadow_identity.embedded_command_labels(repo, (("status",),), comparisons=None) == [
        "backend status"
    ]
    assert shadow_identity.embedded_command_labels(
        repo,
        (("status",),),
        comparisons=[{"embedded": {"backend": {}}}],
    ) == ["backend status"]


def test_shadowidentity_evidence_inputs_ignore_special_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    missing = shadow_identity.evidence_input(repo, "missing")
    link = repo / "link"
    link.symlink_to(repo / "missing-target")
    linked = shadow_identity.evidence_input(repo, "link")
    tree = repo / "tree"
    tree.mkdir()
    (tree / "kept.txt").write_text("kept", encoding="utf-8")
    (tree / ".git").mkdir()
    (tree / ".git" / "ignored.txt").write_text("ignored", encoding="utf-8")

    assert missing is None
    assert linked is None
    assert shadow_identity.evidence_input(repo, "tree") == {
        "path": "tree",
        "kind": "directory",
        "sha256": shadow_identity.tree_sha256(tree),
    }


def test_shadow_small_parsers_cover_invalid_shapes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[", encoding="utf-8")

    assert shadow_execution.pyproject_tool(tmp_path) == {}
    assert shadow_execution.parse_json_from_stdout("no json") == {}
    assert shadow_execution.parse_json_from_stdout("[1]") == {}
    assert shadow_execution.parse_json_from_stdout("{bad}") == {}
    assert shadow_semantics.accepted_summary(["ignored", {"kind": ""}, {"kind": "sample"}]) == {
        "total_count": 1,
        "kind_counts": {"sample": 1},
    }
    with pytest.raises(TypeError):
        shadow_semantics._semantic_args(({}, {}, {}, {}))
