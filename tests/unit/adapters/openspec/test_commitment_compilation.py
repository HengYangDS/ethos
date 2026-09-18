"""Official OpenSpec projection is the sole input to Commitment compilation."""

from __future__ import annotations

import hashlib
import shutil
from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

import ethos.adapters.openspec.commitment as compilation
from ethos.adapters.openspec.commitment import commitment_from_projection
from ethos.contracts.semantic import Commitment
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _materialize_spec_free_change(root: Path, *, tasks: str) -> Path:
    """Reuse the native official carrier and select its supported spec-free mode."""
    write_active_commitment(root, change_id="dependency-refresh")
    change = root / "openspec/changes/dependency-refresh"
    shutil.rmtree(change / "specs")
    (change / ".openspec.yaml").write_text("schema: spec-driven\nskip_specs: true\n")
    (change / "tasks.md").write_text(tasks)
    return change


def _requirement_projection(*requirements: object, spec: str = "authority") -> dict:
    """Share native carrier structure while leaving expected observations independent."""
    values = requirements or (
        {
            "text": "Official OpenSpec is the sole tracked intent carrier.",
            "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
        },
    )
    return {"id": "minimal-authority", "deltas": [{"spec": spec, "requirements": list(values)}]}


@pytest.fixture
def compilation_root(tmp_path, monkeypatch):
    """Isolate official transport while retaining real compilation and validation."""
    root = init_git_repo(tmp_path / "repo")
    monkeypatch.setattr(compilation, "openspec_profile_enabled", lambda *_a, **_k: True)
    monkeypatch.setattr(compilation, "_openspec_projection", lambda *_a: nullcontext(root))
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    return root


@pytest.mark.parametrize("removed", [False, True])
def test_official_projection_compiles_minimal_commitment(*, removed: bool) -> None:
    projection = _requirement_projection()
    if removed:
        removed = _requirement_projection(
            {"text": "Retired parallel authority remains supported.", "scenarios": []}
        )["deltas"][0] | {"operation": "REMOVED"}
        projection["deltas"].insert(0, removed)
        projection["deltas"][1]["operation"] = "ADDED"

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.id == "change:minimal-authority"
    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Commitment.model_validate(commitment.model_dump() | {"predecessors": ()})


@pytest.mark.parametrize("with_requirement", [False, True])
def test_native_rename_compiles_a_bound_relation_without_fabricated_requirements(
    *, with_requirement: bool
) -> None:
    """A native rename is material intent, alone or alongside changed behavior."""
    rename = {
        "spec": "quality",
        "operation": "RENAMED",
        "rename": {"from": "Hosted budget tool supply", "to": "Native verification tool supply"},
    }
    requirement = _requirement_projection(
        {
            "text": "Native supply SHALL be rootless.",
            "scenarios": [
                {"rawText": "- **WHEN** unprivileged\n- **THEN** materialize in owned cache"}
            ],
        },
        spec="quality",
    )["deltas"][0] | {"operation": "MODIFIED"}
    projection = {
        "id": "native-supply",
        "deltas": [rename, *([requirement] if with_requirement else [])],
    }

    result = commitment_from_projection("native-supply", projection)

    assert (
        'quality:rename:{"from": "Hosted budget tool supply", '
        '"to": "Native verification tool supply"}' in result.acceptance
    )
    assert len(result.acceptance) == (3 if with_requirement else 1)
    rename["rename"]["to"] = "Different destination"
    assert commitment_from_projection("native-supply", projection).digest() != result.digest()


@pytest.mark.parametrize(
    "rename",
    [
        None,
        {},
        {"from": "Old"},
        {"from": "", "to": "New"},
        {"from": 1, "to": "New"},
        {"from": "Same", "to": "Same"},
    ],
)
def test_native_rename_rejects_incomplete_or_ambiguous_relation(rename: object) -> None:
    """Neither missing endpoints nor an identity rename can form accepted intent."""
    projection = {
        "id": "native-supply",
        "deltas": [{"spec": "quality", "operation": "RENAMED", "rename": rename}],
    }

    with pytest.raises(ValueError, match="openspec_show_invalid"):
        commitment_from_projection("native-supply", projection)


