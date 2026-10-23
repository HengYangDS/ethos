"""Official OpenSpec projection is the sole input to Commitment compilation."""

from __future__ import annotations

import hashlib
import json
import shutil
from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING
from unittest.mock import Mock

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
    monkeypatch.setattr(compilation, "openspec_tree_projection", lambda *_a: nullcontext(root))

    def batch(projection, command, commands):
        return tuple(
            compilation.openspec_cli.run_json(projection, command, args) for args in commands
        )

    monkeypatch.setattr(compilation.openspec_cli, "run_json_batch", batch)
    return root


def test_official_projection_compiles_minimal_commitment() -> None:
    projection = _requirement_projection()

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.id == "change:minimal-authority"
    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Commitment.model_validate(commitment.model_dump() | {"predecessors": ()})


@pytest.mark.parametrize("with_requirement", [False, True])
def test_native_removal_compiles_its_target_without_fabricated_scenarios(
    *, with_requirement: bool
) -> None:
    """Removal is a named operation, not a continuing requirement or spec-free intent."""
    removal = {
        "spec": "authority",
        "operation": "REMOVED",
        "requirements": [
            {
                "name": "Retired parallel authority",
                "text": "**Reason**: The unique owner replaces this mechanism.",
                "scenarios": [],
            }
        ],
    }
    added = _requirement_projection()["deltas"][0] | {"operation": "ADDED"}
    projection = {
        "id": "minimal-authority",
        "deltas": [removal, *([added] if with_requirement else [])],
    }

    result = commitment_from_projection("minimal-authority", projection)

    expected = (f"authority:remove:{json.dumps(removal['requirements'][0], sort_keys=True)}",)
    if with_requirement:
        expected += (
            "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
            "authority:scenario:- **WHEN** selected\n- **THEN** compile",
        )
    assert result == Commitment(
        schema_version=3, id="change:minimal-authority", acceptance=expected
    )
    removal["requirements"][0]["name"] = "Another retired authority"
    assert commitment_from_projection("minimal-authority", projection).digest() != result.digest()
    removal["requirements"][0]["name"] = "Retired parallel authority"
    removal["requirements"][0]["text"] = "**Migration**: Preserve the original evidence."
    assert commitment_from_projection("minimal-authority", projection).digest() != result.digest()


def test_native_removal_requires_the_official_target_name() -> None:
    """A removal body cannot substitute for the name native archive matches."""
    projection = _requirement_projection({"text": "Remove an unnamed rule", "scenarios": []})
    projection["deltas"][0]["operation"] = "REMOVED"

    with pytest.raises(ValueError, match="openspec_show_invalid:minimal-authority"):
        commitment_from_projection("minimal-authority", projection)


@pytest.mark.parametrize("header", [True, False])
def test_native_removal_loads_real_working_and_exact_tree_intent(
    tmp_path: Path, *, header: bool
) -> None:
    """Keep official header and bullet removal targets through the actual native reader."""
    root = init_git_repo(tmp_path / "repo")
    write_active_commitment(root, change_id="fixture-removal")
    spec = root / "openspec/changes/fixture-removal/specs/contracts/spec.md"
    removed = (
        "### Requirement: Governed fixture\n\n"
        "**Reason**: A new owner replaces this fixture obligation.\n\n"
        "**Migration**: Preserve prior proof through Git.\n"
        if header
        else "- `### Requirement: Governed fixture`\n"
    )
    spec.write_text("## REMOVED Requirements\n\n" + removed)
    (projection,) = compilation.openspec_cli.run_json_batch(
        root, None, (("show", "fixture-removal", "--type", "change", "--json"),)
    )
    assert projection["exit_code"] == 0
    assert not projection["parse_error"]
    delta = projection["json"]["deltas"][0]
    assert delta["operation"] == "REMOVED"
    assert delta["requirements"][0]["name"] == "Governed fixture"
    expected = commitment_from_projection("fixture-removal", projection["json"])

    observed = compilation.load_openspec_commitment(root, change_id="fixture-removal")
    head = commit_fixture(root, "declare removal-only intent")
    exact = compilation.load_openspec_commitment(root, tree_ref=head, change_id="fixture-removal")

    assert observed == exact == expected
    assert all(item.startswith("contracts:remove:") for item in observed.acceptance)


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
    run_batch = compilation.openspec_cli.run_json_batch

    def observe(root, command, commands):
        calls.extend(commands)
        return run_batch(root, command, commands)

    monkeypatch.setattr(compilation.openspec_cli, "run_json_batch", observe)

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
    assert calls
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
    ("profile_state", "changes", "change_id", "error"),
    [
        ("disabled", (), None, "openspec_profile_not_enabled"),
        ("enabled", (), None, "openspec_active_change_missing"),
        (
            "enabled",
            ("one", "two"),
            None,
            "openspec_active_change_ambiguous:one,two",
        ),
        ("enabled", (), "archive/bad", "openspec_change_required"),
    ],
)
def test_load_commitment_rejects_missing_or_ambiguous_authority(
    compilation_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile_state: str,
    changes: tuple[str, ...],
    change_id: str | None,
    error: str,
) -> None:

    monkeypatch.setattr(
        compilation,
        "openspec_profile_enabled",
        lambda *_a, **_k: profile_state == "enabled",
    )
    monkeypatch.setattr(
        compilation.openspec_cli,
        "run_json",
        lambda *_a, **_k: {
            "exit_code": 0,
            "parse_error": "",
            "json": {"changes": [{"name": name, "status": "in-progress"} for name in changes]},
        },
    )

    with pytest.raises(ValueError, match=error):
        compilation.load_openspec_commitment(compilation_root, change_id=change_id)


