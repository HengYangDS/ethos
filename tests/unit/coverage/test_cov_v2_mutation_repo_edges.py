from __future__ import annotations

import json
import subprocess
from contextlib import nullcontext
from pathlib import Path  # noqa: TC003 coverage closure keeps callback and branch shapes explicit
from types import SimpleNamespace

import pytest

from ethos.adapters.mutation import proof
from ethos.adapters.mutation.lane_lifecycle.handoff import core as hc
from ethos.adapters.mutation.lane_lifecycle.handoff import package as hp
from ethos.adapters.repo import git
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT as ACCEPTED
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE as WORK
from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef


def _patch(m, obj, **values):
    for name, value in values.items():
        m.setattr(obj, name, value)


def _evidence(head: str) -> dict[str, object]:
    body = {"id": "e", "head": head, "durability": "local", "runs": [{"verdict": "passed", "trust_bearing": True, "state": "proven"}]}  # fmt: skip
    body["digest"] = proof._evidence_digest(body)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    return body


def test_proof_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not proof._runs_prove_head([{"verdict": "failed"}])  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    assert not proof._runs_prove_head([{"verdict": "passed", "trust_bearing": True, "state": "executed"}])  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    directory = tmp_path / ".ethos/state/proof"
    directory.mkdir(parents=True)
    (directory / "H.json").write_text(json.dumps({"state": "executed", "head": "H"}), encoding="utf-8")  # fmt: skip
    assert proof.executed_proof_record(tmp_path, "H") is None
    source, head = tmp_path / "src", "a" * 40
    proof.record_executed_proof(source, _evidence(head))
    real_copy = proof.shutil.copyfile
    monkeypatch.setattr(proof.shutil, "copyfile", lambda *args: (_ for _ in ()).throw(OSError("full")))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    copy_failure = proof.carry_executed_proof_record(source_root=source, target_root=tmp_path / "dst", head=head)  # fmt: skip
    assert (copy_failure["ok"], copy_failure["state"], copy_failure["reason"]) == (False, "failed", "OSError")  # fmt: skip
    monkeypatch.setattr(proof.shutil, "copyfile", real_copy)
    real_read, calls = proof.executed_proof_record, iter((True, False))
    monkeypatch.setattr(proof, "executed_proof_record", lambda root, value: real_read(root, value) if next(calls) else None)  # fmt: skip
    verification_failure = proof.carry_executed_proof_record(source_root=source, target_root=tmp_path / "dst2", head=head)  # fmt: skip
    assert (verification_failure["ok"], verification_failure["state"], verification_failure["reason"]) == (False, "failed", "target-proof-invalid-after-copy")  # fmt: skip


def test_git_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_run, real_tracked, real_stdout = subprocess.run, git.current_tracked_head, git.git_stdout
    assert git.git_common_dir(tmp_path) == ""
    assert git.commits_equivalent_over_paths(tmp_path, "", relevant_paths=("p",)) == ()  # fmt: skip
    monkeypatch.setattr(git.subprocess, "run", lambda *args, **kw: SimpleNamespace(returncode=0, stdout="a\n\n"))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    assert git.git_files(tmp_path) == ["a"]
    monkeypatch.setattr(git.subprocess, "run", lambda *args, **kw: SimpleNamespace(returncode=1, stdout=""))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    assert git.git_files(tmp_path) == []
    monkeypatch.setattr(git, "current_tracked_head", lambda root: "local")  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    cases = (("0 0", "synchronized", 0, 0), ("0 1", "local_ahead", 1, 0), ("1 0", "local_behind", 0, 1), ("1 1", "diverged", 1, 1), ("bad", "synchronized", 0, 0))  # fmt: skip
    for counts, state, ahead, behind in cases:
        calls: list[tuple[str, ...]] = []

        def fake_git_stdout(_root: Path, *args: str, value: str = counts) -> str:
            calls.append(args)  # noqa: B023 coverage closure keeps callback and branch shapes explicit  # fmt: skip
            if args == ("rev-parse", "--verify", "origin/dev"):
                return "remote"
            if args == ("rev-list", "--left-right", "--count", "origin/dev...HEAD"):
                return value
            pytest.fail(f"unexpected git argv: {args!r}")

        monkeypatch.setattr(git, "git_stdout", fake_git_stdout)
        report = git.remote_tracking_sync(tmp_path, "dev")
        assert calls == [("rev-parse", "--verify", "origin/dev"), ("rev-list", "--left-right", "--count", "origin/dev...HEAD")]  # fmt: skip
        advisory_gaps = [] if state == "synchronized" else [f"remote_tracking_{state}:origin/dev:{ahead}:{behind}"]  # fmt: skip
        assert report == {"kind": "git_remote_tracking_sync", "remote": "origin", "branch": "dev", "remote_ref": "origin/dev", "local_head": "local", "remote_head": "remote", "ahead": ahead, "behind": behind, "available": True, "blocking": False, "required_gaps": [], "state": state, "advisory_gaps": advisory_gaps}  # fmt: skip
    monkeypatch.setattr(git, "git_stdout", lambda *args: "")  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    assert git.remote_tracking_sync(tmp_path, "dev")["state"] == "remote_tracking_missing"
    assert git.remote_tracking_sync(tmp_path, "")["state"] == "branch_unknown"
    assert git.remote_availability(tmp_path)["state"] == "unconfigured"
    monkeypatch.setattr(git, "git_stdout", lambda *args: "ssh://host/repo")  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setattr(git.subprocess, "run", lambda *args, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 1)))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    assert git.remote_availability(tmp_path)["reason"] == "timeout"
    missing = tmp_path / "missing"
    monkeypatch.setattr(git.subprocess, "run", real_run)
    monkeypatch.setattr(git, "current_tracked_head", real_tracked)
    monkeypatch.setattr(git, "git_stdout", real_stdout)
    assert git.current_head(missing) == "untracked"
    assert git.current_tracked_head(missing) == ""
    assert git.git_stdout(missing, "status") == ""


