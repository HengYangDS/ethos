from pathlib import Path

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.semantic import Commitment
from ethos.contracts.verdict import Verdict
from tests.support.semantic import commitment_fixture

ROOT = Path("/repository")
HEAD = "a" * 40
ACTIVE_SPEC = "openspec/changes/repair-change/specs/repository-governance/spec.md"
ABSENT = object()


def _authority(*, verdict: Verdict = "pass", reason: str = "matched") -> CurrentAuthority:
    return CurrentAuthority(
        verdict=verdict,
        reason=reason,
        branch="work/example",
        actor="agent:test" if verdict == "pass" else "",
        lease={
            "lease_state": "valid",
            "holder_ref": "agent:test",
            "generation": 3,
            "expires_at": "2099-01-01T00:00:00Z",
        },
        current_head=HEAD,
        current_tree="b" * 40,
    )


def _receipt(payload: object, *, exit_code: int = 0) -> dict[str, object]:
    return {"exit_code": exit_code, "parse_error": "", "json": payload}


def _artifact(
    identifier: str,
    output: str,
    *,
    status: str = "done",
    requires: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "id": identifier,
        "outputPath": output,
        "status": status,
        "requires": list(requires),
    }


def _official_report(
    *,
    change: str | None = None,
    gaps: tuple[str, ...] = (),
    artifacts: tuple[dict[str, object], ...] = (),
    commitment: object = ABSENT,
    change_path: str | None = None,
    scope_binding: dict[str, object] | None = None,
    status_payload: dict[str, object] | None = None,
    validate_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    selected = []
    if change is not None:
        row: dict[str, object] = {
            "name": change,
            "artifacts": list(artifacts),
            "required_gaps": [],
        }
        if change_path is not None:
            row["path"] = change_path
        selected.append(row)
    commands = {"list": _receipt({"changes": [] if change is None else [{"name": change}]})}
    if status_payload is not None:
        commands["status"] = _receipt(status_payload)
    if validate_payload is not None:
        commands["validate"] = _receipt(validate_payload, exit_code=1)
    report: dict[str, object] = {
        "verdict": "block",
        "official_cli": {"available": True},
        "required_gaps": list(gaps),
        "lifecycle": {"scope_binding": scope_binding or {}, "changes": selected},
        "commands": commands,
    }
    if change is not None:
        report["change"] = change
    if commitment is not ABSENT:
        report["commitment"] = commitment
    return report


def _resolve_report(
    monkeypatch,
    report: dict[str, object],
    *,
    root: Path = ROOT,
    paths: tuple[str, ...] = (),
    role: str = "work_lane",
) -> CurrentResolution:
    monkeypatch.setattr(resolution_adapter, "openspec_governance_report", lambda *_a, **_k: report)
    return resolve_current_resolution(
        root,
        status={"role": role, "head": HEAD, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=paths,
    )


def _active_change_validation_report(
    root: Path,
    *,
    issue_level: str = "ERROR",
    issue_path: object = "repository-governance/spec.md",
    spec_outputs: tuple[str, ...] = ("specs/repository-governance/spec.md",),
    create_outputs: bool = True,
    additional_issues: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    change = "repair-change"
    change_root = root / "openspec" / "changes" / change
    outputs = {
        "proposal": ("proposal.md",),
        "specs": spec_outputs,
        "design": ("design.md",),
        "tasks": ("tasks.md",),
    }
    if create_outputs:
        for relative in (".openspec.yaml", *(path for paths in outputs.values() for path in paths)):
            output = change_root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("official artifact\n", encoding="utf-8")
    return _official_report(
        change=change,
        gaps=(
            f"openspec_validation_failed:change:{change}",
            f"commitment_invalid:{change}",
        ),
        artifacts=tuple(_artifact(identifier, paths[0]) for identifier, paths in outputs.items()),
        commitment={},
        change_path=change_root.as_posix(),
        status_payload={
            "changeName": change,
            "changeRoot": change_root.as_posix(),
            "artifactPaths": {
                identifier: {
                    "existingOutputPaths": [(change_root / output).as_posix() for output in paths]
                }
                for identifier, paths in outputs.items()
            },
        },
        validate_payload={
            "items": [
                {
                    "id": change,
                    "type": "change",
                    "valid": False,
                    "issues": [
                        {
                            "level": issue_level,
                            "path": issue_path,
                            "message": "structured validator detail",
                        },
                        *additional_issues,
                    ],
                }
            ]
        },
    )


def _canonical_repair_report(
    *, gaps: tuple[str, ...] = ("openspec_validation_failed:spec:distribution",)
) -> dict[str, object]:
    change = "repair-spec"
    return _official_report(
        change=change,
        gaps=gaps,
        artifacts=(_artifact("tasks", "tasks.md"),),
        commitment=commitment_fixture(id=f"change:{change}").model_dump(mode="json"),
    )


def test_current_resolution_preserves_the_first_authority_gap() -> None:
    resolution = resolve_current_resolution(
        ROOT,
        status={"role": "work_lane", "head": HEAD},
        authority=_authority(verdict="block", reason="invocation_actor_missing:work/example"),
    )
    assert resolution.required_gaps == ("invocation_actor_missing:work/example",)
    assert resolution.next_action == "export ETHOS_ACTOR=agent:test"
    assert resolution.user_decision_required is False


def test_current_resolution_owns_acceptance_and_fresh_paths(monkeypatch) -> None:
    commitment = Commitment(
        schema_version=3,
        id="change:example",
        acceptance=("result projection is consistent",),
    )
    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", lambda *_a, **_k: commitment)
    monkeypatch.setattr(
        resolution_adapter,
        "change_scope_paths_from_status",
        lambda *_a, **_k: ("src/example.py",),
    )
    resolution = resolve_current_resolution(
        ROOT, status={"role": "work_lane", "head": HEAD}, authority=_authority()
    )
    assert isinstance(resolution, CurrentResolution)
    assert resolution.verdict == "pass"
    assert resolution.commitment == commitment
    assert resolution.scope.paths == ("src/example.py",)
    assert resolution.required_gaps == ()
    assert resolution.next_action == ""


@pytest.mark.parametrize(
    "gap", ["", "openspec_official_cli_missing", "openspec_acceptance_missing:example"]
)
def test_current_resolution_compiles_committed_source_intent_without_workspace_reread(
    monkeypatch, gap
):
    commitment = commitment_fixture(id="change:example")
    calls: list[tuple[str | None, str | None]] = []
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("committed-source resolution must not read mutable workspace intent")
        ),
    )

    def load(_root: Path, *, change_id: str | None, tree_ref: str | None = None):
        calls.append((change_id, tree_ref))
        if gap:
            raise ValueError(gap)
        return commitment

    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", load)
    resolution = resolve_current_resolution(
        ROOT,
        status={"role": "work_lane", "head": HEAD, "changed_paths": []},
        authority=_authority(),
        change="example",
        changed=False,
        intent_tree_ref=HEAD,
    )
    assert calls == [("example", HEAD)]
    if gap:
        assert resolution.verdict == "block"
        assert resolution.commitment is None
        assert resolution.required_gaps == (gap,)
        assert resolution.next_action == (
            "npm ci --ignore-scripts --no-audit --no-fund"
            if gap == "openspec_official_cli_missing"
            else "openspec status --change example --json"
        )
    else:
        assert resolution.verdict == "pass"
        assert resolution.commitment == commitment
        assert resolution.openspec == {
            "verdict": "pass",
            "state": "committed_source",
            "change": "example",
            "source_head": HEAD,
            "required_gaps": [],
        }


def test_current_resolution_preserves_unknown_official_intent_without_reinterpreting(monkeypatch):
    report = _official_report(gaps=("carrier_unreadable",)) | {"verdict": "unknown"}
    monkeypatch.setattr(
        resolution_adapter,
        "load_profile_commitment",
        lambda *_a, **_k: pytest.fail("unknown official intent must stop resolution"),
    )
    resolution = _resolve_report(monkeypatch, report, role=ROLE_ACCEPTED_ROOT)
    assert resolution.verdict == "unknown"
    assert resolution.commitment is None
    assert resolution.required_gaps == ("carrier_unreadable",)


@pytest.mark.parametrize("role", [ROLE_CANDIDATE, ROLE_ACCEPTED_ROOT])
@pytest.mark.parametrize(
    ("official_verdict", "official_gaps"),
    [
        ("pass", []),
        ("block", ["openspec_active_change_missing"]),
    ],
)
def test_current_resolution_admits_entity_free_repository_proof(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    official_verdict: str,
    official_gaps: list[str],
) -> None:
    head = "a" * 40
    authority = CurrentAuthority(
        verdict="pass",
        reason="not_required",
        branch="candidate/dev" if role == ROLE_CANDIDATE else "dev",
        actor="agent:test",
        lease={},
        current_head=head,
        current_tree="b" * 40,
        required=False,
    )
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": official_verdict,
            "required_gaps": official_gaps,
            "commitment": {},
            "lifecycle": {"scope_binding": {}, "changes": []},
        },
    )
    monkeypatch.setattr(
        resolution_adapter,
        "attested_archive_transition",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        resolution_adapter,
        "load_profile_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("entity-free repository proof must not invent intent")
        ),
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": role, "head": head, "changed_paths": []},
        authority=authority,
        changed=False,
    )

    assert resolution.verdict == "pass"
    assert resolution.authority is authority
    assert resolution.commitment is None
    assert resolution.scope.paths == ()
    assert resolution.openspec == {
        "verdict": "pass",
        "state": "not_applicable",
        "required_gaps": [],
    }


