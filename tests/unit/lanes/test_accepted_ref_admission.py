"""Accepted/candidate ref-move and protected publication admission matrix.

release-mirror/accepted-policy-requires-intent|independent|FAHNP|r|main|main|c1|block|=release_mirror_ref_move_no_ref_intent
release-mirror/candidate-policy-cannot-rewrite-accepted-policy|independent|JFPA|r|main|main|c1|block|=release_mirror_ref_move_no_ref_intent
ref/accepted/off-train-blocks|independent|W|r|dev|base|work|block|~accepted_advance_not_candidate_validated+w
ref/accepted/candidate-contained-unproven-blocks|independent|WC|r|dev|base|work|block|~proof_not_proven+w
ref/candidate/unproven-blocks-fail-closed|independent||r|candidate/dev|base|zero|block|!proof
ref/candidate/proven-without-intent-blocks|independent|1P|r|candidate/dev|base|c1|block|=candidate_ref_move_no_ref_intent
policy/profile-only-defaults|profile|1|o|work/example|base|c1|pass|policy
ref/candidate/accepted-contained-rewind-passes|independent|1R|r|candidate/dev|c1|base|pass|=
ref/accepted/rollback-blocks|independent|1P2|r|dev|c2|c1|block|~accepted_ref_move_not_fast_forward
ref/accepted/non-head-blocks|independent|1P2|r|dev|base|c1|block|~accepted_ref_move_not_candidate_head
cas/equivalent-proof-keeps-binding|independent|1PIE|r|dev|base|c1|pass|=
cas/distinct-proof-closure-stales-binding|independent|1PIX|r|dev|base|c1|block|=stale_binding
intent/matching-passes|independent|1PI|r|dev|base|c1|pass|=
intent/missing-blocks|independent|1P|r|dev|base|c1|block|~accepted_ref_move_no_ref_intent
intent/mismatch-blocks|independent|1PM|r|dev|base|c1|block|~ref_intent_mismatch
intent/stale-blocks|independent|1PIS|r|dev|base|c1|block|~ref_intent_stale
cas/intent-consumed-once|independent|1PI|r|dev|base|c1|block|consume
push/accepted/off-train-blocks|offtrain||p|dev|base|work|block|~accepted_advance_not_candidate_validated
push/accepted/non-head-blocks|independent|1P2|p|dev|base|c1|block|~accepted_ref_move_not_candidate_head
push/accepted/rollback-blocks|independent|1P2|p|dev|c2|c1|block|~accepted_ref_move_not_fast_forward
push/protected/local-ref-mismatch-blocks|independent|1P|p|dev|base|c1|block|~push_to_protected_role_not_proven:local_ref_mismatch:dev
push/protected/local-closeout-passes|independent|1PA|p|dev|base|c1|pass|=
push/protected/target-role-governs|fixture||p|dev|base|c1|pass|=
push/work-lane/remote-publication-blocks|independent|W|p|work/x|base|work|block|=publication_remote_branch_forbidden:work/x
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.git_admission as admission
import ethos.adapters.admission.ref_intent as intent
import ethos.adapters.admission.ref_move_policy as ref_move_policy
import ethos.adapters.mutation.proof as proof
from tests.support import governed_repository as fx

if TYPE_CHECKING:
    from pathlib import Path


def _advance(repo: Path, name: str) -> str:
    (repo / name).write_text(name, encoding="utf-8")
    fx.git(repo, "add", ".")
    fx.git(repo, "commit", "-m", name)
    return fx.git(repo, "rev-parse", "HEAD")


class State:
    """Materialize compact claim-state codes."""

    def __init__(self, tmp: Path, mode: str) -> None:
        repo, candidate = fx.start_adopted_candidate(tmp)
        self.repo, self.v = candidate, {"base": fx.git(repo, "rev-parse", "dev"), "zero": "c" * 40}
        if mode == "offtrain":
            fixture = fx.start_adopted_work_lane(tmp / "offtrain")
            self.repo, self.v = (
                fixture.worktree,
                {"base": fx.git(fixture.repository, "rev-parse", "dev")},
            )
            self.v["work"] = fx.commit_fixture_file(self.repo, "work", "work", "work")
            fx.seed_executed_proof(self.repo, self.v["work"])
        elif mode == "profile":
            (candidate / ".ethos/workspace.toml").unlink()
        elif mode == "fixture":
            fixture = fx.start_adopted_work_lane(tmp / "fixture")
            head = fx.commit_fixture_file(
                fixture.candidate, "CANDIDATE.md", "candidate\n", "candidate"
            )
            fx.seed_executed_proof(fixture.candidate, head)
            fx.git(fixture.repository, "update-ref", "refs/heads/dev", head)
            self.repo = fixture.worktree
            self.v = {"base": fx.git(fixture.repository, "rev-parse", f"{head}^"), "c1": head}

    def run(self, codes: str) -> None:
        for code in codes:
            if code in "12WCP":
                self._topology(code)
            else:
                self._binding(code)

    def _topology(self, code: str) -> None:
        if code in "12":
            self.v[f"c{code}"] = _advance(self.repo, f"c{code}")
        elif code == "W":
            fx.git(self.repo, "checkout", "-q", "-b", "work/x")
            self.v["work"] = _advance(self.repo, "work")
        elif code == "C":
            fx.git(self.repo, "branch", "-f", "candidate/dev", self.v["work"])
        elif code == "P":
            fx.seed_executed_proof(self.repo, self.v["c1"])

    def _binding(self, code: str) -> None:
        if code in "IMR":
            old = "0" * 40 if code == "M" else self.v["c1" if code == "R" else "base"]
            new = self.v["base" if code == "R" else "c1"]
            self._intent(old, new, "candidate.refresh" if code == "R" else "candidate.accept")
        elif code == "S":
            for path in intent.ref_intent_dir(self.repo).glob("*.json"):
                data = json.loads(path.read_text()) | {"expires_at": "2000-01-01T00:00:00+00:00"}
                path.write_text(json.dumps(data))
        elif code == "E":
            first = proof.proof_attestation(self.repo, self.v["c1"])
            assert first is not None
            proof.persist_proof_attestation(
                self.repo,
                proof.Attestation.issue(
                    first.model_dump(exclude={"id", "schema_version", "statement_digest"})
                    | {"issued_at": first.issued_at + timedelta(seconds=1)}
                ),
            )
        elif code in "XA":
            if code == "X":
                self._distinct_proof()
            else:
                fx.git(self.repo, "update-ref", "refs/heads/dev", self.v["c1"], self.v["base"])
        elif code in "HJ":
            fx.git(
                self.repo,
                "branch",
                "main",
                fx.git(self.repo, "rev-parse", "HEAD" if code == "H" else "HEAD~1"),
            )
            self.v["main"] = fx.git(self.repo, "rev-parse", "main")
        else:
            self._policy("accepted_ff" if code == "F" else "independent")

    def _policy(self, value: str) -> None:
        path = self.repo / ".ethos/workspace.toml"
        current = "accepted_ff" if value == "independent" else "independent"
        path.write_text(
            path.read_text().replace(f'release_mirror = "{current}"', f'release_mirror = "{value}"')
        )
        fx.git(self.repo, "add", path.as_posix())
        fx.git(self.repo, "commit", "-m", "change release mirror policy")
        self.v["c1"] = fx.git(self.repo, "rev-parse", "HEAD")

    def _intent(self, old: str, new: str, operation: str) -> None:
        ref = "refs/heads/candidate/dev" if operation == "candidate.refresh" else "refs/heads/dev"
        update = admission.GitRefUpdate(expected=old, desired=new)
        intent.write_ref_intent(
            root=self.repo,
            ref_name=ref,
            update=update,
            operation=operation,
            plan_digest=proof.canonical_json_digest({"operation": operation}),
        )

    def _distinct_proof(self) -> None:
        head = self.v["c1"]
        plan = proof.proof_plan(self.repo, head=head, changed_paths=("other-operation",))
        checks = tuple(
            fx.conformant_proof_check(gate, self.repo, tree_ref=head)
            for gate in proof.resolve_gate_policy(self.repo, tree_ref=head).gate_ids
        )
        proof.persist_proof_attestation(
            self.repo,
            proof.issue_proof_attestation(
                self.repo,
                {
                    "plan": plan,
                    "checks": checks,
                    "verdict": "pass",
                    "issuer": "agent:test:case:ref-move",
                    "scope": "repository",
                    "boundary": "repository",
                },
            ),
        )


_ROWS = tuple(line.split("|") for line in (__doc__ or "").splitlines()[2:])


def _call(state: State, plane: str, target: str, old: str, new: str, **extra: str) -> object:
    if plane == "o":
        return ref_move_policy.resolve_ref_move_policy(
            state.repo, ref_name=f"refs/heads/{target}", old_value=old, new_value=new
        )
    if plane == "p":
        return admission.push_admission_report(
            root=state.repo, target_ref=f"refs/heads/{target}", pushed_head=new, remote_head=old
        )
    return admission.ref_move_admission_report(
        root=state.repo, ref_name=f"refs/heads/{target}", old_value=old, new_value=new, **extra
    )


@pytest.mark.parametrize("row", _ROWS, ids=lambda row: row[0])
def test_accepted_ref_admission_claim_matrix(tmp_path: Path, row: tuple[str, ...]) -> None:
    _claim, mode, actions, plane, target, old_key, new_key, verdict, boundary = row
    state = State(tmp_path, mode)
    state.run(actions)
    old, new = state.v[old_key], state.v[new_key]
    if boundary == "consume":
        assert _call(state, plane, target, old, new)["verdict"] == "pass"
        assert _call(state, plane, target, old, new, phase="committed")["verdict"] == "pass"
    report = _call(state, plane, target, old, new)
    if boundary == "policy":
        assert report == ref_move_policy.BranchRolePolicy()
        return
    assert report["verdict"] == verdict
    if boundary == "!proof":
        assert report["state"] == "blocked"
        assert report["decision"] == {"action": "block", "reason": "protected_ref_move_not_proven"}
        assert any(
            "proof" in str(gap) or "not_proven" in str(gap) for gap in report["required_gaps"]
        )
    elif boundary == "consume":
        assert report["required_gaps"] == ["ref_intent_reused"]
    elif boundary.startswith("="):
        assert report["required_gaps"] == ([boundary[1:]] if boundary[1:] else [])
    else:
        gap = boundary.removeprefix("~").removesuffix("+w")
        assert gap in report["required_gaps"]
        if boundary.endswith("+w"):
            assert _call(state, "r", "work/x", old, new)["verdict"] == "pass"