def test_handoff_core_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert hc._holder_ref_gaps("bad", "bad") == ["holder_ref_invalid", "target_holder_ref_invalid"]  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    assert hc._dirty_disposition_gaps([], "bad") == ["dirty_disposition_invalid"]  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    assert hc._handoff_context(context_text="x", context_file=tmp_path)[1] == "handoff_context_ambiguous"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    assert hc._handoff_context(context_text="", context_file=tmp_path / "missing")[1] == "handoff_context_file_unreadable"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    manifest = {"package_id": "p", "source_lane_ref": "work/x", "source_head": "h", "target_holder_ref": "agent:test:case:other"}  # fmt: skip
    _patch(monkeypatch, hc, repo_root=lambda root: root, workspace_status=lambda root: {"role": ACCEPTED, "dirty": False})  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setattr(hc.handoff_package, "verified_handoff_manifest", lambda **kw: (manifest, []))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    report = hc.import_cross_host_handoff(root=tmp_path, package=tmp_path, target_holder_ref="bad", apply=False)  # fmt: skip
    assert {"target_holder_ref_invalid", "handoff_target_holder_mismatch"} <= set(report["required_gaps"])  # fmt: skip
    holder, branch, head, lease_id = "agent:test:case:owner", "work/x", "h", "l"
    manifest = {
        "package_id": "p",
        "source_lane_ref": branch,
        "target_holder_ref": "agent:test:case:other",
        "source_lease_binding": {
            "holder_ref": holder,
            "lease_id": lease_id,
            "epoch": 1,
            "expected_head": head,
            "expires_at": "x",
            "payload_sha256": "y",
        },
    }
    ack = tmp_path / "ack.json"
    ack_payload = {
        "acknowledgement_id": "a",
        "package_id": "p",
        "destination_lane_ref": branch,
        "destination_head": head,
        "destination_holder_ref": "agent:test:case:other",
        "destination_lease_expected_head": head,
        "source_lease_transferred": False,
    }
    ack.write_text(json.dumps(ack_payload), encoding="utf-8")
    _patch(monkeypatch, hc, workspace_status=lambda root: {"role": WORK, "branch": branch}, _git_value=lambda *args: head, _current_lease=lambda **kw: {"expires_at": "x", "payload_sha256": "y"}, revoke_lease=lambda *args, **kw: (_ for _ in ()).throw(ValueError("stale")))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    monkeypatch.setattr(hc.handoff_package, "verified_handoff_manifest", lambda **kw: (manifest, []))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setattr(
        hc.handoff_package,
        "verified_handoff_acknowledgement",
        lambda **kw: (ack_payload, []),  # noqa: ARG005 - exact callback shape
    )

    def call(*, apply: bool) -> dict[str, object]:
        return hc.revoke_cross_host_source(root=tmp_path, package=tmp_path, acknowledgement=ack, holder_ref=holder, lease_id=lease_id, epoch=1, expected_expires_at="x", expected_payload_sha256="y", expect_head=head, apply=apply)  # fmt: skip

    assert call(apply=False)["ok"]
    assert call(apply=True)["required_gaps"] == ["stale"]


