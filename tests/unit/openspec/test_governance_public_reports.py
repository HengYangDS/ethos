"""Public OpenSpec governance edge reports."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

import ethos.adapters.openspec.cli as cli
import ethos.adapters.openspec.governance as governance
import ethos.adapters.openspec.lifecycle.scope as lifecycle_scope
import ethos.adapters.openspec.lifecycle.validation as lifecycle_validation
import ethos.adapters.openspec.selection as selection
import tests.support.governed_repository as fixture
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.openspec_lifecycle import official_validation_payload


def _repo(tmp_path: Path) -> Path:
    root = fixture.init_git_repo(tmp_path / "repo")
    fixture.write_test_profile(root, openspec={"material_paths": ["openspec/**"]})
    (root / "openspec/specs").mkdir(parents=True)
    (root / "openspec/config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    return root


def test_governance_reports_not_applicable_without_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("ETHOS_CHANGE", "missing")
    root = fixture.init_git_repo(tmp_path / "repo")

    report = governance.openspec_governance_report(root, lifecycle=True)

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "not_applicable",
        [],
    )
    assert report["official_cli"] == {"available": False, "base_command": []}


def test_governance_selects_ambiguous_intent_once_per_observation(monkeypatch, tmp_path):
    """One request must not rescan lane provenance for the same OpenSpec list."""
    root = _repo(tmp_path)
    fixture.write_active_commitment(root, change_id="first")
    fixture.write_active_commitment(root, change_id="second")
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    calls: list[int] = []

    def observe_lineage(*_args):
        calls.append(1)

    monkeypatch.setattr(selection, "_lane_contribution", observe_lineage)
    report = governance.openspec_governance_report(
        root, lifecycle=True, changed_paths=("openspec/changes/first/tasks.md",)
    )

    assert report["required_gaps"] == ["openspec_active_change_ambiguous:first,second"]
    assert len(calls) == 1


@pytest.mark.parametrize("selection", ["explicit", "environment"])
def test_governance_rejects_archive_and_invalid_active_identifiers(
    monkeypatch, tmp_path, selection
):
    root = _repo(tmp_path)
    (root / "openspec/changes/archive/archived").mkdir(parents=True)
    monkeypatch.setattr(cli, "openspec_base_command", lambda: (_ for _ in ()).throw(AssertionError))

    def report(change):
        monkeypatch.setenv("ETHOS_CHANGE", change if selection == "environment" else "other")
        return governance.openspec_governance_report(
            root, change=change if selection == "explicit" else None, lifecycle=True
        )

    archived = report("archived")
    invalid = report("20260810-invalid")
    empty = report("")
    assert empty["verdict"] == "block"
    assert empty["required_gaps"] == ["openspec_active_change_identifier_invalid:"]

    assert archived["required_gaps"] == [
        "openspec_active_change_identifier_is_archive_directory:archived"
    ]
    assert invalid["required_gaps"] == [
        "openspec_active_change_identifier_invalid:20260810-invalid"
    ]
    assert archived["commands"] == {"doctor": {}, "list": {}, "status": {}, "validate": {}}


def test_governance_reports_cli_unavailable_and_optional_absent_workspace(monkeypatch, tmp_path):
    root, _candidate = fixture.start_adopted_candidate(tmp_path)
    monkeypatch.setattr(cli, "openspec_base_command", lambda **_kwargs: None)

    unavailable = governance.openspec_governance_report(root)
    absent = fixture.init_git_repo(tmp_path / "absent")
    fixture.write_test_profile(absent, openspec={"material_paths": ["docs/**"]})
    not_applicable = governance.openspec_governance_report(absent, require_workspace=False)

    for report in (unavailable, governance.openspec_validation_report(root)):
        assert report["verdict"] == "block"
        assert "openspec_official_cli_missing" in report["required_gaps"]
    assert (not_applicable["verdict"], not_applicable["state"]) == ("pass", "not_applicable")


@pytest.mark.parametrize("fault", ["timeout", "malformed", "empty"])
def test_governance_preserves_failed_observation_and_empty_native_results(
    monkeypatch, tmp_path, fault
):
    """A failed batch is distinct from a successful observation with no Change."""
    root, _candidate = fixture.start_adopted_candidate(tmp_path)
    original = cli.run_json_batch
    calls = []

    def observe(root, base, commands):
        calls.append(commands)
        rows = list(original(root, base, commands))
        for index, args in enumerate(commands):
            if fault == "timeout" or (fault == "malformed" and args[0] != "doctor"):
                rows[index]["parse_error"] = (
                    "openspec_command_timeout" if fault == "timeout" else "malformed"
                )
        return tuple(rows)

    monkeypatch.setattr(cli, "run_json_batch", observe)
    report = governance.openspec_governance_report(root)
    assert len(calls) == 1
    assert report["verdict"] == ("pass" if fault == "empty" else "block")
    assert report["commands"]["status"] == {}
    expected = {
        "timeout": {"openspec_doctor_unhealthy", "openspec_doctor_json_parse_failed"},
        "malformed": {
            f"openspec_{name}_json_parse_failed" for name in ("config", "list", "validate")
        },
        "empty": set(),
    }[fault]
    assert expected <= set(report["required_gaps"])
    if fault == "empty":
        assert (report["change"], report["required_gaps"]) == (None, [])


@pytest.mark.parametrize("fault", ["invalid-intent", "unexplained-failure"])
def test_public_plan_batches_fresh_intent_and_preserves_native_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    """Each public plan observes current intent with bounded native startup and no false pass."""
    workspace = fixture.prepared_work_lane(tmp_path)
    commands = []
    native = subprocess.Popen.__init__

    def observe(process, command, *args, **kwargs):
        if "node" in str(command[0]):
            commands.append(command)
        return native(process, command, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "__init__", observe)
    assert run_ethos("plan", "--json", cwd=workspace.worktree)["verdict"] == "pass"
    assert len(commands) <= 3, commands
    commands.clear()
    original = cli.run_json_batch
    observed: list[dict[str, object]] = []

    def failed_validation(root, command, requested):
        results = original(root, command, requested)
        for args, result in zip(requested, results, strict=True):
            if args[:1] == ("validate",):
                result.update(
                    exit_code=1,
                    stderr="native validation stopped without item diagnostics",
                    json=official_validation_payload(root, []),
                )
                observed.append(result)
        return results

    if fault == "unexplained-failure":
        monkeypatch.setattr(cli, "run_json_batch", failed_validation)
    else:
        spec = workspace.worktree / "openspec/changes/fixture-change/specs/contracts/spec.md"
        spec.write_text("# Invalid current acceptance\n")
    projected = run_ethos("plan", "--json", cwd=workspace.worktree)
    assert projected["verdict"] == "block", projected
    assert len(commands) <= 3, commands
    assert bool(observed) is (fault == "unexplained-failure")
    assert (
        "openspec_validate_failed"
        if observed
        else "openspec_validation_failed:change:fixture-change"
    ) in projected["required_gaps"]


@pytest.mark.parametrize("mode", ["empty", "info", "canonical-warning", "mixed"])
def test_locked_native_validation_preserves_empty_information_and_warnings(
    tmp_path: Path, mode: str, monkeypatch
) -> None:
    """The registered gate uses locked native supply even without ambient OpenSpec."""
    root = _repo(tmp_path)
    if mode != "empty":
        fixture.write_active_commitment(root)
        change = root / "openspec/changes/fixture-change"
        shutil.rmtree(change / "specs")
        (change / ".openspec.yaml").write_text("schema: spec-driven\nskip_specs: true\n")
        if mode == "canonical-warning":
            long_spec = root / "openspec/specs/long/spec.md"
            long_spec.parent.mkdir()
            long_spec.write_text(
                "# Long Specification\n\n## Purpose\n\n"
                "Check that warnings in current canonical requirements "
                "remain visible to the repository quality gate.\n\n"
                "## Requirements\n\n### Requirement: Long content\n\n"
                + "The system SHALL retain the complete observable meaning of this requirement. "
                * 8
                + "\n\n#### Scenario: The reader validates it\n\n"
                "- **WHEN** the current spec is validated\n"
                "- **THEN** the native finding remains visible\n",
                encoding="utf-8",
            )
        elif mode == "mixed":
            invalid = root / "openspec/specs/invalid/spec.md"
            invalid.parent.mkdir()
            invalid.write_text("# Invalid native specification\n")
    monkeypatch.setenv("PATH", os.defpath)
    observed = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "openspec", "--json", cwd=root
    )
    failed = mode in {"canonical-warning", "mixed"}
    assert observed.returncode == (1 if failed else 0), observed.stdout
    checks = json.loads(observed.stdout)["data"]["checks"]
    check = next(item for item in checks if item["action_id"] == "openspec")
    result = json.loads(check["stdout"])["providers"][0]["report"]["validation"]
    items = result["json"]["items"]
    assert result["parse_error"] == ""
    assert result["exit_code"] == (1 if failed else 0)
    if mode == "empty":
        assert items == []
    else:
        info = next(item for item in items if item["id"] == "fixture-change")
        assert info["valid"] is True
        assert any(issue["level"] == "INFO" for issue in info["issues"])
    if mode == "canonical-warning":
        warning = next(item for item in items if item["id"] == "long")
        assert warning["valid"] is False
        assert any(
            issue["level"] == "WARNING" and issue["path"] == "requirements[0]"
            for issue in warning["issues"]
        )
    expected = (
        ["openspec_validation_failed:spec:invalid"]
        if mode == "mixed"
        else ["openspec_validation_failed:spec:long"]
        if mode == "canonical-warning"
        else []
    )
    assert lifecycle_validation.validation_failures(result["json"]) == expected


@pytest.mark.parametrize("mode", ["unsynced", "early-synced", "near-miss", "conflict"])
def test_locked_native_archive_preserves_removal_meaning(tmp_path: Path, mode: str) -> None:
    """Native removal is idempotent, but misspelled or conflicting intent cannot write."""
    root = _repo(tmp_path)
    fixture.write_active_commitment(root)
    change = root / "openspec/changes/fixture-change"
    main = root / "openspec/specs/contracts/spec.md"
    retained = main.read_bytes()
    legacy = (
        "\n### Requirement: Legacy capability\n\n"
        "The system SHALL retain legacy behavior until explicitly retired.\n\n"
        "#### Scenario: Legacy operation\n\n"
        "- **WHEN** legacy behavior is requested\n"
        "- **THEN** the legacy response is available\n"
    )
    if mode != "early-synced":
        main.write_bytes(retained + legacy.encode())
    delta = change / "specs/contracts/spec.md"
    content = (
        "## REMOVED Requirements\n\n### Requirement: Legacy capability\n\n"
        "**Reason**: The legacy behavior is no longer needed.\n\n"
        "**Migration**: Use the governed fixture.\n"
    )
    if mode == "near-miss":
        content = content.replace("Legacy capability", "legacy capability")
    if mode == "conflict":
        content += (
            "\n## RENAMED Requirements\n\n"
            "- FROM: `### Requirement: Legacy capability`\n"
            "- TO: `### Requirement: Renamed capability`\n"
        )
    delta.write_text(content)
    (change / ".openspec.yaml").write_text("schema: spec-driven\n")
    tasks = change / "tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))

    def snapshot():
        return {
            p.relative_to(root): p.read_bytes()
            for p in (root / "openspec").rglob("*")
            if p.is_file()
        }

    before = snapshot()
    command = cli.openspec_base_command()
    assert command is not None
    result = cli.run_json(root, command, ("archive", "fixture-change", "--yes", "--json"))
    assert result["parse_error"] == ""
    if mode in {"near-miss", "conflict"}:
        assert result["exit_code"] != 0, result
        assert change.is_dir()
        assert snapshot() == before
        return
    assert result["exit_code"] == 0, result
    assert not change.exists()
    archive = result["json"]["archive"]
    archived = root / "openspec/changes/archive" / archive["archivedAs"]
    assert (archived / "specs/contracts/spec.md").read_text() == content
    assert main.read_bytes() == retained
    assert archive["specsUpdated"] is (mode == "unsynced")
    assert archive["totals"] == {
        "added": 0,
        "modified": 0,
        "removed": int(mode == "unsynced"),
        "renamed": 0,
    }
    warnings = archive.get("warnings", [])
    assert bool(warnings) is (mode == "early-synced")
    if warnings:
        assert all("already removed" in warning for warning in warnings)


def test_governance_observes_archive_effect_separately_from_generation_scope(monkeypatch, tmp_path):
    root, _candidate = fixture.start_adopted_candidate(tmp_path)
    archive_scope = {
        "verdict": "pass",
        "state": "post_archive_closeout",
        "changes": [{"name": "archived", "path": "openspec/changes/archive/archived"}],
        "required_gaps": [],
    }

    def observe_archive(_root, **kwargs):
        assert kwargs["changed_paths"] == ()
        assert kwargs["requested_change"] == "archived"
        return archive_scope

    monkeypatch.setattr(governance, "lease_bound_archive_scope_report", observe_archive)

    report = governance.openspec_governance_report(
        root,
        change="archived",
        lifecycle=True,
        changed_paths=("src/current-generation.py",),
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "archived"
    assert report["lifecycle"]["scope_binding"] == archive_scope


@pytest.mark.parametrize("missing_source", [False, True])
@pytest.mark.parametrize("spec_free", [False, True])
def test_governance_keeps_completed_unarchived_change_as_current_intent(
    monkeypatch, tmp_path, missing_source, spec_free
):
    """Current completed intent needs every document selected by the official reader."""
    root = _repo(tmp_path)
    fixture.git(root, "checkout", "-b", "work/complete")
    fixture.write_active_commitment(root, change_id="complete")
    tasks = root / "openspec/changes/complete/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    if spec_free:
        shutil.rmtree(tasks.parent / "specs")
        (tasks.parent / ".openspec.yaml").write_text("schema: spec-driven\nskip_specs: true\n")
    original = cli.run_json_batch
    verified, calls = Mock(wraps=cli.openspec_base_command), []
    monkeypatch.setattr(cli, "openspec_base_command", verified)

    def observe(repo, command, requested):
        calls.extend(requested)
        results = original(repo, command, requested)
        for args, result in zip(requested, results, strict=True):
            if missing_source and args[:2] == ("instructions", "apply"):
                result["json"]["contextFiles"]["proposal"] = [str(root / "missing-proposal.md")]
        return results

    monkeypatch.setattr(cli, "run_json_batch", observe)
    report = governance.openspec_governance_report(root, lifecycle=True)
    verified.assert_called_once()
    assert calls.count(("status", "--change", "complete", "--json")) == 1
    assert report["verdict"] == ("block" if missing_source else "pass")
    assert bool(report["required_gaps"]) is missing_source
    assert report["intent_context"]["source_state"] == (
        "incomplete" if missing_source else "complete"
    )
    assert report["change"] == "complete"
    assert report["commitment"]["id"] == "change:complete"
    assert report["lifecycle"]["changes"][0]["progress"]["remaining"] == 0


def test_governance_reports_invalid_commitment_and_artifact_paths(monkeypatch, tmp_path):
    root = fixture.prepared_work_lane(tmp_path).worktree
    monkeypatch.setattr(
        governance,
        "load_openspec_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid")),
    )
    report = governance.openspec_governance_report(root, lifecycle=True)

    assert "commitment_invalid:fixture-change" in report["required_gaps"]
    outside = tmp_path / "outside.md"
    status = {
        "artifactPaths": {
            "ignored": "not-a-mapping",
            "mixed": {
                "existingOutputPaths": [
                    root / "openspec/changes/active/specs/capability/spec.md",
                    outside,
                ]
            },
        }
    }
    assert governance.artifact_output_paths(root, {}) == ()
    assert governance.artifact_output_paths(root, status) == (
        "openspec/changes/active/specs/capability/spec.md",
    )


def _select_native_task_fixture(root: Path, command: tuple[str, ...], mode: str) -> Path:
    change = root / "openspec/changes/fixture-change"
    task = change / "tasks.md"
    schema_dir = root / "openspec/schemas/fixture-schema"
    shutil.copytree(Path(command[1]).resolve().parent.parent / "schemas/spec-driven", schema_dir)
    schema = yaml.safe_load((schema_dir / "schema.yaml").read_text())
    schema["name"] = "fixture-schema"
    if mode == "no-tracking":
        schema["apply"]["tracks"] = None
    else:
        artifact = next(row for row in schema["artifacts"] if row["id"] == "tasks")
        artifact.update(id="work-items", generates="work/*.md")
        schema["apply"].update(
            requires=["proposal" if mode == "independent-prerequisite" else "work-items"],
            tracks="work/*.md",
        )
        task.unlink()
        task = change / "work/one.md"
        task.parent.mkdir()
    (schema_dir / "schema.yaml").write_text(yaml.safe_dump(schema, sort_keys=False))
    (change / ".openspec.yaml").write_text("schema: fixture-schema\n")
    return task


@pytest.mark.parametrize(
    "mode",
    [
        "pending",
        "done",
        "empty",
        "blank-description",
        "nested-pending",
        "nested-empty",
        "independent-prerequisite",
        "no-tracking",
    ],
)
def test_governance_obeys_native_apply_readiness_for_selected_task_artifacts(
    tmp_path: Path, mode: str
) -> None:
    root = fixture.prepared_work_lane(tmp_path).worktree
    command = cli.openspec_base_command(execution_probe=False)
    assert command is not None
    change = root / "openspec/changes/fixture-change"
    task = change / "tasks.md"
    renamed = mode.startswith("nested-") or mode == "independent-prerequisite"
    if renamed or mode == "no-tracking":
        task = _select_native_task_fixture(root, command, mode)
    blocked = mode in {"empty", "blank-description", "nested-empty", "independent-prerequisite"}
    content = "- [ ]\n" if mode == "blank-description" else "No executable checklist.\n"
    if not blocked and mode != "no-tracking":
        marker = "x" if mode == "done" else " "
        content = f"- [{marker}] 1.1 Exercise the fixture and verify its report.\n"
    task.write_text("# Tasks\n\n## 1. Fixture\n\n" + content)
    fixture.commit_fixture(root, "test: preserve selected task evidence")
    report = governance.openspec_governance_report(root, change="fixture-change", lifecycle=True)
    status = report["commands"]["status"]["json"]
    apply = report["commands"]["apply"]["json"]
    assert status["isComplete"] is True
    assert apply["taskTrackingConfigured"] is (mode != "no-tracking")
    assert apply["state"] == ("blocked" if blocked else "all_done" if mode == "done" else "ready")
    role = "work-items" if renamed else "tasks"
    if mode == "independent-prerequisite":
        assert status["applyRequires"] == ["proposal"]
    assert status["artifactPaths"][role]["existingOutputPaths"] == [str(task)]
    assert apply["contextFiles"][role] == [str(task)]
    gap = "openspec_apply_blocked:fixture-change"
    assert report["verdict"] == ("block" if blocked else "pass"), report["required_gaps"]
    assert (gap in report["required_gaps"]) is blocked
    plan = run_ethos("plan", "--change", "fixture-change", "--json", cwd=root)
    assert plan["verdict"] == ("block" if blocked else "pass"), plan["required_gaps"]
    assert (gap in plan["required_gaps"]) is blocked
    if blocked:
        proof = run_ethos_raw("prove", "--change", "fixture-change", "--json", cwd=root)
        assert proof.returncode == 1
        assert gap in json.loads(proof.stdout)["required_gaps"], proof.stdout
        args = ("--editor-root", str(root), "--require-editor-root", "--json")
        for forbidden in ("README.md", "openspec/changes/fixture-change/proposal.md"):
            denied = run_ethos_raw("lane", "prewrite", "--paths", forbidden, *args, cwd=root)
            assert denied.returncode == 1, denied.stdout
        repair = run_ethos(
            "lane", "prewrite", "--paths", task.relative_to(root).as_posix(), *args, cwd=root
        )
        assert repair["verdict"] == "pass", repair
        scope = repair["data"]["material_scope"]
        assert scope["authorized_paths"] == [task.relative_to(root).as_posix()]
        assert (
            repair["next_action"] == f"openspec instructions {role} --change fixture-change --json"
        )


def test_task_repair_requires_the_matching_native_tracking_binding(tmp_path: Path) -> None:
    root = fixture.prepared_work_lane(tmp_path).worktree
    path = "openspec/changes/fixture-change/tasks.md"
    (root / path).write_text("# Tasks\n\nNo executable checklist.\n", encoding="utf-8")
    official = governance.openspec_governance_report(root, change="fixture-change", lifecycle=True)
    status = official["commands"]["status"]
    binding = status["task_tracking"]
    assert binding["artifactId"] == "tasks"
    assert binding["outputPaths"] == [str(root / path)]
    scope = lifecycle_scope.official_change_bootstrap_scope_report(
        root=root, official=official, requested_paths=(path,)
    )
    assert scope["authorized_paths"] == [path]
    assert scope["verdict"] == "pass"
    for replacement in (None, binding | {"schemaName": "another-selected-schema"}):
        unbound = deepcopy(official)
        status = unbound["commands"]["status"]
        if replacement is None:
            status.pop("task_tracking")
        else:
            status["task_tracking"] = replacement
        refused = lifecycle_scope.official_change_bootstrap_scope_report(
            root=root, official=unbound, requested_paths=(path,)
        )
        assert refused.get("authorized_paths", []) == []
