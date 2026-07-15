from __future__ import annotations

import ethos.adapters.openspec.lifecycle.scope as openspec_scope
from tests.support.lane_helpers import init_repo


def test_current_archive_scope_is_only_admitted_for_its_reconciliation(
    tmp_path,
) -> None:
    """Archived scopes are current-diff-only and malformed companions fail closed."""
    cases = (
        (
            'schema_version = 1\npaths = ["guidelines.md", "openspec/**"]\n',
            "covered",
            "",
        ),
        (None, "uncovered", "openspec_archive_scope_missing:change"),
        ("paths = [\n", "uncovered", "openspec_archive_scope_invalid:change"),
    )
    for index, (scope_body, state, diagnostic) in enumerate(cases):
        repo = init_repo(tmp_path / str(index))
        profile = repo / ".ethos" / "profile.toml"
        profile.parent.mkdir(exist_ok=True)
        profile.write_text('[openspec]\nmaterial_paths = ["guidelines.md", "openspec/**"]\n')
        archive = repo / "openspec" / "changes" / "archive" / "change"
        archive.mkdir(parents=True)
        if scope_body is not None:
            (archive / "scope.toml").write_text(scope_body)
        metadata = archive / ".openspec.yaml"
        metadata.write_text("schema: spec-driven\ncreated: 2026-07-15\n")
        current = openspec_scope.material_change_scope_report(
            repo,
            changed_paths=("guidelines.md", metadata.relative_to(repo).as_posix()),
            active_change_names=(),
        )
        historical = openspec_scope.material_change_scope_report(
            repo, changed_paths=("guidelines.md",), active_change_names=()
        )
        assert (current["state"], historical["state"]) == (state, "uncovered")
        assert diagnostic in current["advisory_gaps"] or not diagnostic
