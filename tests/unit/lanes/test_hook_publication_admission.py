from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.core import push_admission_report
from ethos.surface.cli.hook import core as hook_cli
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_push_admission_keeps_campaign_progress_out_of_required_gaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    campaign_publication = {
        "remote_publication_admission": "blocked",
        "required_gaps": ["campaign_publication_campaign_active:compression"],
    }
    protected = push_admission_report(
        root=repo,
        target_ref="refs/heads/dev",
        pushed_head=head,
        campaign_publication=campaign_publication,
    )
    lane = push_admission_report(
        root=repo,
        target_ref="refs/heads/work/compression",
        pushed_head=head,
    )

    assert protected["ok"] is False
    assert protected["decision"]["reason"] == "push_to_protected_role_not_proven"
    assert "campaign_publication_campaign_active:compression" not in protected["required_gaps"]
    assert lane["ok"] is True


def test_pre_push_forwards_named_remote_to_both_admission_evaluations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    emitted: list[object] = []
    monkeypatch.setattr(hook_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_cli, "emit", lambda result, **_kwargs: emitted.append(result))
    monkeypatch.setattr(
        hook_cli,
        "push_admission_report",
        lambda **kwargs: (
            calls.append(kwargs)
            or {
                "ok": True,
                "state": "admitted",
                "target_branch": "dev",
                "role": "accepted_root",
                "remote_name": kwargs["remote_name"],
                "decision": {"action": "allow", "reason": "push_admitted"},
                "required_gaps": [],
            }
        ),
    )
    monkeypatch.setattr(
        hook_cli,
        "campaign_publication_report",
        lambda _repo: {
            "remote_publication_admission": "admitted",
            "next_action_id": "protected_publication",
            "required_gaps": [],
            "advisory_gaps": ["campaign_publication_campaign_active:compression"],
        },
    )

    hook_cli.pre_push("refs/heads/dev", "head", remote="github", json_output=True)

    assert [call["remote_name"] for call in calls] == ["github", "github"]
    assert emitted[-1].summary["remote"] == "github"