@pytest.mark.parametrize(
    ("complete", "spec_state"), [(True, "skipped"), (True, "done"), (False, "skipped")]
)
def test_official_spec_free_projection_compiles_minimal_commitment(*, complete, spec_state) -> None:
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
        "isComplete": complete,
        "artifacts": [
            {"id": "proposal", "status": "done", "requires": []},
            {"id": "specs", "status": spec_state, "requires": ["proposal"]},
            {"id": "design", "status": "done", "requires": ["proposal"]},
            {"id": "tasks", "status": "done", "requires": ["specs", "design"]},
        ],
    }
    artifact_digests = {
        name: hashlib.sha256(name.encode()).hexdigest()
        for name in ("metadata", "proposal", "design", "tasks")
    }

    compile_intent = partial(
        commitment_from_projection,
        "dependency-refresh",
        projection,
        status=status,
        artifact_digests=artifact_digests,
    )
    if not complete or spec_state != "skipped":
        with pytest.raises(ValueError, match="openspec_acceptance_missing"):
            compile_intent()
        return
    first, second = compile_intent(), compile_intent()
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
    ("projection", "error"),
    [
        (None, "openspec_show_invalid:minimal-authority"),
        ({"id": "other", "deltas": []}, "openspec_show_invalid:minimal-authority"),
        ({"id": "minimal-authority", "deltas": []}, "openspec_acceptance_missing"),
        ({"id": "minimal-authority", "deltas": [None]}, "openspec_show_invalid"),
        (
            _requirement_projection(spec=""),
            "openspec_show_invalid",
        ),
        (
            _requirement_projection(None),
            "openspec_show_invalid",
        ),
        (
            _requirement_projection({"text": "", "scenarios": []}),
            "openspec_acceptance_missing",
        ),
        (
            _requirement_projection({"text": "required", "scenarios": [{}]}),
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
    compilation_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projection = _requirement_projection()
    expected = commitment_from_projection("minimal-authority", projection)

    def run_json(_root: Path, _command: tuple[str, ...], args: tuple[str, ...]):
        return (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"changes": [{"name": "minimal-authority", "status": "in-progress"}]},
            }
            if args[0] == "list"
            else {"exit_code": 0, "parse_error": "", "json": projection}
        )

    monkeypatch.setattr(compilation.openspec_cli, "run_json", run_json)

    loaded = compilation.load_openspec_commitment(
        compilation_root,
        expected_digest=expected.digest(),
    )

    assert loaded == expected
    with pytest.raises(ValueError, match="commitment_digest_mismatch"):
        compilation.load_openspec_commitment(compilation_root, expected_digest="f" * 64)


def test_load_commitment_compiles_planned_spec_free_projection_before_tasks_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = init_git_repo(tmp_path / "repo")
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
    head = commit_fixture(tmp_path, "declare spec-free acceptance")
    assert (
        compilation.load_openspec_commitment(tmp_path, tree_ref=head, official_status={}) == planned
    )
    before = len(calls)
    with pytest.raises(ValueError, match="openspec_acceptance_missing"):
        compilation.load_openspec_commitment(
            tmp_path, change_id="dependency-refresh", official_status={}
        )
    assert not any(args[0] == "status" for args in calls[before:])


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
    compilation_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile_state: str,
    command: tuple[str, ...] | None,
    changes: tuple[str, ...],
    change_id: str | None,
    error: str,
) -> None:

    monkeypatch.setattr(
        compilation,
        "openspec_profile_enabled",
        lambda *_a, **_k: profile_state == "enabled",
    )
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", lambda: command)
    monkeypatch.setattr(
        compilation.openspec_cli,
        "run_json",
        lambda *_a, **_k: {
            "exit_code": 0,
            "parse_error": "",
            "json": {"changes": [{"name": name, "status": "in-progress"} for name in changes]},
        },
    )
    monkeypatch.setattr(compilation, "_archived_commitment", lambda *_a, **_k: None)

    with pytest.raises(ValueError, match=error):
        compilation.load_openspec_commitment(compilation_root, change_id=change_id)


def test_load_commitment_uses_exact_attested_archive_when_official_show_is_absent(
    compilation_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archived = commitment_fixture(id="change:archived")

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
        compilation_root,
        change_id="archived",
        tree_ref="a" * 40,
    )

    assert loaded == archived