def test_handoff_manifest_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    path = package / "manifest.json"
    assert hp.verified_handoff_manifest(package=package, root=tmp_path)[1] == ["handoff_manifest_missing"]  # fmt: skip
    expected = (("[", ["handoff_manifest_invalid_json"]), ("[]", ["handoff_manifest_invalid"]))
    for text, gaps in expected:
        path.write_text(text, encoding="utf-8")
        assert hp.verified_handoff_manifest(package=package, root=tmp_path)[1] == gaps
    monkeypatch.setattr(hp, "validate_schema_instance", lambda *args, **kw: {"ok": True, "required_gaps": []})  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    (package / "digest").write_text("x", encoding="utf-8")
    payload = {"artifacts": ["bad", {"path": "missing"}, {"path": "digest", "sha256": "bad"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert hp.verified_handoff_manifest(package=package, root=tmp_path)[1] == [
        "handoff_artifact_invalid",
        "handoff_artifact_missing:missing",
        "handoff_artifact_kind_duplicate:",
        "handoff_artifact_digest_mismatch:digest",
        "handoff_artifact_kind_missing:git_bundle",
        "handoff_artifact_kind_missing:context",
        "handoff_artifact_inventory_mismatch",
    ]


def test_handoff_package_effect_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package, destination = tmp_path / "pkg", tmp_path / "repo"
    package.mkdir()
    calls: list[tuple[str, ...]] = []
    real_run = hp._run  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    _patch(monkeypatch, hp, _run=lambda root, *args: calls.append(args), acquire_lease=lambda *args, **kw: (_ for _ in ()).throw(ValueError("lease")))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip

    def git_result(args, **_kw):
        calls.append(tuple(args))
        stdout = ""
        if args[1:3] == ["bundle", "list-heads"]:
            stdout = "h refs/heads/source\n"
        elif args[1:2] == ["rev-parse"]:
            stdout = "t\n" if str(args[-1]).endswith("^{tree}") else "h\n"
        return SimpleNamespace(
            returncode=1 if args[1:3] == ["show-ref", "--verify"] else 0,
            stdout=stdout,
        )

    monkeypatch.setattr(hp.subprocess, "run", git_result)
    manifest = {
        "source_lane_ref": "work/x",
        "source_head": "h",
        "source_tree": "t",
        "package_id": "p",
        "artifacts": [],
    }
    monkeypatch.setattr(hp, "_verified_package_snapshot", lambda **_: nullcontext(package))
    with pytest.raises(ValueError, match="lease"):
        hp.apply_handoff_import(destination=destination, package=package, manifest=manifest, target_holder_ref="agent:test:case:owner")  # fmt: skip
    worktree = destination.with_name(f"{destination.name}-work-x")
    assert ("git", "worktree", "remove", "--force", worktree.as_posix()) in calls
    assert ("git", "update-ref", "-d", "refs/heads/work/x", "h") in calls
    for prefix, word in (
        (("git", "bundle", "unbundle"), "unbundle"),
        (("git", "worktree"), "worktree"),
    ):
        monkeypatch.setattr(hp, "_run", lambda root, *args, prefix=prefix, word=word: (_ for _ in ()).throw(ValueError(word)) if args[: len(prefix)] == prefix else None)  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
        with pytest.raises(ValueError, match=word):
            hp.apply_handoff_import(destination=destination, package=package, manifest=manifest, target_holder_ref="agent:test:case:owner")  # fmt: skip
    calls.clear()
    monkeypatch.setattr(hp, "_run", lambda root, *args: calls.append(args))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    for artifacts in ([], [{"kind": "tracked_patch", "path": "p"}, {"kind": "untracked_archive", "path": "a"}]):  # fmt: skip
        hp._restore_preserved_work(package=package, manifest={"dirty_disposition": "preserved", "artifacts": artifacts}, worktree=tmp_path)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    assert len(calls) == 2
    monkeypatch.setattr(hp, "_artifact", lambda path, root, kind: {"path": path.name, "kind": kind, "sha256": "x"})  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    for untracked, kinds in ((["u"], ["untracked_archive"]), ([], [])):
        monkeypatch.setattr(hp, "_git_lines", lambda *args, u=untracked: u)  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
        assert [x["kind"] for x in hp._preserve_dirty_work(repo=tmp_path, package_dir=package)] == kinds  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    output = tmp_path / "out"
    (output / "p").mkdir(parents=True)
    monkeypatch.setattr(hp, "shutil", SimpleNamespace(rmtree=lambda _path: None))
    _patch(monkeypatch, hp, _run=lambda *args: None, validate_schema_instance=lambda *args, **kw: {"ok": False, "required_gaps": ["bad"]})  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    with pytest.raises(ValueError, match="handoff_manifest_invalid:bad"):
        hp.write_handoff_package(repo=tmp_path, handoff=CrossHostHandoff(source_lane_ref="work/x", source_head="a" * 40, source_tree="b" * 40, source_holder_ref=HolderRef.parse("agent:test:case:owner"), target_holder_ref=HolderRef.parse("agent:test:case:other"), source_lease_id="l", source_lease_epoch=1, source_lease_expires_at="x", source_lease_payload_sha256="a" * 64, dirty_content_sha256="b" * 64, dirty_disposition="clean", context_digest="c" * 64), context="c", output_root=output)  # fmt: skip
    monkeypatch.setattr(hp, "_run", real_run)
    monkeypatch.setattr(hp.subprocess, "run", lambda *args, **kw: SimpleNamespace(returncode=1, stderr="bad", stdout=""))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    with pytest.raises(subprocess.SubprocessError, match="bad"):
        hp._run(tmp_path, "git", "bad")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
