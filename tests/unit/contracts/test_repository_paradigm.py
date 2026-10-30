"""Repository paradigm contract loading and declaration boundaries."""

from __future__ import annotations

import tomllib
from importlib import resources

import pytest
from pydantic import ValidationError

from ethos.contracts.paradigm.declaration import RepositoryParadigm
from ethos.contracts.paradigm.declaration import load_repository_paradigm


def _packaged() -> dict[str, object]:
    source = resources.files("ethos.contracts.paradigm").joinpath("paradigm.toml")
    return tomllib.loads(source.read_text(encoding="utf-8"))


def test_packaged_paradigm_names_canonical_carriers() -> None:
    """The packaged contract resolves discovered root names to their canonical carrier."""
    paradigm = load_repository_paradigm()
    assert paradigm.id == "repository-paradigm"
    assert paradigm.canonical_carrier("pytest.ini") == ".config/checks/pytest/pytest.toml"
    assert paradigm.canonical_carrier("mise.toml") == ".config/mise/config.toml"
    assert paradigm.canonical_carrier("unrelated.txt") == ""
    assert paradigm.native_carrier("codespell.toml") == ".config/checks/codespell/codespell.toml"
    assert paradigm.native_carrier("policy.toml") == ""
    owners = paradigm.owner_directories()
    assert owners[".config/checks/gitleaks"] == (
        frozenset({"gitleaks.toml", "gitleaksignore"}),
        False,
    )
    assert owners[".config/checks/vale"][1] is True
    assert ".config/mise" not in owners
    assert {module.id for module in paradigm.module} == {"python", "node", "go"}
    assert paradigm.size.python_effective_lines == 500
    assert paradigm.size.markdown_nonblank_lines == 500
    assert paradigm.size.bound == 1000
    assert paradigm.documents.decision_record_name.startswith("^dr-")
    grammar = paradigm.commit.subject_pattern(("cli",))
    assert grammar.startswith("^(build|chore|ci|docs|feat|fix|perf|refactor|revert|test)")
    assert grammar.endswith(r"(\((cli)\))?!?: .+")
    assert paradigm.openspec.artifact_schema == "spec-driven"
    assert all(paradigm.openspec.rules.model_dump().values())
    retention = paradigm.pipelines.retention
    assert retention.record == ".config/ci/retained-steps.toml"
    assert retention.classes == ("official-installer", "operating-system-glue")
    assert retention.platforms == ("darwin", "linux", "windows")


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown-key",
        "duplicate-root-name",
        "duplicate-module",
        "unadmitted-document",
        "scope",
        "duplicate-table",
        "tool-unknown-key",
        "size-not-positive",
        "openspec-unknown-artifact",
        "openspec-other-schema",
        "openspec-empty-rules",
        "retention-unknown-key",
        "retention-no-classes",
    ],
)
def test_paradigm_declaration_fails_closed(mutation: str) -> None:
    """Unknown keys, ambiguous identities and inconsistent documents never load."""
    payload = _packaged()
    tools = payload["tool"]
    modules = payload["module"]
    root = payload["root"]
    assert isinstance(tools, list)
    assert isinstance(modules, list)
    assert isinstance(root, dict)
    if mutation == "unknown-key":
        payload["exceptions"] = ["pytest.ini"]
    elif mutation == "duplicate-root-name":
        tools.append({"id": "copy", "carrier": ".config/copy", "root_names": ["pytest.ini"]})
    elif mutation == "duplicate-module":
        modules.append(dict(modules[0]))
    elif mutation == "unadmitted-document":
        root["required_documents"] = ["CLAUDE.md"]
    elif mutation == "scope":
        modules[0] = {**modules[0], "lock_scope": "optional"}
    elif mutation == "duplicate-table":
        tools.append(
            {
                "id": "copy",
                "carrier": ".config/checks/copy/copy.toml",
                "manifest_tables": ["ruff"],
            }
        )
    elif mutation == "size-not-positive":
        payload["size"] = {**payload["size"], "python_effective_lines": 0}
    elif mutation.startswith("retention-"):
        pipelines = payload["pipelines"]
        assert isinstance(pipelines, dict)
        retention = pipelines["retention"]
        assert isinstance(retention, dict)
        pipelines["retention"] = (
            {**retention, "waiver": "always"}
            if mutation == "retention-unknown-key"
            else {**retention, "classes": []}
        )
    elif mutation.startswith("openspec-"):
        openspec = payload["openspec"]
        assert isinstance(openspec, dict)
        payload["openspec"] = {
            "openspec-unknown-artifact": {
                **openspec,
                "rules": {**openspec["rules"], "review": ["Review it."]},
            },
            "openspec-other-schema": {**openspec, "artifact_schema": "custom"},
            "openspec-empty-rules": {
                **openspec,
                "rules": {**openspec["rules"], "tasks": []},
            },
        }[mutation]
    else:
        tools[0] = {**tools[0], "exceptions": ["mise.toml"]}
    with pytest.raises(ValidationError):
        RepositoryParadigm.model_validate(payload)


@pytest.mark.parametrize(
    "commit",
    [
        {"types": ["fix", "fix"]},
        {"types": []},
        {"scope": "[a-z"},
        {"breaking_marker": "!!"},
    ],
    ids=["duplicate-type", "no-types", "uncompilable-scope", "marker-length"],
)
def test_commit_grammar_fails_closed(commit: dict[str, object]) -> None:
    """Duplicate or missing types, an uncompilable scope or a long marker never load."""
    payload = _packaged()
    payload["commit"] = {**payload["commit"], **commit}
    with pytest.raises(ValidationError):
        RepositoryParadigm.model_validate(payload)