@pytest.mark.parametrize(
    ("path", "verdict"),
    [
        ("openspec/changes/example/.openspec.yaml", "pass"),
        ("openspec/changes/example/proposal.md", "pass"),
        ("openspec/changes/example/specs/capability/spec.md", "pass"),
        ("openspec/changes/example/design.md", "pass"),
        ("openspec/changes/example/tasks.md", "pass"),
        ("openspec/changes/example/README.md", "block"),
        ("openspec/changes/other/proposal.md", "block"),
        ("openspec/changes/archive/2026-08-30-example/tasks.md", "block"),
        ("src/product.py", "block"),
    ],
)
def test_current_resolution_projects_only_incomplete_official_change_artifacts_for_prewrite(
    monkeypatch,
    path: str,
    verdict: str,
) -> None:
    change = "example"
    artifacts = (
        _artifact("proposal", "proposal.md", status="ready"),
        _artifact("specs", "specs/**/*.md", status="blocked", requires=("proposal",)),
        _artifact("design", "design.md", status="blocked", requires=("proposal",)),
        _artifact("tasks", "tasks.md", status="blocked", requires=("specs", "design")),
    )
    resolution = _resolve_report(
        monkeypatch,
        _official_report(
            change=change,
            gaps=(f"openspec_status_incomplete:{change}",),
            artifacts=artifacts,
            change_path=f"openspec/changes/{change}",
            scope_binding={"verdict": "pass", "state": "no_material_paths"},
        ),
        paths=(path,),
    )
    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "official_change_bootstrap"
    assert resolution.next_action == f"openspec instructions proposal --change {change} --json"