@pytest.mark.parametrize(
    ("command", "tree_ref"),
    [(("openspec",), "a" * 40), (("openspec",), "HEAD"), (None, "HEAD")],
)
def test_attested_archive_reuses_accepted_intent_without_current_cli_probe(
    compilation_root: Path, monkeypatch: pytest.MonkeyPatch, command, tree_ref
) -> None:
    archived = commitment_fixture(id="change:archived")
    show = Mock(return_value={"exit_code": 1, "parse_error": "", "json": {}})
    monkeypatch.setattr(compilation.openspec_cli, "run_json", show)
    resolver = Mock(return_value=command)
    monkeypatch.setattr(compilation.openspec_cli, "openspec_base_command", resolver)
    monkeypatch.setattr(
        compilation,
        "attested_archive_transition",
        lambda *_a, **_k: (archived, {"attestation_id": "archive"}),
    )

    loaded = compilation.load_openspec_commitment(
        compilation_root,
        change_id="archived",
        tree_ref=tree_ref,
    )
    assert loaded == archived
    assert show.call_count == (tree_ref != "HEAD")
    if tree_ref == "HEAD":
        resolver.assert_not_called()


def _named(name: str, text: str, *scenarios: tuple[str, str]) -> dict[str, object]:
    return {
        "name": name,
        "text": text,
        "scenarios": [{"name": title, "rawText": raw} for title, raw in scenarios],
    }


def test_named_encoding_keeps_requirements_with_equal_bodies_distinct() -> None:
    """Names carry acceptance identity, so equal bodies under two names stay two items."""
    when = "- **WHEN** selected\n- **THEN** compile"
    projection = _requirement_projection(
        _named("One native intent", "Official OpenSpec is the sole intent.", ("Selected", when)),
        _named("Profile routing", "Official OpenSpec is the sole intent.", ("Routed", when)),
    )

    commitment = commitment_from_projection("minimal-authority", projection, named=True)

    assert commitment.acceptance == (
        'authority:requirement:["One native intent","Official OpenSpec is the sole intent."]',
        'authority:requirement:["Profile routing","Official OpenSpec is the sole intent."]',
        (
            'authority:scenario:["One native intent","Selected",'
            '"- **WHEN** selected\\n- **THEN** compile"]'
        ),
        (
            'authority:scenario:["Profile routing","Routed",'
            '"- **WHEN** selected\\n- **THEN** compile"]'
        ),
    )
    with pytest.raises(ValidationError):
        commitment_from_projection("minimal-authority", projection)
    requirements = projection["deltas"][0]["requirements"]
    requirements.reverse()
    named = partial(commitment_from_projection, "minimal-authority", named=True)
    assert named(projection).digest() == commitment.digest()
    requirements[0]["scenarios"][0]["rawText"] += "\n- **AND** keep the profile"
    assert named(projection).digest() != commitment.digest()


@pytest.mark.parametrize("missing", ["requirement", "scenario"])
def test_named_encoding_refuses_an_unnamed_requirement_or_scenario(missing: str) -> None:
    """A projection that lacks a name cannot be compiled into named acceptance identity."""
    requirement = _named("Native validation", "Native validation SHALL run first.", ("Ready", "x"))
    if missing == "requirement":
        del requirement["name"]
    else:
        del requirement["scenarios"][0]["name"]
    projection = _requirement_projection(requirement)
    with pytest.raises(ValueError, match="openspec_acceptance_missing"):
        commitment_from_projection("minimal-authority", projection, named=True)
    assert commitment_from_projection("minimal-authority", projection).acceptance
