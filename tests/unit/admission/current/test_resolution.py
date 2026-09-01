from pathlib import Path

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.semantic import Commitment
from tests.support.semantic import commitment_fixture


def _authority(*, verdict: str = "pass", reason: str = "matched") -> CurrentAuthority:
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
        current_head="a" * 40,
        current_tree="b" * 40,
    )


def test_current_resolution_preserves_the_first_authority_gap() -> None:
    root = Path("/repository")
    resolution = resolve_current_resolution(
        root,
        status={"role": "work_lane", "head": "a" * 40},
        authority=_authority(
            verdict="block",
            reason="invocation_actor_missing:work/example",
        ),
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
    monkeypatch.setattr(
        "ethos.adapters.admission.current.resolution.load_profile_commitment",
        lambda *_args, **_kwargs: commitment,
    )
    monkeypatch.setattr(
        "ethos.adapters.admission.current.resolution.change_scope_paths_from_status",
        lambda *_args, **_kwargs: ("src/example.py",),
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40},
        authority=_authority(),
    )

    assert isinstance(resolution, CurrentResolution)
    assert resolution.verdict == "pass"
    assert resolution.commitment == commitment
    assert resolution.scope.paths == ("src/example.py",)
    assert resolution.required_gaps == ()
    assert resolution.next_action == ""


def test_current_resolution_preserves_unknown_official_intent_without_reinterpreting(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "unknown",
            "required_gaps": ["carrier_unreadable"],
            "lifecycle": {"scope_binding": {}},
        },
        raising=False,
    )
    monkeypatch.setattr(
        resolution_adapter,
        "load_profile_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unknown official intent must stop resolution")
        ),
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "accepted_root", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
    )

    assert resolution.verdict == "unknown"
    assert resolution.commitment is None
    assert resolution.required_gaps == ("carrier_unreadable",)


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
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "change": change,
            "official_cli": {"available": True},
            "required_gaps": [f"openspec_status_incomplete:{change}"],
            "lifecycle": {
                "scope_binding": {
                    "verdict": "pass",
                    "state": "no_material_paths",
                    "required_gaps": [],
                },
                "changes": [
                    {
                        "name": change,
                        "path": f"openspec/changes/{change}",
                        "artifacts": [
                            {
                                "id": "proposal",
                                "outputPath": "proposal.md",
                                "status": "ready",
                                "requires": [],
                            },
                            {
                                "id": "specs",
                                "outputPath": "specs/**/*.md",
                                "status": "blocked",
                                "requires": ["proposal"],
                            },
                            {
                                "id": "design",
                                "outputPath": "design.md",
                                "status": "blocked",
                                "requires": ["proposal"],
                            },
                            {
                                "id": "tasks",
                                "outputPath": "tasks.md",
                                "status": "blocked",
                                "requires": ["specs", "design"],
                            },
                        ],
                    }
                ],
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {
                        "changes": [
                            {
                                "name": change,
                                "completedTasks": 0,
                                "totalTasks": 1,
                                "status": "in-progress",
                            }
                        ]
                    },
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=(path,),
    )

    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "official_change_bootstrap"
    assert resolution.next_action == f"openspec instructions proposal --change {change} --json"


def test_current_resolution_admits_only_one_new_official_metadata_path(monkeypatch) -> None:
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "official_cli": {"available": True},
            "required_gaps": ["openspec_active_change_missing"],
            "lifecycle": {"scope_binding": {}, "changes": []},
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {"changes": []},
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=("openspec/changes/example/.openspec.yaml",),
    )

    assert resolution.verdict == "pass"
    assert resolution.next_action == "openspec new change example --json"


def test_current_resolution_admits_remaining_official_artifact_after_partial_compilation(
    monkeypatch,
) -> None:
    change = "example"
    tasks = f"openspec/changes/{change}/tasks.md"
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "official_cli": {"available": True},
            "required_gaps": [
                f"openspec_status_incomplete:{change}",
                f"openspec_artifact_incomplete:{change}:tasks",
            ],
            "commitment": {"schema_version": 1, "id": change, "acceptance": []},
            "lifecycle": {
                "changes": [
                    {
                        "name": change,
                        "artifacts": [
                            {
                                "id": "proposal",
                                "outputPath": "proposal.md",
                                "status": "done",
                                "requires": [],
                            },
                            {
                                "id": "tasks",
                                "outputPath": "tasks.md",
                                "status": "ready",
                                "requires": ["proposal"],
                            },
                        ],
                    }
                ],
                "scope_binding": {},
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {"changes": [{"name": change}]},
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=(tasks,),
    )

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
            (
                "openspec/specs/distribution/spec.md",
                "src/ethos/product.py",
            ),
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
    change = "repair-spec"
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "change": change,
            "official_cli": {"available": True},
            "required_gaps": ["openspec_validation_failed:spec:distribution"],
            "commitment": commitment_fixture(id=f"change:{change}").model_dump(mode="json"),
            "lifecycle": {
                "scope_binding": {
                    "verdict": "pass",
                    "state": "no_material_paths",
                    "required_gaps": [],
                },
                "changes": [
                    {
                        "name": change,
                        "artifacts": [
                            {
                                "id": "tasks",
                                "outputPath": "tasks.md",
                                "status": "done",
                                "requires": [],
                            }
                        ],
                    }
                ],
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {"changes": [{"name": change}]},
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=paths,
    )

    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "canonical_spec_repair"
    assert resolution.scope.material_scope["uncovered_paths"] == uncovered
    assert resolution.next_action == "openspec validate --all --strict --json"


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
    change = "repair-spec"
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "change": change,
            "official_cli": {"available": True},
            "required_gaps": [gap],
            "commitment": commitment_fixture(id=f"change:{change}").model_dump(mode="json"),
            "lifecycle": {
                "scope_binding": {},
                "changes": [
                    {
                        "name": change,
                        "artifacts": [
                            {
                                "id": "tasks",
                                "outputPath": "tasks.md",
                                "status": "done",
                                "requires": [],
                            }
                        ],
                    }
                ],
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {"changes": [{"name": change}]},
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=("openspec/specs/distribution/spec.md",),
    )

    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "canonical_spec_repair"
    assert resolution.required_gaps == (gap,)