@pytest.mark.parametrize("target", ["metadata", "absent-root", "existing-root"])
def test_current_resolution_derives_only_exact_new_change_metadata(tmp_path, monkeypatch, target):
    change = "openspec/changes/example"
    if target == "existing-root":
        (tmp_path / change).mkdir(parents=True)
    resolution = _resolve_report(
        monkeypatch,
        _official_report(gaps=("openspec_active_change_missing",)),
        root=tmp_path,
        paths=(f"{change}/.openspec.yaml" if target == "metadata" else change,),
    )
    assert resolution.verdict == ("pass" if target == "metadata" else "block")
    if target == "metadata":
        assert resolution.scope.material_scope["authorized_paths"] == [f"{change}/.openspec.yaml"]
        assert resolution.next_action == "openspec new change example --json"
    elif target == "absent-root":
        assert resolution.scope.material_scope["state"] == "official_change_bootstrap_intent"
        assert resolution.required_gaps == ("openspec_change_metadata_prewrite_required:example",)
        assert resolution.next_action == (
            f"ethos lane prewrite --paths {change}/.openspec.yaml "
            f"--editor-root {tmp_path} --require-editor-root --root {tmp_path} --json"
        )
    else:
        assert resolution.required_gaps == ("openspec_active_change_missing",)
        assert not resolution.scope.material_scope.get("authorized_paths")


