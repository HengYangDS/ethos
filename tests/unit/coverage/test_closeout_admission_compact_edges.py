from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.core as adm
import ethos.adapters.admission.prewrite as pw
import ethos.adapters.admission.shell as shell
import ethos.adapters.admission.transitions as tx
import ethos.adapters.gates.runner as gates
import ethos.domain.land.intake.core as intake
import ethos.domain.land.trust.core as trust
import ethos.surface.cli._base as cli
import ethos.surface.cli.root.lifecycle as life
import ethos_core.contracts.lifecycle.core as lifecycle
from ethos_core.contracts.admission import HookAdmissionRequest
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.coordination import LaneLease
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


def _patch(monkeypatch: pytest.MonkeyPatch, target: object, **values: object) -> None:
    for name, value in values.items():
        monkeypatch.setattr(target, name, value)


def test_lease_shell_and_git_parser_matrix() -> None:
    facts = lifecycle.LeaseFacts(role="work_lane", current_branch="work/x", current_head="a", branch="work/x", expect_head="b", lease_id="l", epoch=1, ttl_seconds=1, offer_id="", apply=False)  # fmt: skip
    assert lifecycle.reduce_lease_request(lifecycle.lease_transition("renew"), facts).gaps == ("expect_head_mismatch",)  # fmt: skip
    cases = json.loads('[ ["","work_lane",false], ["git stash list","accepted_root",false], ["git branch --list","accepted_root",false], ["git worktree list","accepted_root",false], ["ethos status --json","accepted_root",false], ["git branch -D old","work_lane",true], ["python script.py","accepted_root",true] ]')  # fmt: skip
    assert [shell.command_risk(command, role=role)["tracked_mutation_risk"] for command, role, _ in cases] == [expected for _, _, expected in cases]  # fmt: skip
    tokens, find, mutates, protected, readonly = shell._shell_tokens, shell._find_git_subcommand, shell._has_explicit_mutation_command, shell._is_protected_read_command, shell._git_command_is_read_only  # noqa: SLF001, RUF100 - parser edges  # fmt: skip
    assert tokens("git '") == ["git", "'"]
    assert [find(args, start=1) for args in (["git", "-C", "/r", "status"], ["git", "--git-dir=/r", "status"], ["git", "--bare"])] == [3, 2, None]  # fmt: skip
    assert [mutates(args) for args in (["git", "--bare"], ["git", "status", "git", "add"])] == [False, True]  # fmt: skip
    assert [protected(args) for args in ([], ["cat"])] == [True, True]
    assert [readonly(args) for args in (["git", "--bare"], ["git", "worktree", "list"], ["git", "status"])] == [False, True, True]  # fmt: skip
    assert shell._git_branch_is_read_only(["main"]) is False  # noqa: SLF001, RUF100 - branch edge
    assert shell._first_non_option(["-a"]) is None  # noqa: SLF001, RUF100 - option edge
    assert [shell.git_stash_policy(command)["operation"] for command in ("git stash '", "git stash list", "git stash")] == ["'", "list", "push"]  # fmt: skip


@pytest.mark.parametrize("content", ["bad = [", 'provider = ""'])
def test_intake_invalid_config(tmp_path: Path, content: str) -> None:
    config = tmp_path / ".ethos/intake.toml"
    config.parent.mkdir()
    config.write_text(content, encoding="utf-8")
    assert intake.intake_projection_report(tmp_path)["state"] == "invalid"