@pytest.mark.parametrize(
    "official_override",
    [
        {"commitment": {}},
        {"lifecycle": {"scope_binding": {}, "changes": []}},
        {
            "required_gaps": [
                "openspec_validation_failed:spec:distribution",
                "commitment_invalid:repair-spec",
            ]
        },
    ],
)
def test_current_resolution_requires_valid_change_contract_for_canonical_repair(
    monkeypatch,
    official_override: dict[str, object],
) -> None:
    change = "repair-spec"
    official: dict[str, object] = {
        "verdict": "block",
        "change": change,
        "official_cli": {"available": True},
        "required_gaps": ["openspec_validation_failed:spec:distribution"],
        "commitment": commitment_fixture(id=f"change:{change}").model_dump(mode="json"),
        "lifecycle": {
            "scope_binding": {},
            "changes": [
                {
                    "name": change,
                    "artifacts": [
                        {
                            "id": "tasks",
                            "outputPath": "tasks.md",
                            "status": "done",
                            "requires": [],
                        }
                    ],
                    "required_gaps": [],
                }
            ],
        },
        "commands": {
            "list": {
                "exit_code": 0,
                "parse_error": "",
                "json": {"changes": [{"name": change}]},
            }
        },
    }
    official.update(official_override)
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: official,
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=("openspec/specs/distribution/spec.md",),
    )

    assert resolution.verdict == "block"
    assert resolution.scope.material_scope.get("state") != "canonical_spec_repair"


@pytest.mark.parametrize(
    "paths",
    [
        (
            "openspec/changes/example/.openspec.yaml",
            "openspec/changes/example/proposal.md",
        ),
        ("openspec/changes/Invalid/.openspec.yaml",),
        ("openspec/changes/archive/.openspec.yaml",),
    ],
)
def test_current_resolution_rejects_ambiguous_or_invalid_new_change_bootstrap(
    monkeypatch,
    paths: tuple[str, ...],
) -> None:
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "official_cli": {"available": True},
            "required_gaps": ["openspec_active_change_missing"],
            "lifecycle": {"scope_binding": {}, "changes": []},
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {"changes": []},
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=paths,
    )

    assert resolution.verdict == "block"
    assert resolution.required_gaps == ("openspec_active_change_missing",)


def test_current_resolution_keeps_incomplete_official_change_blocked_outside_prewrite(
    monkeypatch,
) -> None:
    change = "example"
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "change": change,
            "official_cli": {"available": True},
            "required_gaps": [f"openspec_status_incomplete:{change}"],
            "lifecycle": {
                "scope_binding": {},
                "changes": [
                    {
                        "name": change,
                        "artifacts": [
                            {
                                "id": "proposal",
                                "outputPath": "proposal.md",
                                "status": "ready",
                                "requires": [],
                            }
                        ],
                    }
                ],
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {
                        "changes": [
                            {
                                "name": change,
                                "completedTasks": 0,
                                "totalTasks": 1,
                                "status": "in-progress",
                            }
                        ]
                    },
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
    )

    assert resolution.verdict == "block"
    assert resolution.commitment is None
    assert resolution.required_gaps == (f"openspec_status_incomplete:{change}",)
    assert resolution.next_action == (f"openspec instructions proposal --change {change} --json")


def test_current_resolution_does_not_bootstrap_completed_invalid_commitment(monkeypatch) -> None:
    change = "example"
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "change": change,
            "official_cli": {"available": True},
            "required_gaps": [f"commitment_invalid:{change}"],
            "lifecycle": {
                "scope_binding": {},
                "changes": [
                    {
                        "name": change,
                        "artifacts": [
                            {
                                "id": "proposal",
                                "outputPath": "proposal.md",
                                "status": "done",
                                "requires": [],
                            }
                        ],
                    }
                ],
            },
            "commands": {
                "list": {
                    "exit_code": 0,
                    "parse_error": "",
                    "json": {
                        "changes": [
                            {
                                "name": change,
                                "completedTasks": 1,
                                "totalTasks": 1,
                                "status": "complete",
                            }
                        ]
                    },
                }
            },
        },
    )

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": "work_lane", "head": "a" * 40, "changed_paths": []},
        authority=_authority(),
        changed=False,
        prewrite_paths=(f"openspec/changes/{change}/proposal.md",),
    )

    assert resolution.verdict == "block"
    assert resolution.required_gaps == (f"commitment_invalid:{change}",)