def test_current_resolution_admits_remaining_official_artifact_after_partial_compilation(
    monkeypatch,
) -> None:
    change = "example"
    tasks = f"openspec/changes/{change}/tasks.md"
    report = _official_report(
        change=change,
        gaps=(
            f"openspec_status_incomplete:{change}",
            f"openspec_artifact_incomplete:{change}:tasks",
        ),
        artifacts=(
            _artifact("proposal", "proposal.md"),
            _artifact("tasks", "tasks.md", status="ready", requires=("proposal",)),
        ),
        commitment={"schema_version": 1, "id": change, "acceptance": []},
    )
    resolution = _resolve_report(monkeypatch, report, paths=(tasks,))
    assert resolution.verdict == "pass"
    assert resolution.scope.material_scope["state"] == "official_change_bootstrap"
    assert resolution.next_action == f"openspec instructions tasks --change {change} --json"


@pytest.mark.parametrize(
    ("paths", "verdict", "uncovered"),
    [
        (("openspec/specs/distribution/spec.md",), "pass", []),
        (
            ("openspec/specs/product-status-contract/spec.md",),
            "block",
            ["openspec/specs/product-status-contract/spec.md"],
        ),
        (
            ("openspec/specs/distribution/spec.md", "src/ethos/product.py"),
            "block",
            ["src/ethos/product.py"],
        ),
    ],
)
def test_current_resolution_admits_only_validator_named_canonical_spec_repairs(
    monkeypatch,
    paths: tuple[str, ...],
    verdict: str,
    uncovered: list[str],
) -> None:
    resolution = _resolve_report(monkeypatch, _canonical_repair_report(), paths=paths)
    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "canonical_spec_repair"
    assert resolution.scope.material_scope["uncovered_paths"] == uncovered
    assert resolution.next_action == "openspec validate --all --strict --json"


@pytest.mark.parametrize(
    ("issue_level", "issue_path", "requested_path"),
    [
        ("ERROR", "repository-governance/spec.md", ACTIVE_SPEC),
        ("WARNING", "specs/repository-governance/spec.md", ACTIVE_SPEC),
        ("ERROR", ".openspec.yaml", "openspec/changes/repair-change/.openspec.yaml"),
    ],
)
def test_current_resolution_admits_selected_change_strict_validation_repair_without_commitment(
    tmp_path: Path,
    monkeypatch,
    issue_level: str,
    issue_path: str,
    requested_path: str,
) -> None:
    report = _active_change_validation_report(
        tmp_path, issue_level=issue_level, issue_path=issue_path
    )
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=(requested_path,))
    assert resolution.verdict == "pass"
    assert resolution.commitment is None
    assert resolution.required_gaps == ()
    assert resolution.scope.material_scope["state"] == "official_change_validation_repair"
    assert resolution.scope.material_scope["authorized_paths"] == [requested_path]
    assert resolution.next_action == "openspec validate --all --strict --json"


