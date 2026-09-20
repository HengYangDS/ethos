"""Regression coverage for documentation command validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.design.integrity import front_matter_ok
from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.health import ethos_command_tokens
from ethos.repository.registry.docs.health import shell_commands
from ethos.repository.registry.docs.registry import front_matter
from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


def write_active_doc(root: Path, command: str) -> None:
    """Write a canonical document and a command under the same metadata fixture."""
    path = root / "docs/reference/example.md"
    path.parent.mkdir(parents=True)
    fence = chr(96) * 3
    path.write_text(
        _document("ethos:example", "reference", "canonical", "Example")
        + f"\n{fence}bash\n{command}\n{fence}\n"
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


@pytest.mark.parametrize("boundary", [False, True])
def test_docs_health_retains_only_meaningful_readme_boundaries(tmp_path, boundary) -> None:
    """A real boundary needs no child page; an empty directory marker is rejected."""
    path = tmp_path / "docs/native/README.md"
    path.parent.mkdir(parents=True)
    text = _document("docs:native", "index", "canonical", "Native")
    if boundary:
        text = text.replace("relations: {}", "relations:\n  canonical_for: native documentation")
    path.write_text(text)
    report = docs_registry_report(tmp_path)
    assert report["readme_disposition"] == (
        [] if boundary else ["docs_readme_without_children:docs/native/README.md"]
    )


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
        "relations": {},
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


def _document(subject: str, role: str, state: str, title: str) -> str:
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: {state}\nrelations: {{}}\n---\n\n"
        f"# {title}\n\nStatus: {state}.\n\nPurpose: exercise docs health.\n\nSee also: none.\n"
    )


@pytest.mark.parametrize("docs", ["docs/native", "handbook"])
def test_docs_health_uses_only_the_declared_portable_documentation_root(tmp_path, docs) -> None:
    """Native layout is retained; unrelated product carriers are never absorbed."""
    if docs == "handbook":
        profile = tmp_path / ".ethos/profile.toml"
        profile.parent.mkdir()
        profile.write_text("profile_id = 'sample'\n[roots]\ndocs = 'handbook'\n")
    guide = tmp_path / docs / "guide.md"
    guide.parent.mkdir(parents=True)
    guide.write_text(_document("adopter:guide", "how-to", "active", "Guide"))
    distribution = tmp_path / "distributions/python/README.md"
    distribution.parent.mkdir(parents=True)
    distribution.write_text("# Product-only carrier\n")
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert [entry["path"] for entry in report["registry"]] == [f"{docs}/guide.md"]


@pytest.mark.parametrize(
    ("path", "content", "gap"),
    [
        (
            ".ethos/profile.toml",
            "profile_id='sample'\n[roots]\ndocs='../outside'\n",
            "repository_profile_invalid:.ethos/profile.toml",
        ),
        ("docs/_meta/taxonomy.toml", "[states\n", "docs_taxonomy_invalid:docs/_meta/taxonomy.toml"),
    ],
)
def test_docs_health_fails_closed_for_invalid_native_configuration(tmp_path, path, content, gap):
    """Malformed native inputs never silently select default roots or taxonomy."""
    write_active_doc(tmp_path, "ethos status --json")
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["document_count"] == 0
    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("module", "consumer"),
    [
        ("ethos.repository.registry.docs.health", docs_health_report),
        ("ethos.repository.design.integrity", design_integrity_report),
        ("ethos.repository.policy.references.closure", repository_semantic_closure),
    ],
)
def test_docs_health_does_not_reclassify_unrelated_registry_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module, consumer
) -> None:
    message = "unrelated native read failure"

    def fail(_root: Path) -> list[dict[str, str]]:
        raise ValueError(message)

    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(f"{module}.build_docs_registry", fail)
    with pytest.raises(ValueError, match=message):
        consumer(tmp_path)


@pytest.mark.parametrize(
    ("before", "after", "verdict"),
    [
        ("role: reference", 'role: "reference"', "pass"),
        ("state: canonical", "state: 'canonical'", "pass"),
        ("state: canonical", "state: archived\\nstate: canonical", "block"),
        ("relations: {}\\n---", "relations: {}", "block"),
        ("relations: {}", "relations: [broken", "block"),
        ("subject: ethos:example", "subject: [ethos:example]", "block"),
        ("relations: {}", "relations: not-a-mapping", "block"),
        (
            "subject: ethos:example\\nrole: reference\\nstate: canonical\\nrelations: {}",
            "[invalid]",
            "block",
        ),
        ("relations: {}", "relations:\\n  current_owner: missing.md", "block"),
        ("relations: {}", "relations:\\n  canonical_for: a descriptive scope", "pass"),
        ("Status: canonical.", "Status: superseded.", "block"),
        ("Status: canonical.", "Status: see front matter.", "pass"),
        ("Status: canonical.", "Status:", "block"),
        ("relations: {}", "relations:\\n  current_owner: a\\n  current_owner: b", "block"),
        (
            "relations: {}",
            "default: &default {canonical_for: scope}\\nrelations:\\n  <<: *default",
            "pass",
        ),
        ("relations: {}", "relations: {}\\nextra: !!python/object:builtins.object {}", "block"),
    ],
)
def test_metadata_public_report_preserves_validity_and_rejects_ambiguity(
    tmp_path: Path, before: str, after: str, verdict: str
) -> None:
    """Syntax, identity, relation resolution and visible state share one report."""
    write_active_doc(tmp_path, "ethos status --json")
    path = tmp_path / "docs/reference/example.md"
    before, after = before.replace("\\n", "\n"), after.replace("\\n", "\n")
    path.write_text(path.read_text().replace(before, after))
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == verdict
    assert bool(report["required_gaps"]) == (verdict == "block")
    if any(gap.startswith("docs_metadata_invalid:") for gap in report["required_gaps"]):
        for consumer in (design_integrity_report, repository_semantic_closure):
            assert any(
                "docs_metadata_invalid:" in gap for gap in consumer(tmp_path)["required_gaps"]
            )
        if report["required_gaps"][0].endswith(":syntax"):
            assert not front_matter_ok(path)


def test_metadata_retains_structures_and_excludes_literal_guidance(tmp_path: Path) -> None:
    """Unknown input fields remain data; fenced labels do not guide a reader."""
    path = tmp_path / "docs/reference/example.md"
    write_active_doc(tmp_path, "ethos status --json")
    text = path.read_text().replace(
        "relations: {}", "relations:\n  current_owner: owner.md\nextra:\n  nested: [retained]"
    )
    (path.parent / "owner.md").write_text(
        _document("ethos:owner", "reference", "canonical", "Owner")
    )
    path.write_text(text)
    metadata = front_matter(path)
    assert metadata["relations"] == {"current_owner": "owner.md"}
    assert metadata["extra"] == {"nested": ["retained"]}
    assert docs_registry_report(tmp_path)["verdict"] == "pass"
    start, body = text.split("# Example", 1)
    fence = chr(96) * 4
    path.write_text(start + "# Example\n\n" + fence + "\n" + body + "\n" + fence + "\n")
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["missing_visible_sections"] == [
        "missing_visible_section:docs/reference/example.md:status",
        "missing_visible_section:docs/reference/example.md:purpose",
        "missing_visible_section:docs/reference/example.md:see also",
    ]


@pytest.mark.parametrize("role", ["reference", "evidence", "history", "ledger"])
def test_native_document_roles_keep_observations_and_rationale_non_authorizing(tmp_path, role):
    """Reader roles do not invent another decision grammar or progress ledger."""
    path = tmp_path / "docs/native/topic.md"
    path.parent.mkdir(parents=True)
    text = _document("example:topic", role, "active", "Topic")
    if role in {"evidence", "history"}:
        text = text.split("# Topic", 1)[0] + "# Topic\n"
    path.write_text(
        text + "\n## Record\n\n| Field | Value |\n| --- | --- |\n"
        "| Decision ID | deliberately malformed |\n"
    )
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == ("block" if role == "ledger" else "pass")
    assert report["invalid_role"] == (
        ["invalid_role:docs/native/topic.md:ledger"] if role == "ledger" else []
    )
    assert report["missing_visible_sections"] == []
    assert "decision_record_gaps" not in report


@pytest.mark.parametrize("closed", [False, True])
def test_native_shell_fences_flush_continuations_and_ignore_unrelated_commands(tmp_path, closed):
    """Closing and end-of-file boundaries preserve the same logical command."""
    fence = chr(96) * 3
    path = tmp_path / "commands.md"
    command = "ethos status" if closed else "uv run python -V"
    path.write_text(f"{fence}sh\n{command} " + "\\" + "\n" + (fence if closed else "  --verbose"))
    assert shell_commands(path) == [(2, command if closed else command + " --verbose")]
    assert ethos_command_tokens("uv run python -V") == []