def test_admission_and_prewrite_fail_closed_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    claims = tmp_path / "evidence/claims"
    claims.mkdir(parents=True)
    for index, body in enumerate(("bad = [", 'id = "plain"', '[evidence]\nhead = ""')):
        (claims / f"{index}.toml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(intake, "_git_head", lambda _root: "head")
    assert intake.intake_mine_report(tmp_path)["state"] == "clean"
    workspace = {"role": "work_lane", "branch": "work/x", "closeout_support": {"supported": True, "claim_binding": "missing"}}  # fmt: skip
    claim_report = {"ok": False, "required_gaps": ["claim_invalid"], "claims": {}}
    assert "work_lane_claim_binding_missing:work/x" in trust.trust_closeout_package(workspace=workspace, claims=claim_report)["required_gaps"]  # fmt: skip
    bound_workspace = {"role": "work_lane", "branch": "work/x", "closeout_support": {"supported": True, "claim_binding": "bound"}}  # fmt: skip
    assert "work_lane_claim_binding_missing:work/x" not in trust.trust_closeout_package(workspace=bound_workspace, claims=claim_report)["required_gaps"]  # fmt: skip
    _patch(monkeypatch, adm, workspace_status=lambda *_args, **_kwargs: {"role": "work_lane", "branch": "work/x", "changed_paths": []})  # fmt: skip

    def request(layer: str, **values: object) -> dict[str, object]:
        return adm.hook_admission_report(HookAdmissionRequest(root=tmp_path, layer=layer, **values))

    assert [request("pre-run", command="git stash push")["required_gaps"], request("pre-run", command="git status")["decision"]["reason"], request("git")["state"]] == [["git_stash_forbidden"], "command_observe_only", "fallback"]  # fmt: skip
    monkeypatch.setattr(adm, "_prewrite_report", lambda base, **_kwargs: base | {"prewrite": True})
    assert request("pre-run", command="git add x", paths=(str(tmp_path / "x"),))["prewrite"] is True
    assert adm.ref_move_admission_report(root=tmp_path, ref_name="refs/heads/dev", old_value="a", new_value="0" * 40)["ok"] is True  # fmt: skip
    post, relative = adm._post_write_report, adm._relative  # noqa: SLF001, RUF100 - admission edges
    outside = tmp_path.parent / "x"
    assert (post({}, tmp_path, [tmp_path / "x"])["decision"]["reason"], relative(tmp_path, outside)) == ("post_write_expected_paths_clean", outside.as_posix())  # fmt: skip
    monkeypatch.setattr(pw, "git_stdout", lambda *_args: "")
    status, editor, check = pw._prewrite_status, pw._editor_root_check, pw._check_path  # noqa: SLF001, RUF100 - prewrite edges  # fmt: skip
    assert (status(tmp_path)["branch"], editor(root=tmp_path, editor_root=tmp_path / "x", require_editor_root=True)["reason"], check(root=tmp_path, path=outside, role="work_lane")["reason"]) == ("untracked", "editor_root_mismatch", "path_outside_worktree")  # fmt: skip


def test_cli_contract_and_transition_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    gap_tuple, first, integer = life._gap_tuple, life._first_string, life._int_value  # noqa: SLF001, RUF100 - coercion edges  # fmt: skip
    assert (gates.classify_action_result(exit_code=1, stdout=""), gap_tuple({"required_gaps": ["x"]}), first(["x"]), [integer(value, default=7) for value in (2, "3", "x", None)]) == (("failed", ()), ("x",), "x", [2, 3, 7, 7])  # fmt: skip
    target = tmp_path / "x"
    target.write_bytes(b"x")
    assert cli.sha256_file(target) == "sha256:2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"  # fmt: skip
    cli.emit(EthosResult(command="x", ok=True, state="ok", next_actions=("go",)), json_output=False)
    assert capsys.readouterr().out == "x: ok\nnext: go\n"
    registered, imported = [], []
    monkeypatch.setattr(cli, "register_declared_group", lambda _app, name: registered.append(name))
    monkeypatch.setattr(cli.importlib, "import_module", imported.append)

    def load(argv: list[str]) -> tuple[list[str], list[str]]:
        cli.load_command_groups(argv)
        result = registered.copy(), imported.copy()
        registered.clear()
        imported.clear()
        return result

    assert load(["fleet"]) == ([], ["ethos.surface.cli.fleet"])
    assert load(["lane"])[1] == ["ethos.surface.cli.lane.core", "ethos.surface.cli.lane.lease", "ethos.surface.cli.lane.resolution"]  # fmt: skip
    assert load(["status"]) == ([], [])
    registered, imported = load([])
    assert registered == ["quality"]
    assert imported == ["ethos.surface.cli.fleet", "ethos.surface.cli.intake", "ethos.surface.cli.rules", "ethos.surface.cli.lane.core", "ethos.surface.cli.lane.lease", "ethos.surface.cli.lane.resolution", "ethos.surface.cli.assistants", "ethos.surface.cli.campaign", "ethos.surface.cli.parity.core", "ethos.surface.cli.playbooks", "ethos.surface.cli.hook.core"]  # fmt: skip
    now = datetime(2026, 1, 1, tzinfo=UTC)
    base = {"lane_incarnation_id": "i", "lease_id": "l", "lane_ref": "work/x", "holder_ref": HolderRef.parse("agent:test:thread:x"), "epoch": 1}  # fmt: skip
    for renewed, expires, message in ((now - timedelta(1), now, "renewed_at"), (now, now - timedelta(1), "expires_at")):  # fmt: skip
        with pytest.raises(ValueError, match=message):
            LaneLease(**base, issued_at=now, renewed_at=renewed, expires_at=expires)
    gaps = tx._work_lane_lease_transition_gaps  # noqa: SLF001, RUF100 - lease edge
    assert gaps("work/x", {}, "a", "h") == ["work_lane_missing_lease:work/x"]
    data = {"holder_ref": "a", "lease_id": "l", "epoch": 1, "expected_head": "h"}
    monkeypatch.setenv("ETHOS_ACTOR", "a")
    _patch(monkeypatch, tx, load_branch_role_policy=lambda _root: object(), worktree_records=lambda *_args, **_kwargs: [], leases_by_branch=lambda *_args, **_kwargs: {"work/x": data})  # fmt: skip

    def stale(*_args: object, **_kwargs: object) -> object:
        raise ValueError("stale")  # noqa: EM101, RUF100 - injected lease transition failure

    monkeypatch.setattr(tx, "advance_lease_head", stale)
    report = tx.work_lane_ref_transition_report(root=tmp_path, phase="committed", ref_name="refs/heads/work/x", old_value="h", new_value="n")  # fmt: skip
    assert (report["state"], report["required_gaps"]) == ("repair_required", ["stale"])