@pytest.mark.parametrize(
    ("coordinate", "value"),
    [
        (("official_cli", "available"), False),
        (("commands",), None),
        (("commands", "list", "parse_error"), "invalid JSON"),
        (("commands", "validate", "json", "items"), None),
        (("commands", "validate", "json", "items", 0, "type"), "spec"),
        (("commands", "validate", "json", "items", 0, "id"), "other-change"),
        (("commands", "validate", "json", "items", 0, "valid"), True),
        (("commands", "validate", "json", "items", 0, "issues"), [None]),
        (("commands", "validate", "json", "items", 0, "issues", 0, "level"), "INFO"),
        (("commands", "validate", "json", "items", 0, "issues", 0, "level"), "UNKNOWN"),
        (("commands", "status", "parse_error"), "invalid JSON"),
        (("commands", "validate", "exit_code"), 0),
        (("lifecycle", "changes"), []),
        (("lifecycle", "changes", 0, "required_gaps"), ["artifact_unavailable"]),
        (("lifecycle", "changes", 0, "artifacts", 0, "status"), "blocked"),
        (("change",), "Invalid"),
        (
            ("required_gaps",),
            ["openspec_validation_failed:change:repair-change", "openspec_doctor_unhealthy"],
        ),
    ],
)
def test_current_resolution_rejects_untrusted_active_change_validation_items(
    tmp_path, monkeypatch, coordinate, value
):
    report = _active_change_validation_report(tmp_path)
    valid = _resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert valid.verdict == "pass"
    assert valid.scope.material_scope["authorized_paths"] == [ACTIVE_SPEC]
    subject = report
    for key in coordinate[:-1]:
        subject = subject[key]
    subject[coordinate[-1]] = value
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")
    assert resolution.required_gaps == tuple(report["required_gaps"])


def test_current_resolution_ignores_info_beside_strict_blocking_change_issue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report = _active_change_validation_report(
        tmp_path,
        additional_issues=({"level": "INFO", "path": "requirements[0]", "message": "guidance"},),
    )
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "pass"
    assert resolution.scope.material_scope["authorized_paths"] == [ACTIVE_SPEC]


@pytest.mark.parametrize(
    "issue_path",
    ["", "/absolute/spec.md", "../tasks.md", "specs/../tasks.md", "missing/spec.md", None],
)
def test_current_resolution_rejects_invalid_active_change_validation_issue_paths(
    tmp_path: Path,
    monkeypatch,
    issue_path: object,
) -> None:
    report = _active_change_validation_report(tmp_path, issue_path=issue_path)
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=(ACTIVE_SPEC,))
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "official_change_validation_repair"


@pytest.mark.parametrize("fault", ["missing", "metadata_link", "output_link", "ambiguous"])
def test_current_resolution_requires_unique_existing_unlinked_official_repair(
    tmp_path, monkeypatch, fault
):
    requested = {
        "metadata_link": "openspec/changes/repair-change/.openspec.yaml",
        "output_link": "openspec/changes/repair-change/shadow.md",
        "ambiguous": "openspec/changes/repair-change/tasks.md",
    }.get(fault, ACTIVE_SPEC)
    issue = {
        "metadata_link": ".openspec.yaml",
        "output_link": "shadow.md",
        "ambiguous": "tasks.md",
    }.get(fault, "repository-governance/spec.md")
    report = _active_change_validation_report(
        tmp_path,
        issue_path=issue,
        create_outputs=fault != "missing",
        spec_outputs=("specs/repository-governance/spec.md", "specs/tasks.md")
        if fault == "ambiguous"
        else ("specs/repository-governance/spec.md",),
    )
    target = None
    if fault in {"metadata_link", "output_link"}:
        declared = tmp_path / (requested if fault == "metadata_link" else ACTIVE_SPEC)
        target = tmp_path / ("outside-metadata.yaml" if fault == "metadata_link" else requested)
        target.write_text("unofficial target\n", encoding="utf-8")
        declared.unlink()
        declared.symlink_to(target)
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=(requested,))
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")
    if target is not None:
        assert target.read_text() == "unofficial target\n"


@pytest.mark.parametrize(
    "requested_paths",
    [
        ("openspec/changes/repair-change/design.md",),
        (ACTIVE_SPEC, "openspec/changes/repair-change/design.md"),
        ("openspec/changes/repair-change/specs",),
    ],
)
def test_current_resolution_blocks_unrelated_or_mixed_validation_repair_paths(
    tmp_path: Path,
    monkeypatch,
    requested_paths: tuple[str, ...],
) -> None:
    report = _active_change_validation_report(tmp_path)
    resolution = _resolve_report(monkeypatch, report, root=tmp_path, paths=requested_paths)
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope["state"] == "official_change_validation_repair"
    assert resolution.scope.material_scope["uncovered_paths"]


