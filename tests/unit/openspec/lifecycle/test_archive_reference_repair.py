"""Keep authored Markdown consumers repairable after official archive."""

from __future__ import annotations

from io import StringIO

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.scope import official_validation_repair_scope_report
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.proof import seed_executed_proof


def test_archived_change_admits_only_stale_markdown_link_consumers(tmp_path, monkeypatch):
    """An exact archived transition owns its still-broken authored consumers."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    root = lifecycle.worktree
    guide = root / "docs/guide.md"
    guide.parent.mkdir()
    guide.write_text(
        "# Guide\n\nThe active [design](../openspec/changes/fixture-change/design.md) "
        "explains this decision.\n",
        encoding="utf-8",
    )
    decoy = root / "docs/decoy.md"
    decoy.write_text(
        "# Decoy\n\n```md\n[design](../openspec/changes/fixture-change/design.md)\n```\n",
        encoding="utf-8",
    )
    missing = root / "docs/missing.md"
    missing.write_text(
        "# Missing\n\n[absent](../openspec/changes/fixture-change/absent.md)\n",
        encoding="utf-8",
    )
    commit_fixture(root, "link active Change from authored docs")
    seed_executed_proof(root, lifecycle.head)
    monkeypatch.setattr(archive, "proof_gaps", proof_gaps)
    archived = lifecycle.archive()
    assert archived["verdict"] == "pass"
    assert not lifecycle.active.exists()
    assert "The active" in guide.read_text(encoding="utf-8")

    official = openspec_governance_report(root, change="fixture-change", lifecycle=True)
    assert not official_validation_repair_scope_report(
        root=root,
        head=lifecycle.head,
        official=official,
        official_artifact_paths=(),
        requested_paths=("docs/guide.md",),
        archived=None,
    )

    options = ("--editor-root", str(root), "--require-editor-root", "--json")
    repair = run_ethos("lane", "prewrite", "docs/guide.md", *options, cwd=root)
    assert repair["verdict"] == "pass", repair
    assert repair["data"]["material_scope"]["state"] == "archive_reference_repair"
    assert repair["data"]["material_scope"]["authorized_paths"] == ["docs/guide.md"]

    for path in ("docs/decoy.md", "README.md"):
        blocked = run_ethos_blocked("lane", "prewrite", path, *options, cwd=root)
        assert f"openspec_material_path_uncovered:{path}" in blocked["required_gaps"]
    absent = run_ethos_blocked("lane", "prewrite", "docs/missing.md", *options, cwd=root)
    assert any("archive_reference_target_missing" in gap for gap in absent["required_gaps"])

    archive_dir = next((root / "openspec/changes/archive").glob("*-fixture-change"))
    original = guide.read_text(encoding="utf-8")
    guide.write_text(
        original.replace("The active", "The archived").replace(
            "../openspec/changes/fixture-change/design.md",
            f"../{archive_dir.relative_to(root).as_posix()}/design.md",
        ),
        encoding="utf-8",
    )
    updated = guide.read_text(encoding="utf-8")
    patch = tmp_path / "authored-repair.patch"
    patch.write_text(git(root, "diff", "--", "docs/guide.md") + "\n", encoding="utf-8")
    guide.write_text(original, encoding="utf-8")
    admitted = run_ethos(
        "lane", "prewrite", "docs/guide.md", "--patch", str(patch), *options, cwd=root
    )
    assert admitted["verdict"] == "pass", admitted
    assert admitted["data"]["patch_admission"]["verdict"] == "pass"

    guide.write_text(updated, encoding="utf-8")
    git(root, "add", "docs/guide.md")
    assert execute_hook(root, "pre-commit", (), stdin=StringIO()) == 0
