"""Official OpenSpec projection is the sole input to Commitment compilation."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

import ethos.adapters.openspec.commitment as compilation
from ethos.adapters.openspec.commitment import commitment_from_projection
from ethos.contracts.semantic import Commitment
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _materialize_spec_free_change(root: Path, *, tasks: str) -> Path:
    (root / "openspec").mkdir()
    (root / "openspec/config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    change_root = root / "openspec/changes/dependency-refresh"
    change_root.mkdir(parents=True)
    for name, content in {
        ".openspec.yaml": "schema: spec-driven\nskip_specs: true\n",
        "proposal.md": """## Why

Refresh the dependency.

## What Changes

- Use the stable package.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

Supply chain only.
""",
        "design.md": "## Decisions\n\nUse the stable package.\n",
        "tasks.md": tasks,
    }.items():
        (change_root / name).write_text(content, encoding="utf-8")
    return change_root


def test_official_projection_compiles_minimal_commitment() -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "authority",
                "requirements": [
                    {
                        "text": "Official OpenSpec is the sole tracked intent carrier.",
                        "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
                    }
                ],
            }
        ],
    }

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.id == "change:minimal-authority"
    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Commitment.model_validate(commitment.model_dump() | {"predecessors": ()})


def test_removed_requirements_do_not_become_acceptance_obligations() -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "authority",
                "operation": "REMOVED",
                "requirements": [
                    {
                        "text": "Retired parallel authority remains supported.",
                        "scenarios": [],
                    }
                ],
            },
            {
                "spec": "authority",
                "operation": "ADDED",
                "requirements": [
                    {
                        "text": "Official OpenSpec is the sole tracked intent carrier.",
                        "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
                    }
                ],
            },
        ],
    }

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )


def test_official_spec_free_projection_compiles_minimal_commitment() -> None:
    projection = {
        "id": "dependency-refresh",
        "deltas": [
            {
                "spec": "BREAKING",
                "operation": "MODIFIED",
                "description": "lock the repository package to the stable release.",
            }
        ],
    }
    status = {
        "changeName": "dependency-refresh",
        "isComplete": True,
        "artifacts": [
            {"id": "proposal", "status": "done", "requires": []},
            {"id": "specs", "status": "skipped", "requires": ["proposal"]},
            {"id": "design", "status": "done", "requires": ["proposal"]},
            {"id": "tasks", "status": "done", "requires": ["specs", "design"]},
        ],
    }
    artifact_digests = {
        name: hashlib.sha256(name.encode()).hexdigest()
        for name in ("metadata", "proposal", "design", "tasks")
    }

    first = commitment_from_projection(
        "dependency-refresh",
        projection,
        status=status,
        artifact_digests=artifact_digests,
    )
    second = commitment_from_projection(
        "dependency-refresh",
        projection,
        status=status,
        artifact_digests=artifact_digests,
    )

    assert first == second
    assert first.acceptance == (
        f"openspec:artifact:design:sha256:{artifact_digests['design']}",
        f"openspec:artifact:metadata:sha256:{artifact_digests['metadata']}",
        f"openspec:artifact:proposal:sha256:{artifact_digests['proposal']}",
        f"openspec:artifact:tasks:sha256:{artifact_digests['tasks']}",
        "openspec:change:dependency-refresh",
        "openspec:specs:skipped",
    )


@pytest.mark.parametrize(
    "status",
    [
        {
            "changeName": "minimal-authority",
            "isComplete": True,
            "artifacts": [
                {"id": "proposal", "status": "done", "requires": []},
                {"id": "specs", "status": "done", "requires": ["proposal"]},
                {"id": "design", "status": "done", "requires": ["proposal"]},
                {"id": "tasks", "status": "done", "requires": ["specs", "design"]},
            ],
        },
        {
            "changeName": "minimal-authority",
            "isComplete": False,
            "artifacts": [
                {"id": "proposal", "status": "done", "requires": []},
                {"id": "specs", "status": "skipped", "requires": ["proposal"]},
                {"id": "design", "status": "done", "requires": ["proposal"]},
                {"id": "tasks", "status": "done", "requires": ["specs", "design"]},
            ],
        },
    ],
)
def test_zero_requirement_projection_requires_valid_official_spec_free_planning_graph(
    status: dict[str, object],
) -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "not-a-capability",
                "operation": "MODIFIED",
                "description": "official show emitted proposal prose rather than requirements",
            }
        ],
    }

    with pytest.raises(ValueError, match="openspec_acceptance_missing"):
        commitment_from_projection(
            "minimal-authority",
            projection,
            status=status,
            artifact_digests={
                name: hashlib.sha256(name.encode()).hexdigest()
                for name in ("metadata", "proposal", "design", "tasks")
            },
        )


@pytest.mark.parametrize(
    ("projection", "error"),
    [
        (None, "openspec_show_invalid:minimal-authority"),
        ({"id": "other", "deltas": []}, "openspec_show_invalid:minimal-authority"),
        ({"id": "minimal-authority", "deltas": []}, "openspec_acceptance_missing"),
        ({"id": "minimal-authority", "deltas": [None]}, "openspec_show_invalid"),
        (
            {"id": "minimal-authority", "deltas": [{"spec": "", "requirements": []}]},
            "openspec_show_invalid",
        ),
        (
            {
                "id": "minimal-authority",
                "deltas": [{"spec": "authority", "requirements": [None]}],
            },
            "openspec_show_invalid",
        ),
        (
            {
                "id": "minimal-authority",
                "deltas": [{"spec": "authority", "requirements": [{"text": "", "scenarios": []}]}],
            },
            "openspec_acceptance_missing",
        ),
        (
            {
                "id": "minimal-authority",
                "deltas": [
                    {
                        "spec": "authority",
                        "requirements": [{"text": "required", "scenarios": [{}]}],
                    }
                ],
            },
            "openspec_acceptance_missing",
        ),
    ],
)
def test_commitment_compilation_fails_closed_on_incomplete_official_projection(
    projection: object,
    error: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        commitment_from_projection("minimal-authority", projection)


def test_load_commitment_selects_one_active_change_and_checks_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "authority",
                "requirements": [
                    {
                        "text": "Official OpenSpec remains authoritative.",
                        "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
                    }
                ],
            }
        ],
    }
    expected = commitment_from_projection("minimal-authority", projection)

    @contextmanager
    def selected_projection(_repo: Path, _tree_ref: str | None):
        yield tmp_path

    monkeypatch.setattr(compilation, "openspec_profile_enabled", lambda *_a, **_k: True)
    monkeypatch.setattr(compilation, "_openspec_projection", selected_projection)
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", lambda: ("openspec",))

    def run_json(_root: Path, _command: tuple[str, ...], args: tuple[str, ...]):
        return (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"changes": [{"name": "minimal-authority"}]},
            }
            if args[0] == "list"
            else {"exit_code": 0, "parse_error": "", "json": projection}
        )

    monkeypatch.setattr(compilation.openspec_cli, "run_json", run_json)

    loaded = compilation.load_openspec_commitment(
        tmp_path,
        expected_digest=expected.digest(),
    )

    assert loaded == expected
    with pytest.raises(ValueError, match="commitment_digest_mismatch"):
        compilation.load_openspec_commitment(tmp_path, expected_digest="f" * 64)


def test_load_commitment_compiles_planned_spec_free_projection_before_tasks_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change_root = _materialize_spec_free_change(
        tmp_path,
        tasks="- [ ] Refresh and prove the package.\n",
    )

    monkeypatch.setattr(compilation, "openspec_profile_enabled", lambda *_a, **_k: True)
    calls: list[tuple[str, ...]] = []
    run_json = compilation.openspec_cli.run_json
    monkeypatch.setattr(
        compilation.openspec_cli,
        "run_json",
        lambda root, command, args: (calls.append(args), run_json(root, command, args))[1],
    )

    planned = compilation.load_openspec_commitment(tmp_path)

    assert planned.acceptance == (
        *(
            f"openspec:artifact:{kind}:sha256:"
            f"{hashlib.sha256((change_root / filename).read_bytes()).hexdigest()}"
            for kind, filename in (
                ("design", "design.md"),
                ("metadata", ".openspec.yaml"),
                ("proposal", "proposal.md"),
                ("tasks", "tasks.md"),
            )
        ),
        "openspec:change:dependency-refresh",
        "openspec:specs:skipped",
    )
    (change_root / "tasks.md").write_text(
        "- [x] Refresh and prove the package.\n",
        encoding="utf-8",
    )
    progressed = compilation.load_openspec_commitment(tmp_path)

    assert progressed == planned
    assert all(args[:2] != ("instructions", "apply") for args in calls)


@pytest.mark.parametrize(
    ("profile_state", "command", "changes", "change_id", "error"),
    [
        ("disabled", ("openspec",), (), None, "openspec_profile_not_enabled"),
        ("enabled", None, (), None, "openspec_official_cli_missing"),
        ("enabled", ("openspec",), (), None, "openspec_active_change_missing"),
        (
            "enabled",
            ("openspec",),
            ("one", "two"),
            None,
            "openspec_active_change_ambiguous:one,two",
        ),
        ("enabled", ("openspec",), (), "archive/bad", "openspec_change_required"),
    ],
)
def test_load_commitment_rejects_missing_or_ambiguous_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile_state: str,
    command: tuple[str, ...] | None,
    changes: tuple[str, ...],
    change_id: str | None,
    error: str,
) -> None:
    @contextmanager
    def selected_projection(_repo: Path, _tree_ref: str | None):
        yield tmp_path

    monkeypatch.setattr(
        compilation,
        "openspec_profile_enabled",
        lambda *_a, **_k: profile_state == "enabled",
    )
    monkeypatch.setattr(compilation, "_openspec_projection", selected_projection)
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", lambda: command)
    monkeypatch.setattr(
        compilation.openspec_cli,
        "run_json",
        lambda *_a, **_k: {
            "exit_code": 0,
            "parse_error": "",
            "json": {"changes": [{"name": name} for name in changes]},
        },
    )
    monkeypatch.setattr(compilation, "_archived_commitment", lambda *_a, **_k: None)

    with pytest.raises(ValueError, match=error):
        compilation.load_openspec_commitment(tmp_path, change_id=change_id)


def test_load_commitment_uses_exact_attested_archive_when_official_show_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archived = commitment_fixture(id="change:archived")

    @contextmanager
    def selected_projection(_repo: Path, _tree_ref: str | None):
        yield tmp_path

    monkeypatch.setattr(compilation, "openspec_profile_enabled", lambda *_a, **_k: True)
    monkeypatch.setattr(compilation, "_openspec_projection", selected_projection)
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        compilation.openspec_cli,
        "run_json",
        lambda *_a, **_k: {"exit_code": 1, "parse_error": "", "json": {}},
    )
    monkeypatch.setattr(
        compilation,
        "attested_archive_transition",
        lambda *_a, **_k: (archived, {"attestation_id": "archive"}),
    )

    loaded = compilation.load_openspec_commitment(
        tmp_path,
        change_id="archived",
        tree_ref="a" * 40,
    )

    assert loaded == archived