@pytest.mark.parametrize(
    "gap",
    [
        "openspec_validation_failed:spec:",
        "openspec_validation_failed:spec:Invalid",
        "openspec_validation_failed:spec:../distribution",
        "openspec_validation_failed:change:distribution",
    ],
)
def test_current_resolution_does_not_derive_canonical_repair_from_invalid_gap(
    monkeypatch,
    gap: str,
) -> None:
    resolution = _resolve_report(
        monkeypatch,
        _canonical_repair_report(gaps=(gap,)),
        paths=("openspec/specs/distribution/spec.md",),
    )
    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "canonical_spec_repair"
    assert resolution.required_gaps == (gap,)


@pytest.mark.parametrize(
    ("coordinate", "value"),
    [
        (("commitment",), {}),
        (("commitment",), None),
        (("commitment", "id"), "change:other"),
        (("lifecycle", "changes"), []),
        (("lifecycle", "changes", 0, "artifacts"), []),
        (
            ("required_gaps",),
            ["openspec_validation_failed:spec:distribution", "commitment_invalid:repair-spec"],
        ),
    ],
)
def test_current_resolution_requires_valid_change_contract_for_canonical_repair(
    monkeypatch, coordinate, value
):
    report = _canonical_repair_report()
    paths = ("openspec/specs/distribution/spec.md",)
    assert _resolve_report(monkeypatch, report, paths=paths).verdict == "pass"
    subject = report
    for key in coordinate[:-1]:
        subject = subject[key]
    subject[coordinate[-1]] = value
    resolution = _resolve_report(monkeypatch, report, paths=paths)
    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")


@pytest.mark.parametrize(
    "paths",
    [
        ("openspec/changes/example/.openspec.yaml", "openspec/changes/example/proposal.md"),
        ("openspec/changes/Invalid/.openspec.yaml",),
        ("openspec/changes/archive/.openspec.yaml",),
        ("other/example/.openspec.yaml",),
    ],
)
def test_current_resolution_rejects_ambiguous_or_invalid_new_change_bootstrap(
    monkeypatch,
    paths: tuple[str, ...],
) -> None:
    resolution = _resolve_report(
        monkeypatch,
        _official_report(gaps=("openspec_active_change_missing",)),
        paths=paths,
    )
    assert resolution.verdict == "block"
    assert resolution.required_gaps == ("openspec_active_change_missing",)


@pytest.mark.parametrize(
    "fault",
    [
        "not-prewrite",
        "complete-invalid",
        "non-object",
        "missing-output",
        "missing-requires",
        "not-ready",
    ],
)
def test_current_resolution_keeps_incomplete_or_invalid_artifact_authority_bounded(
    monkeypatch, fault
):
    report = _official_report(
        change="example",
        gaps=("openspec_status_incomplete:example",),
        artifacts=(_artifact("proposal", "proposal.md", status="ready"),),
    )
    artifact = report["lifecycle"]["changes"][0]["artifacts"][0]
    if fault == "complete-invalid":
        report["required_gaps"] = ["commitment_invalid:example"]
        artifact["status"] = "done"
    elif fault == "non-object":
        report["lifecycle"]["changes"][0]["artifacts"] = [None]
    elif fault in {"missing-output", "missing-requires"}:
        artifact.pop("outputPath" if fault == "missing-output" else "requires")
    elif fault == "not-ready":
        artifact["status"] = "blocked"
    resolution = _resolve_report(
        monkeypatch,
        report,
        paths=()
        if fault in {"not-prewrite", "not-ready"}
        else ("openspec/changes/example/proposal.md",),
    )
    assert resolution.verdict == "block"
    assert resolution.commitment is None
    assert resolution.required_gaps == tuple(report["required_gaps"])
    assert not resolution.scope.material_scope.get("authorized_paths")
    if fault in {"not-prewrite", "not-ready"}:
        expected = "instructions proposal" if fault == "not-prewrite" else "status"
        assert resolution.next_action == f"openspec {expected} --change example --json"
