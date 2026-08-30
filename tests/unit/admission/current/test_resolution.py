from pathlib import Path

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.semantic import Commitment


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
