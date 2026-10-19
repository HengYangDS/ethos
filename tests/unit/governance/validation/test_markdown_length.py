"""Current Markdown length observes source ownership instead of file suffix alone."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

import ethos.adapters.gates.formatting as source_formatting
import ethos.adapters.gates.tool as quality_tools
import ethos.adapters.repo.content.observation as original_observation
from ethos.adapters.gates.verification import provider_reports
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import GitExecutionError
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.domain.status import audit_for_root
from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.registry import DocumentOrigins
from ethos.repository.registry.docs.registry import retained_document_origins
from ethos.repository.release.resources import canonical_resource
from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_CEILING = load_repository_paradigm().size.markdown_nonblank_lines


@pytest.mark.parametrize(
    ("relative", "state", "count"),
    [
        ("docs/topic.md", "canonical", _CEILING),
        ("docs/topic.md", "canonical", _CEILING + 1),
        ("docs/topic.md", "archived", _CEILING + 1),
        ("README.md", "canonical", _CEILING + 1),
        ("handbook/topic.md", "canonical", _CEILING + 1),
    ],
)
def test_current_markdown_uses_physical_nonblank_limit(
    tmp_path: Path, relative: str, state: str, count: int
) -> None:
    """Blank lines and metadata relabeling cannot evade the portable limit."""
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    base = (
        f"---\nsubject: sample:topic\nrole: reference\nstate: {state}\nrelations: {{}}\n"
        "---\n\n# Topic\n\nPurpose: exercise length.\n"
        if relative.startswith("docs/")
        else "# Topic\n"
    )
    path.write_text(base + "record\n\n" * (count - sum(bool(x.strip()) for x in base.splitlines())))
    git(root, "add", "--", relative)

    report = docs_registry_report(root)

    expected = [] if count == _CEILING else [f"docs_length_exceeded:{relative}:{count}>{_CEILING}"]
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("pass" if count == _CEILING else "block")


def test_release_history_is_not_bounded_by_document_length(tmp_path: Path) -> None:
    """Neither total history nor one release entry is a current document topic."""
    root = init_git_repo(tmp_path / "repo")
    history = "# Changelog\n\n## [Unreleased]\n\n- Pending.\n"
    history += "".join(
        f"\n## [{version}.0.0] - 2026-09-29\n" + "- Change.\n" * 600 for version in range(2, 0, -1)
    )
    assert sum(bool(line.strip()) for line in history.splitlines()) > _CEILING
    (root / "CHANGELOG.md").write_text(history)
    commit_fixture(root, "sectioned release history")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    provider = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]

    assert result.returncode == 0
    assert report["verdict"] == "pass"
    assert provider["required_gaps"] == []


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("CHANGELOG.md", []),
        (
            "handbook/CHANGELOG.md",
            [f"docs_length_exceeded:handbook/CHANGELOG.md:{_CEILING + 1}>{_CEILING}"],
        ),
    ],
)
def test_only_release_owned_changelog_is_exempt_from_document_length(
    tmp_path: Path, relative: str, expected: list[str]
) -> None:
    """A filename elsewhere does not turn authored prose into release history."""
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Changelog\n" + "- Undifferentiated.\n" * _CEILING)
    git(root, "add", "--", relative)

    report = docs_registry_report(root)

    assert report["required_gaps"] == expected


def test_release_history_still_requires_readable_source(tmp_path: Path) -> None:
    """The length exemption does not make an unreadable release carrier healthy."""
    root = init_git_repo(tmp_path / "repo")
    (root / "CHANGELOG.md").write_bytes(b"\xff")
    git(root, "add", "CHANGELOG.md")

    report = docs_registry_report(root)

    assert report["required_gaps"] == ["docs_source_unavailable:CHANGELOG.md"]


def test_official_and_owned_generated_markdown_are_not_authored_docs(tmp_path: Path) -> None:
    """The document limit never mistakes official intent or owned output for prose."""
    root = init_git_repo(tmp_path / "repo")
    declaration = root / ".config/checks/ci-projection/policy.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-ci-template-consistency-v1"\n'
        '[[projection]]\nkind = "copy"\ntemplate = "source.txt"\n'
        'projection = "docs/generated.md"\n'
    )
    (root / "source.txt").write_text("content\n" * (_CEILING + 1))
    for relative in (
        "docs/generated.md",
        "openspec/specs/quality/spec.md",
        "openspec/changes/archive/2026-08-01-old/design.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n" * (_CEILING + 1))
    active = root / "openspec/changes/change/design.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text("# Design\n\nCurrent authored intent.\n")
    git(
        root,
        "add",
        "--",
        ".config/checks/ci-projection/policy.toml",
        "source.txt",
        "docs",
        "openspec",
    )

    report = docs_registry_report(root)

    assert report["verdict"] == "pass", report["required_gaps"]
    selected = quality_tools.prose_report(root)["native"][0]["command"]
    assert "docs/generated.md" not in selected
    assert "openspec/changes/archive/2026-08-01-old/design.md" not in selected
    assert {"openspec/specs/quality/spec.md", "openspec/changes/change/design.md"} <= set(selected)


def test_active_change_artifacts_are_bounded_like_current_markdown(tmp_path: Path) -> None:
    """Only the immutable archive and accepted specifications escape the document limit."""
    root = init_git_repo(tmp_path / "repo")
    active = (
        "openspec/changes/change/design.md",
        "openspec/changes/change/specs/identity/user-auth/spec.md",
        "openspec/changes/change/specs/quality/spec.md",
    )
    exempt = (
        "openspec/specs/quality/spec.md",
        "openspec/changes/archive/2026-08-01-old/design.md",
        "openspec/changes/archive/2026-08-01-old/specs/quality/spec.md",
    )
    for relative in (*active, *exempt):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n" * (_CEILING + 1))
    git(root, "add", "--", "openspec")

    report = docs_registry_report(root)

    assert report["required_gaps"] == [
        f"docs_length_exceeded:{relative}:{_CEILING + 1}>{_CEILING}" for relative in sorted(active)
    ]


@pytest.mark.parametrize("nonblank_lines", [_CEILING, _CEILING + 1])
def test_public_docs_gate_enforces_current_boundary(tmp_path: Path, nonblank_lines: int) -> None:
    """The real prove entrypoint preserves exact acceptance and failed-document observations."""
    root = init_git_repo(tmp_path / "repo")
    (root / "README.md").write_text("# Probe\n" + "record\n" * (nonblank_lines - 1))
    commit_fixture(root, "document boundary")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    checks = report["data"]["checks"]
    provider = json.loads(checks[0]["stdout"])["providers"][0]["report"]
    exceeded = nonblank_lines > _CEILING

    assert (result.returncode != 0) is exceeded
    assert report["verdict"] == ("block" if exceeded else "pass")
    assert report["summary"]["proof_attestation_issued"] is False
    assert provider["required_gaps"] == (
        [f"docs_length_exceeded:README.md:{nonblank_lines}>{_CEILING}"] if exceeded else []
    )


def _retained_original(tmp_path: Path, role: str = "evidence") -> tuple[Path, Path]:
    root = init_git_repo(tmp_path / "repo")
    original = root / "docs/observation.md"
    original.parent.mkdir()
    original.write_text("# Original\n" + "Observed record.\n" * 520)
    revision = commit_fixture(root, "capture original observation")
    base = (
        "---\nsubject: sample:{subject}\nrole: {role}\nstate: canonical\nrelations: {{}}\n"
        "---\n\n# {title}\n\nPurpose: select the current owner.\n"
    )
    (root / "docs/owner.md").write_text(
        base.format(subject="owner", role="reference", title="Owner")
    )
    (root / "docs/README.md").write_text(
        base.format(subject="docs", role="index", title="Docs")
        + "\nStart with [Owner](owner.md).\n"
    )
    metadata = root / "docs/_meta"
    metadata.mkdir()
    (metadata / "README.md").write_text(
        base.format(subject="metadata", role="index", title="Metadata")
        + "\nRead [Taxonomy](taxonomy.toml).\n"
    )
    (metadata / "taxonomy.toml").write_text(
        '[[retained]]\npath = "docs/observation.md"\nsubject = "sample:observation"\n'
        f'role = "{role}"\n'
        f'state = "archived"\norigin = "{revision}:docs/observation.md"\n'
        'relations = { current_owner = "sample:owner" }\n'
        'review_date = "2026-10-15"\n'
        'exit_condition = "Release after the current owner no longer needs this original."\n'
    )
    git(root, "add", "--", "docs")
    return root, original


@pytest.mark.parametrize("role", ["evidence", "history"])
def test_retained_origin_projects_observation_without_rewriting_original(tmp_path, role):
    root, original = _retained_original(tmp_path, role)
    before = original.read_bytes(), original.stat().st_mode
    report = docs_registry_report(root)
    schema = json.loads(
        canonical_resource("system/schemas/kernel/docs-registry.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(report)
    assert report["verdict"] == "pass", report["required_gaps"]
    assert (original.read_bytes(), original.stat().st_mode) == before
    entry = next(x for x in report["registry"] if x["path"] == "docs/observation.md")
    assert (entry["role"], entry["state"]) == (role, "archived")


@pytest.mark.parametrize("change", ["bytes", "mode"])
def test_retained_origin_refuses_changed_native_member(tmp_path, change):
    root, original = _retained_original(tmp_path)
    if change == "bytes":
        original.write_text(original.read_text() + "Changed.\n")
    else:
        original.chmod(0o755)
    before = original.read_bytes(), original.stat().st_mode
    report = docs_registry_report(root)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "docs_metadata_invalid:docs/_meta/taxonomy.toml:retained_origin"
    ]
    assert (original.read_bytes(), original.stat().st_mode) == before


def test_retained_origin_cannot_relabel_current_reference_as_observation(tmp_path):
    root, _ = _retained_original(tmp_path, "reference")
    report = docs_registry_report(root)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["docs_metadata_invalid:docs/_meta/taxonomy.toml:retained"]


@pytest.mark.parametrize("field", ["review_date", "exit_condition"])
def test_retained_origin_requires_a_finite_consumer_contract(tmp_path, field):
    root, _ = _retained_original(tmp_path)
    declaration = root / "docs/_meta/taxonomy.toml"
    declaration.write_text(
        "\n".join(
            line
            for line in declaration.read_text().splitlines()
            if not line.startswith(field + " =")
        )
        + "\n"
    )
    report = docs_registry_report(root)
    assert report["required_gaps"] == ["docs_metadata_invalid:docs/_meta/taxonomy.toml:retained"]


@pytest.mark.parametrize("owner", ["sample:observation", "sample:missing"])
def test_retained_origin_requires_a_live_independent_reader(tmp_path, owner):
    root, original = _retained_original(tmp_path)
    declaration = root / "docs/_meta/taxonomy.toml"
    declaration.write_text(declaration.read_text().replace("sample:owner", owner))
    report = docs_registry_report(root)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "docs_metadata_invalid:docs/observation.md:retained_consumer"
    ]
    assert original.read_text().startswith("# Original")


def test_retained_origin_is_one_native_authored_input_boundary(tmp_path):
    """Prose and the native formatter share one authored set without the original."""
    root, original = _retained_original(tmp_path)
    before = original.read_bytes(), original.stat().st_mode
    git(root, "add", "docs")

    current = quality_tools.prose_report(root)["native"][0]["command"]
    formatted = {item.path for item in source_formatting.prepare_source_format(root)}

    assert "docs/observation.md" not in current
    assert "docs/owner.md" in current
    assert "docs/observation.md" not in formatted
    assert "docs/owner.md" in formatted
    with pytest.raises(ValueError, match=r"source_format_other_owner:docs/observation\.md"):
        source_formatting.prepare_source_format(root, paths=("docs/observation.md",))
    assert (original.read_bytes(), original.stat().st_mode) == before


def test_retained_origin_cannot_be_projected_by_an_unobserved_repository_reader(tmp_path):

    root, original = _retained_original(tmp_path)
    before = original.read_bytes(), original.stat().st_mode

    report = docs_health_report(root)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "docs_metadata_invalid:docs/_meta/taxonomy.toml:retained_origin_unobserved"
    ]
    assert (original.read_bytes(), original.stat().st_mode) == before


def test_document_origins_preserve_an_immutable_snapshot(tmp_path):
    root, _ = _retained_original(tmp_path)
    source = retained_document_origins(root)
    snapshot = DocumentOrigins(source)
    source.clear()

    entry = snapshot.entries["docs/observation.md"]
    assert entry.subject == "sample:observation"
    assert entry.relations == {"current_owner": "sample:owner"}
    with pytest.raises(TypeError):
        snapshot.entries["docs/observation.md"] = entry
    with pytest.raises(ValidationError):
        entry.subject = "sample:replacement"
    with pytest.raises(TypeError):
        entry.relations["current_owner"] = "replacement"


@pytest.mark.parametrize("replacement", ["regular", "symlink", "missing"])
def test_retained_bytes_and_mode_belong_to_one_native_snapshot(tmp_path, monkeypatch, replacement):
    root, original = _retained_original(tmp_path)
    original.chmod(0o755)

    def read(*args, **kwargs):
        content = read_regular_bytes(*args, **kwargs)
        substitute = original.with_suffix(".substitute")
        substitute.write_bytes(content)
        substitute.chmod(0o644)
        original.unlink()
        if replacement == "regular":
            substitute.replace(original)
        elif replacement == "symlink":
            original.symlink_to(substitute)
        return content

    monkeypatch.setattr("ethos.adapters.repo.content.observation.read_regular_bytes", read)

    result = observed_document_origins(root)

    assert result.required_gaps == (
        "docs_metadata_invalid:docs/_meta/taxonomy.toml:retained_origin",
    )


def test_native_retained_observation_reaches_existing_semantic_consumers(tmp_path):

    root, original = _retained_original(tmp_path)
    before = original.read_bytes(), original.stat().st_mode
    origins = observed_document_origins(root)

    report = audit_for_root(root, openspec={"verdict": "pass", "required_gaps": []})
    assert report["docs"]["verdict"] == "pass", report
    assert report["docs"]["required_gaps"] == []
    for consumer in (design_integrity_report, repository_semantic_closure):
        result = consumer(root, retained_origins=origins)
        assert not any("retained_origin" in gap for gap in result["required_gaps"]), result
    reports, verdict, diagnostics = provider_reports(
        "docs-registry",
        (
            "ethos.repository.registry.docs.health:docs_health_report",
            "ethos.repository.policy.schema:schema_validation_report",
        ),
        root,
    )
    assert verdict == "pass", diagnostics
    assert all(entry["report"]["verdict"] == "pass" for entry in reports)
    assert (original.read_bytes(), original.stat().st_mode) == before


def test_authored_selection_does_not_exempt_metadata_state(tmp_path):
    """Only verified originals and exact native carriers leave authored checks."""
    root, _ = _retained_original(tmp_path)
    sources = {
        "docs/closed.md": "---\nsubject: sample:closed\nrole: history\n"
        "state: archived\nrelations: {}\n---\n\n# Closed\n",
        "openspec/changes/archive/2026-10-14-old/design.md": "# Native history\n",
        "openspec/changes/current/tasks.md": "# Native tasks\n",
        "openspec/specs/quality/spec.md": "# Native spec\n",
        "openspec/changes/README.md": "# Entrance\n",
    }
    for relative, text in sources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(root, "add", ".")
    selected = quality_tools.prose_report(root)["native"][0]["command"]
    assert {"docs/closed.md", "openspec/changes/README.md"} <= set(selected)
    assert not {
        "docs/observation.md",
        "openspec/changes/archive/2026-10-14-old/design.md",
    } & set(selected)
    assert {"openspec/changes/current/tasks.md", "openspec/specs/quality/spec.md"} <= set(selected)


def test_retained_original_is_excluded_by_actual_native_quality_consumers(tmp_path):
    """Bad original formatting, spelling and links cannot contaminate current checks."""
    root, original = _retained_original(tmp_path)
    original.write_text(original.read_text() + "\n|teh|[gone](missing.md)|\n")
    revision = commit_fixture(root, "record deliberately unformatted original")
    declaration = root / "docs/_meta/taxonomy.toml"
    declaration.write_text(
        declaration.read_text().replace(
            next(line for line in declaration.read_text().splitlines() if "origin =" in line),
            f'origin = "{revision}:docs/observation.md"',
        )
    )
    commit_fixture(root, "bind current retained observation owner")
    before = original.read_bytes(), original.stat().st_mode
    for consumer in (
        quality_tools.markdown_lint_report,
        quality_tools.prose_report,
        quality_tools.markdown_links_report,
    ):
        report = consumer(root)
        assert report["verdict"] == "pass", report
        selections = [
            json.dumps(item.get("command", item.get("files", []))) for item in report["native"]
        ]
        assert all("docs/observation.md" not in selection for selection in selections), report
    assert (original.read_bytes(), original.stat().st_mode) == before


@pytest.mark.parametrize(
    "consumer",
    [
        quality_tools.markdown_lint_report,
        quality_tools.prose_report,
        quality_tools.markdown_links_report,
        source_formatting.source_format_report,
    ],
)
def test_retained_original_native_git_failure_remains_unknown(tmp_path, monkeypatch, consumer):
    """An unavailable native reader is not a false configuration-invalid result."""
    root, original = _retained_original(tmp_path)
    before = original.read_bytes(), original.stat().st_mode
    failure = GitExecutionError(
        "git_spawn_failed",
        reason="permission_denied",
        command=("git", "cat-file", "--batch"),
        cwd=str(root),
    )

    def refuse(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(original_observation, "read_objects", refuse)
    report = consumer(root)

    assert report["verdict"] == "unknown"
    assert report["state"] == "inventory_unavailable"
    assert report["errors"] == [failure.evidence()]
    assert (original.read_bytes(), original.stat().st_mode) == before


def test_invalid_retained_origin_is_data_at_existing_audit_composition(tmp_path):
    """Native refusal must reach the existing docs result rather than escape as an exception."""
    root, original = _retained_original(tmp_path)
    original.write_text(original.read_text() + "Changed.\n")
    before = original.read_bytes(), original.stat().st_mode
    report = audit_for_root(root, openspec={"verdict": "pass", "required_gaps": []})
    assert report["docs"]["verdict"] == "block"
    assert report["docs"]["required_gaps"] == [
        "docs_metadata_invalid:docs/_meta/taxonomy.toml:retained_origin"
    ]
    assert (original.read_bytes(), original.stat().st_mode) == before


@pytest.mark.parametrize(("role", "state"), [("evidence", "canonical"), ("history", "active")])
def test_retained_observations_preserve_existing_native_state(tmp_path, role, state):
    """Observational originals retain source metadata, not a forced retirement relabel."""
    root, original = _retained_original(tmp_path, role)
    original.write_text(
        f"---\nsubject: sample:observation\nrole: {role}\nstate: {state}\n"
        "relations: {}\n---\n\n" + original.read_text()
    )
    revision = commit_fixture(root, "record original metadata without relabeling")
    declaration = root / "docs/_meta/taxonomy.toml"
    text = declaration.read_text()
    old = next(line for line in text.splitlines() if "origin =" in line)
    declaration.write_text(
        text.replace('state = "archived"', f'state = "{state}"').replace(
            old, f'origin = "{revision}:docs/observation.md"'
        )
    )
    before = original.read_bytes(), original.stat().st_mode
    report = docs_registry_report(root)
    assert report["verdict"] == "pass", report["required_gaps"]
    assert "docs/observation.md" not in quality_tools.prose_report(root)["native"][0]["command"]
    assert (original.read_bytes(), original.stat().st_mode) == before


@pytest.mark.parametrize("current_children", [False, True])
def test_verified_historical_readme_remains_an_observation(tmp_path, current_children):
    """A retained historical README is not current directory navigation by its name."""
    root, original = _retained_original(tmp_path, "history")
    historical = root / "docs/closed/README.md"
    historical.parent.mkdir()
    original.rename(historical)
    revision = commit_fixture(root, "preserve closed historical README")
    declaration = root / "docs/_meta/taxonomy.toml"
    text = declaration.read_text().replace("docs/observation.md", "docs/closed/README.md")
    old = next(line for line in text.splitlines() if "origin =" in line)
    declaration.write_text(text.replace(old, f'origin = "{revision}:docs/closed/README.md"'))
    if current_children:
        for name in ("first", "second"):
            (historical.parent / f"{name}.md").write_text(
                f"---\nsubject: sample:{name}\nrole: reference\nstate: active\n"
                f"relations: {{}}\n---\n\n# {name.title()}\n\n"
                "Purpose: explain the current reference.\n"
            )
    commit_fixture(root, "record current navigation inputs")
    before = historical.read_bytes(), historical.stat().st_mode
    report = docs_registry_report(root)
    expected = ["docs_readme_missing:docs/closed/README.md"] if current_children else []
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("block" if expected else "pass")
    assert "docs/closed/README.md" not in quality_tools.prose_report(root)["native"][0]["command"]
    assert (historical.read_bytes(), historical.stat().st_mode) == before
