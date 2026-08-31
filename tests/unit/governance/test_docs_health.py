"""Regression coverage for documentation command validation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import pytest

from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.health import ethos_command_tokens
from ethos.repository.registry.docs.health import shell_commands
from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


def write_active_doc(root: Path, command: str) -> None:
    """Write one minimal canonical document containing a shell command example."""
    path = root / "docs" / "reference" / "example.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""\
---
subject: ethos:example
role: reference
state: canonical
relations: none
---

# Example

Status: canonical.

Purpose: exercise the command validator.

See also: none.

```bash
{command}
```
""",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("command", "invalid"),
    literal_case(
        "governance.test_docs_health:parametrize:test_docs_health_resolves_commands_through_the_live_command_tree:0"
    ),
)
def test_docs_health_resolves_commands_through_the_live_command_tree(
    tmp_path: Path, command: str, invalid: str | None
) -> None:
    write_active_doc(tmp_path, command)

    report = docs_registry_report(tmp_path)

    assert report["invalid_command_examples"] == (
        []
        if invalid is None
        else [f"unknown_ethos_command_example:docs/reference/example.md:17:{invalid}"]
    )


def test_docs_health_rejects_unindexed_plan(tmp_path: Path) -> None:
    """Every active or planned plan must be reachable from the plan index."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "README.md").write_text(
        _document("docs:plans", "index", "planned", "Plans"), encoding="utf-8"
    )
    (plans / "orphan.md").write_text(
        _document("ethos:orphan-plan", "plan", "active", "Orphan Plan"), encoding="utf-8"
    )

    report = docs_registry_report(tmp_path)

    assert report["unindexed_plans"] == ["unindexed_plan:docs/plans/orphan.md"]


def test_docs_health_rejects_marker_only_readme(tmp_path: Path) -> None:
    """A README must explain or navigate its directory, not mark its existence."""
    readme = tmp_path / "docs" / "guides" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(_document("docs:guides", "index", "canonical", "Guides"), encoding="utf-8")
    report = docs_registry_report(tmp_path)

    assert report["readme_disposition"] == ["docs_readme_without_children:docs/guides/README.md"]


def test_docs_health_retains_a_boundary_readme_without_sibling_documents(tmp_path: Path) -> None:
    """A README may be the sole document when it declares a real boundary."""
    readme = tmp_path / "docs" / "evidence" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(
        _document("docs:evidence", "index", "canonical", "Evidence").replace(
            "relations: none", "relations:\n  canonical_for: evidence documentation"
        ),
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["readme_disposition"] == []


def test_docs_health_reports_missing_invalid_and_duplicate_metadata(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "reference"
    docs.mkdir(parents=True)
    (docs / "first.md").write_text(
        _document("ethos:duplicate", "unknown", "unexpected", "First"),
        encoding="utf-8",
    )
    (docs / "second.md").write_text(
        _document("ethos:duplicate", "reference", "canonical", "Second"),
        encoding="utf-8",
    )
    (docs / "missing.md").write_text("# Missing metadata\n", encoding="utf-8")

    report = docs_health_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["missing_metadata"] == ["docs/reference/missing.md"]
    assert report["invalid_state"] == ["invalid_state:docs/reference/first.md:unexpected"]
    assert report["invalid_role"] == ["invalid_role:docs/reference/first.md:unknown"]
    assert report["duplicate_subjects"] == [
        "duplicate_subject:ethos:duplicate:docs/reference/first.md,docs/reference/second.md"
    ]


def test_docs_health_ignores_missing_visible_document_after_registry_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = {
        "path": "docs/reference/removed.md",
        "subject": "ethos:removed",
        "role": "reference",
        "state": "canonical",
        "relations": "none",
    }
    monkeypatch.setattr(
        "ethos.repository.registry.docs.health.build_docs_registry", lambda _root: [entry]
    )

    report = docs_health_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["missing_visible_sections"] == []


def test_shell_command_reports_native_invocation_forms_and_malformed_quotes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "commands.md"
    path.write_text(
        """```bash
# ignored
env ETHOS_ACTOR=agent:test ethos status \\
  --json
uv run --package ethos ethos plan --changed --json
python -m ethos.cli prove --json
printf 'not ethos'
ethos "unterminated
```
""",
        encoding="utf-8",
    )

    commands = shell_commands(path)

    assert commands == [
        (3, "env ETHOS_ACTOR=agent:test ethos status --json"),
        (5, "uv run --package ethos ethos plan --changed --json"),
        (6, "python -m ethos.cli prove --json"),
        (7, "printf 'not ethos'"),
        (8, 'ethos "unterminated'),
    ]
    assert [ethos_command_tokens(command) for _, command in commands] == [
        ["status", "--json"],
        ["plan", "--changed", "--json"],
        ["prove", "--json"],
        [],
        ['"unterminated'],
    ]


def test_shell_commands_flushes_unclosed_fence_and_ignores_uv_without_ethos(tmp_path: Path) -> None:
    path = tmp_path / "commands.md"
    path.write_text("```sh\nuv run python -V " + "\\\n  --verbose", encoding="utf-8")

    assert shell_commands(path) == [(2, "uv run python -V --verbose")]
    assert ethos_command_tokens("uv run python -V") == []


def _write_guide(root: Path, relative: str = "docs/native/guide.md") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_text(_document("adopter:guide", "how-to", "active", "Guide"), encoding="utf-8")
    return path


def _document(subject: str, role: str, state: str, title: str) -> str:
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: {state}\nrelations: none\n---\n\n"
        f"# {title}\n\nStatus: {state}.\n\nPurpose: exercise docs health.\n\nSee also: none.\n"
    )


def test_docs_health_is_portable_without_ethos_physical_layout(tmp_path: Path) -> None:
    """Adopter docs health validates semantics without imposing ETHOS paths."""
    _write_guide(tmp_path)

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_docs_health_uses_the_profile_declared_docs_root(tmp_path: Path) -> None:
    """One profile-relative root drives every portable docs check."""
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        "profile_id = 'sample'\n"
        "[roots]\n"
        "docs = 'handbook'\n"
        "[openspec]\n"
        "material_paths = ['openspec/**']\n",
        encoding="utf-8",
    )
    _write_guide(tmp_path, "handbook/guide.md")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    registry = cast("list[dict[str, str]]", report["registry"])
    assert [entry["path"] for entry in registry] == ["handbook/guide.md"]


def test_docs_health_fails_closed_for_an_invalid_profile(tmp_path: Path) -> None:
    """An invalid declaration never falls back to the default docs root."""
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n[roots]\ndocs = '../outside'\n", encoding="utf-8")
    write_active_doc(tmp_path, "ethos status --json")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["document_count"] == 0
    assert report["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]


def test_docs_health_fails_closed_for_invalid_taxonomy(tmp_path: Path) -> None:
    """A present but malformed taxonomy cannot silently select defaults."""
    write_active_doc(tmp_path, "ethos status --json")
    taxonomy = tmp_path / "docs" / "_meta" / "taxonomy.toml"
    taxonomy.parent.mkdir()
    taxonomy.write_text("[states\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["docs_taxonomy_invalid:docs/_meta/taxonomy.toml"]


def test_docs_health_does_not_reclassify_unrelated_registry_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = "unrelated native read failure"

    def fail(_root: Path) -> list[dict[str, str]]:
        raise ValueError(message)

    monkeypatch.setattr("ethos.repository.registry.docs.health.build_docs_registry", fail)

    with pytest.raises(ValueError, match=message):
        docs_health_report(tmp_path)


def test_shell_commands_flushes_buffer_at_closing_fence(tmp_path: Path) -> None:
    path = tmp_path / "commands.md"
    path.write_text("```bash\nethos status " + "\\\n```\n", encoding="utf-8")

    assert shell_commands(path) == [(2, "ethos status")]


def test_docs_health_does_not_scan_product_distribution_layout(tmp_path: Path) -> None:
    """Portable docs semantics do not absorb ETHOS product carriers."""
    write_active_doc(tmp_path, "ethos status --json")
    distribution = tmp_path / "distributions" / "python" / "README.md"
    distribution.parent.mkdir(parents=True)
    distribution.write_text("# Product-only carrier\n", encoding="utf-8")

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    registry = cast("list[dict[str, str]]", report["registry"])
    assert [entry["path"] for entry in registry] == ["docs/reference/example.md"]


def test_observational_roles_do_not_require_reader_sections(tmp_path: Path) -> None:
    """Evidence and history are classified by role, not by hard-coded paths."""
    path = tmp_path / "docs" / "native" / "observation.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        _document("adopter:observation", "evidence", "active", "Observation"), encoding="utf-8"
    )

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["missing_visible_sections"] == []


def test_docs_health_has_no_decision_record_specific_grammar(tmp_path: Path) -> None:
    """Docs health validates portable metadata, not a parallel decision authority."""
    path = tmp_path / "docs" / "reference" / "decision-shaped-note.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
subject: example:decision-shaped-note
role: reference
state: canonical
relations: none
---

# Decision-shaped note

Status: canonical.

Purpose: prove the registry has no Decision Record grammar or index authority.

See also: none.

## Record

| Field | Value |
| --- | --- |
| Decision ID | deliberately malformed |
""",
        encoding="utf-8",
    )

    report = docs_registry_report(tmp_path)

    assert report["verdict"] == "pass"
    assert "decision_record_gaps" not in report
