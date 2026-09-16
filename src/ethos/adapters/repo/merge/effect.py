"""Execute native merge projections around the existing exact Git CAS owner."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import cast

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit.creation import create_git_commit
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_ref_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.merge.observation import MERGE_METADATA
from ethos.adapters.repo.merge.observation import MergeObservation
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import metadata_bytes
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.merge.recovery import preserve_merge
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


def _subject(root: Path, state: str, mode: str) -> dict[str, object]:
    return {"root": str(root.resolve()), "state_digest": state, "mode": mode}


def recognized_merge(
    root: Path,
    state: str,
    mode: str,
    *,
    recheck: Callable[[], None],
    request_matches: Callable[[dict[str, object]], bool],
) -> dict[str, object] | None:
    """Recognize exact prior results, never interpret historical evidence as authority."""
    subject = _subject(root, state, mode)
    records = read_attestation_set(root)[1]
    for attestation in records:
        if attestation.predicate != "effect:git-merge":
            continue
        body = attestation.payload.body
        if body.get("input", {}).get("subject") == subject:
            before = cast("dict[str, object]", mutable_json(body["input"]["observation"]))
            if not request_matches(before):
                _fail("merge_request_stale")
            output = cast("dict[str, object]", mutable_json(body.get("output", {})))
            if output.get("observation") != observe_merge(root).projection():
                _fail("merge_result_stale")
            return output
    prepared = [
        item
        for item in records
        if item.predicate == "observation:git-merge-prepared"
        and item.payload.body.get("subject") == subject
    ]
    if not prepared:
        return None
    if len(prepared) != 1:
        _fail("merge_preparation_ambiguous")
    before = cast("dict[str, object]", mutable_json(prepared[0].payload.body["observation"]))
    if not request_matches(before):
        _fail("merge_request_stale")
    recheck()
    return _recover_prepared(root, prepared[0], records, mode, state, recheck)


def _recover_prepared(
    root: Path,
    prepared: Attestation,
    records: tuple[Attestation, ...],
    mode: str,
    token: str,
    recheck: Callable[[], None],
) -> dict[str, object] | None:
    body = prepared.payload.body
    before = body["observation"]
    current = observe_merge(root)
    if canonical_json_digest(current.projection()) == canonical_json_digest(before):
        return None
    if current.competing or current.untracked_digest != before["untracked_digest"]:
        _fail("merge_outcome_unknown")
    if mode == "continue":
        refs = [
            item
            for item in records
            if item.predicate == "effect:git-ref-update"
            and item.payload.body.get("plan", {}).get("policy", {}).get("merge_state_digest")
            == token
        ]
        if len(refs) != 1:
            _fail("merge_outcome_unknown")
        plan = plan_from_attestation(refs[0])
        validate_ref_attestation(
            root, git_effect_from_plan(plan), refs[0], issuer=refs[0].verifier, plan=plan
        )
        if current.index_digest != before["index_digest"]:
            _fail("merge_outcome_unknown")
        parents = run_git(
            root, "rev-list", "--parents", "-n", "1", "HEAD", observation=True
        ).stdout.split()[1:]
        if parents != [before["head"], *before["parents"]]:
            _fail("merge_outcome_unknown")
        recheck()
        _finish_metadata(root, cast("dict[str, object]", mutable_json(before)))
        result = {
            "head": current.head,
            "state": "base_merged",
            "ref_attestation": refs[0].id,
            "parents": parents,
        }
    elif mode == "abort" and not current.parents and current.head == before["head"]:
        # Without a post-effect acknowledgement only the exact clean rollback is provable.
        for args in (("diff", "HEAD", "--quiet"), ("diff", "--cached", "HEAD", "--quiet")):
            if run_git(root, *args, check=False, observation=True).returncode:
                _fail("merge_outcome_unknown")
        result = {"head": current.head, "state": "merge_aborted"}
    else:
        _fail("merge_outcome_unknown")
    return _record_projection(
        root,
        cast("dict[str, object]", mutable_json(before)),
        mode,
        result | {"recovery": mutable_json(body["recovery"])},
        token,
    )


def _prepare(
    root: Path, observed: MergeObservation, mode: str, recovery: dict[str, object], token: str
) -> None:
    subject = _subject(root, token, mode)
    issued = datetime.now(UTC)
    record_attestation_once(
        root,
        Attestation.issue(
            {
                "schema_version": 2,
                "predicate": "observation:git-merge-prepared",
                "verifier": "git",
                "subject": f"git-merge:{canonical_json_digest(subject)}",
                "issued_at": issued,
                "valid_from": issued,
                "valid_until": None,
                "verdict": "pass",
                "payload": {
                    "kind": "observation:native",
                    "body": {
                        "subject": subject,
                        "observation": observed.projection(),
                        "recovery": recovery,
                    },
                },
                "relations": (),
                "advisories": (),
                "evidence_refs": (),
                "mints_authority": False,
                "commitment_digest": None,
                "facts_digest": observed.digest,
                "plan_digest": None,
                "policy_digest": None,
                "effect_digest": None,
            }
        ),
    )


def _record_projection(
    root: Path, before: dict[str, object], mode: str, output: dict[str, object], state_digest: str
) -> dict[str, object]:
    output = output | {"observation": observe_merge(root).projection()}
    subject = _subject(root, state_digest, mode)
    attestation = issue_native_effect(
        root,
        effect=NativeEffect(
            "effect:git-merge",
            f"git.merge.{mode}",
            ("git", "merge", mode),
            subject,
            {"subject": subject, "observation": before},
            output,
        ),
        state="applied",
        commitment_digest=None,
        repository_id=repository_identity(root, tree_ref=str(output["head"])),
    )
    record_attestations(root, (attestation,))
    return output | {"attestation": attestation.model_dump(mode="json")}


def apply_merge(
    root: Path,
    observed: MergeObservation,
    *,
    mode: str,
    incoming: str,
    candidate_ref: str,
    actor: str,
    lease: dict[str, object],
    message: str,
    recheck: Callable[[], None],
    recheck_authority: Callable[[], None],
    state_digest: str,
) -> dict[str, object]:
    """Perform one admitted native step and retain exact post-effect observations."""
    recheck()
    recovery = preserve_merge(root, observed) if mode in {"abort", "continue"} else {}
    _prepare(root, observed, mode, recovery, state_digest)
    recheck()
    if mode == "continue":
        result = _continue(
            root,
            observed,
            candidate_ref,
            incoming,
            actor,
            lease,
            message,
            recheck,
            recheck_authority,
            state_digest,
        )
    else:
        args = (
            ("--abort",)
            if mode == "abort"
            else ("--no-ff", "--no-commit", "--no-autostash", "--no-overwrite-ignore", incoming)
        )
        completed = run_git(root, "merge", *args, check=False)
        after = observe_merge(root)
        expected_parents = () if mode == "abort" else (incoming,)
        success = (
            after.head == observed.head
            and after.parents == expected_parents
            and after.untracked_digest == observed.untracked_digest
        )
        if not success or completed.returncode not in ({0} if mode == "abort" else {0, 1}):
            code = "merge_native_effect_unknown"
            raise ProcessExecutionError(
                code,
                reason="native_merge_postcondition_unproven",
                command=("git", "merge", *args),
                cwd=str(root),
                cause=completed.stderr.strip(),
                observation={
                    "before": observed.projection(),
                    "after": after.projection(),
                    "recovery": recovery,
                    "returncode": completed.returncode,
                },
            )
        result = {
            "head": after.head,
            "state": "merge_aborted" if mode == "abort" else "merge_pending",
            "observation": after.projection(),
        }
    return _record_projection(
        root, observed.projection(), mode, result | {"recovery": recovery}, state_digest
    )


def _continue(
    root: Path,
    observed: MergeObservation,
    candidate_ref: str,
    incoming: str,
    actor: str,
    lease: dict[str, object],
    message: str,
    recheck: Callable[[], None],
    recheck_authority: Callable[[], None],
    token: str,
) -> dict[str, object]:
    tree = run_git(root, "write-tree").stdout.strip()
    created = create_git_commit(
        root, tree=tree, parent=observed.head, additional_parents=observed.parents, message=message
    )
    if created.returncode:
        raise ValueError(created.stderr.strip() or "merge_commit_creation_failed")
    desired = created.stdout.strip()
    admission = commit_range_admission_report(
        root,
        target_ref=f"refs/heads/{observed.branch}",
        proposed_head=desired,
        remote_head=observed.head,
        remote_name="",
    )
    if admission["verdict"] != "pass":
        _fail(str(cast("list[str]", admission["required_gaps"])[0]))
    recheck()
    effect = GitEffect(
        updates={
            f"refs/heads/{observed.branch}": GitRefUpdate(expected=observed.head, desired=desired)
        },
        assertions={candidate_ref: incoming},
    )
    plan = compile_observed_git_effect(
        root,
        None,
        effect,
        head=observed.head,
        policy={
            "operation": "lane.merge",
            "execution_branch": observed.branch,
            "merge_state_digest": token,
        },
        values={"lease_generation": lease, "merge_observation": observed.projection()},
    )
    attestation = execute_git_effect(root, plan, issuer=actor)
    recheck_authority()
    _finish_metadata(root, observed.projection())
    return {
        "head": desired,
        "state": "base_merged",
        "ref_attestation": attestation.id,
        "parents": [observed.head, *observed.parents],
    }


def _finish_metadata(root: Path, before: dict[str, object]) -> None:
    """Clear only still-matching merge metadata after the proven ref effect."""
    observed = observe_merge(root)
    if observed.competing or observed.untracked_digest != before["untracked_digest"]:
        _fail("merge_projection_stale")
    if observed.index_digest != before["index_digest"]:
        _fail("merge_projection_stale")
    if run_git(root, "diff", "--quiet", check=False, observation=True).returncode:
        _fail("merge_projection_stale")
    for name in MERGE_METADATA:
        if name != "ORIG_HEAD":
            raw = metadata_bytes(git_path(root, name))
            if raw is not None and hashlib.sha256(raw).hexdigest() != cast(
                "dict[str, str]", before["metadata"]
            ).get(name):
                _fail("merge_projection_stale")
    if any(name != "ORIG_HEAD" for name in observed.metadata):
        run_git(root, "merge", "--quit")
