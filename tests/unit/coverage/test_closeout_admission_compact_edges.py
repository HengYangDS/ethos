from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.core as admission
import ethos.adapters.admission.shell as shell
import ethos.domain.land.intake.core as intake
import ethos.domain.land.trust.core as trust
import ethos_core.contracts.lifecycle.core as lifecycle
from ethos_core.contracts.admission import HookAdmissionRequest

if TYPE_CHECKING:
    from pathlib import Path

_COMMANDS = json.loads(
    '[ ["","work_lane",false], ["git stash list","accepted_root",false], ["git branch --list","accepted_root",false], ["git worktree list","accepted_root",false], ["ethos status --json","accepted_root",false], ["git branch -D old","work_lane",true], ["python script.py","accepted_root",true] ]'
)


def test_lease_shell_and_git_parser_matrix() -> None:
    facts = lifecycle.LeaseFacts(
        role="work_lane",
        current_branch="work/x",
        current_head="a",
        branch="work/x",
        expect_head="b",
        lease_id="lease:x",
        epoch=1,
        ttl_seconds=1,
        offer_id="",
        apply=False,
    )
    decision = lifecycle.reduce_lease_request(lifecycle.lease_transition("renew"), facts)
    assert decision.gaps == ("expect_head_mismatch",)
    actual = [
        shell.command_risk(command, role=role)["tracked_mutation_risk"]
        for command, role, _expected in _COMMANDS
    ]
    assert actual == [expected for _command, _role, expected in _COMMANDS]
    private = vars(shell)
    find = private["_find_git_subcommand"]
    assert private["_shell_tokens"]("git '") == ["git", "'"]
    assert [
        find(args, start=1)
        for args in (
            ["git", "-C", "/repo", "status"],
            ["git", "--git-dir=/repo/.git", "status"],
            ["git", "--bare"],
        )
    ] == [3, 2, None]
    assert shell.git_stash_policy("git stash '")["operation"] == "'"


@pytest.mark.parametrize("content", ["bad = [", 'provider = ""'])
def test_intake_invalid_config(tmp_path: Path, content: str) -> None:
    config = tmp_path / ".ethos/intake.toml"
    config.parent.mkdir()
    config.write_text(content, encoding="utf-8")
    assert intake.intake_projection_report(tmp_path)["state"] == "invalid"


def test_admission_fail_closed_matrix(tmp_path: Path, monkeypatch) -> None:
    claims = tmp_path / "evidence/claims"
    claims.mkdir(parents=True)
    for index, body in enumerate(("bad = [", 'id = "plain"', '[evidence]\nhead = ""')):
        (claims / f"{index}.toml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(intake, "_git_head", lambda _repo: "head")
    assert intake.intake_mine_report(tmp_path)["state"] == "clean"
    blocked = trust.trust_closeout_package(
        workspace={
            "role": "work_lane",
            "branch": "work/x",
            "closeout_support": {"supported": True, "claim_binding": "missing"},
        },
        claims={"ok": False, "required_gaps": ["claim_invalid"], "claims": {}},
    )
    assert "work_lane_claim_binding_missing:work/x" in blocked["required_gaps"]
    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda *_args, **_kwargs: {
            "role": "work_lane",
            "branch": "work/x",
            "changed_paths": [],
        },
    )
    report = admission.hook_admission_report(
        HookAdmissionRequest(root=tmp_path, layer="pre-run", command="git stash push")
    )
    assert report["required_gaps"] == ["git_stash_forbidden"]
