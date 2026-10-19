"""Proof requires the selected Change to archive into strictly valid specifications."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.archive_readiness import archive_readiness_gaps
from ethos.adapters.openspec.projection import openspec_tree_projection
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import official_validation_payload
from tests.support.proof import declare_native_proof_checks
from tests.support.proof import proof_repository

if TYPE_CHECKING:
    from pathlib import Path

_MARKER = (
    "from pathlib import Path\n"
    "Path('build').mkdir(exist_ok=True)\n"
    "Path('build/ran').write_text('executed')\n"
)
_REQUIREMENT = "The governed fixture SHALL remain valid throughout its lifecycle."


def _modify_fixture_requirement(repo: Path, length: int) -> str:
    text = f"{_REQUIREMENT} {'x' * (length - len(_REQUIREMENT) - 1)}"
    assert len(text) == length
    delta = repo / "openspec/changes/proof-binding/specs/contracts/spec.md"
    delta.write_text(
        "## MODIFIED Requirements\n\n### Requirement: Governed fixture\n\n"
        f"{text}\n\n#### Scenario: Fixture is exercised\n\n"
        "- **WHEN** the test lifecycle runs\n"
        "- **THEN** the governed fixture remains valid\n",
        encoding="utf-8",
    )
    return commit_fixture(repo, "docs(openspec): modify the fixture requirement")


@pytest.mark.parametrize("length", [500, 501])
def test_proof_gates_run_only_after_the_selected_change_archives_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, length: int
) -> None:
    repo, _head = proof_repository(tmp_path / "repo")
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    declare_native_proof_checks(repo, test=_MARKER, typecheck="print('static green')")
    commit_fixture(repo, "ci: declare real proof gates")
    head = _modify_fixture_requirement(repo, length)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", scratch.as_posix())

    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=repo
    )
    report = json.loads(completed.stdout)

    archivable = length == 500
    assert (completed.returncode == 0, report["verdict"]) == (
        (True, "pass") if archivable else (False, "block")
    )
    assert report["required_gaps"] == (
        []
        if archivable
        else ["openspec_archived_requirement_invalid:proof-binding:contracts:Governed fixture"]
    )
    assert (repo / "build/ran").exists() is archivable
    assert list(scratch.iterdir()) == []
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain=v1") == ""


def _committed_change(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo, change_id="change")
    return repo, git(repo, "rev-parse", "HEAD^{tree}")


@pytest.mark.parametrize("failure", ["cli", "archive"])
def test_a_missing_official_cli_or_a_failed_archive_is_not_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repo, tree = _committed_change(tmp_path)
    if failure == "cli":
        monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda **_kwargs: None)
    else:
        failed = {"exit_code": 1, "json": {}, "parse_error": ""}
        monkeypatch.setattr(openspec_cli, "run_json", lambda *_args, **_kwargs: failed)

    assert archive_readiness_gaps(repo, change="change", tree=tree) == (
        "openspec_official_cli_missing"
        if failure == "cli"
        else "openspec_archive_simulation_failed:change",
    )


def test_an_issue_without_a_resolvable_requirement_names_its_specification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, tree = _committed_change(tmp_path)
    issue = {"level": "ERROR", "message": "invalid"}
    validation = official_validation_payload(
        repo,
        [
            {"type": "change", "id": "change", "valid": True, "issues": []},
            {"type": "spec", "id": "alpha", "valid": False, "issues": []},
            {
                "type": "spec",
                "id": "beta",
                "valid": False,
                "issues": [
                    {**issue, "path": "purpose"},
                    {**issue, "path": "requirements[0].text"},
                    {**issue, "path": "requirements[1]"},
                ],
            },
        ],
    )
    official = openspec_cli.run_json

    def run_json(
        root: Path, command: tuple[str, ...], args: tuple[str, ...], **kwargs: float
    ) -> dict[str, object]:
        if args[0] == "validate":
            return {"exit_code": 1, "json": validation, "parse_error": ""}
        if args[0] == "show":
            return {"exit_code": 0, "json": {"requirements": None}, "parse_error": ""}
        return official(root, command, args, **kwargs)

    monkeypatch.setattr(openspec_cli, "run_json", run_json)

    assert archive_readiness_gaps(repo, change="change", tree=tree) == (
        "openspec_archived_spec_invalid:change:alpha",
        "openspec_archived_spec_invalid:change:beta",
    )


def test_a_tree_without_openspec_artifacts_has_no_projection(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    with (
        pytest.raises(ValueError, match="openspec_tree_projection_missing"),
        openspec_tree_projection(repo, git(repo, "rev-parse", "HEAD^{tree}")),
    ):
        pass
