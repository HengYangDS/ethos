"""Two-phase exceptional Work Lane resolution with preservation-first effects."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import ValidationError

from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import mutation_envelope
from ethos.adapters.store.state.lease import active_leases
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision


def plan_lane_resolution(
    *,
    root: Path,
    branch: str,
    disposition: str,
    reason: str,
    evidence_refs: tuple[str, ...],
    chronicle_ref: str,
    recovery_plan: str,
    decision_path: Path,
    break_glass: bool,
    apply: bool,
) -> dict[str, object]:
    """Create the first-phase exceptional judgment; no lane effect occurs."""
    observation, gaps = _observe_lane(root, branch)
    if disposition not in {"block", "preserve", "retire"}:
        gaps.append("lane_resolution_disposition_invalid")
    if not reason.strip():
        gaps.append("lane_resolution_reason_required")
    if not evidence_refs:
        gaps.append("lane_resolution_evidence_required")
    chronicle_path, chronicle_digest, chronicle_gaps = _accepted_chronicle(
        root, chronicle_ref=chronicle_ref, disposition=disposition
    )
    gaps.extend(chronicle_gaps)
    if not recovery_plan.strip():
        gaps.append("lane_resolution_recovery_plan_required")
    if disposition == "retire" and not break_glass:
        gaps.append("retire_exception_requires_break_glass")
    if not _local_artifact_path(root, decision_path):
        gaps.append("lane_resolution_decision_path_not_local_artifact")
    report = _report(branch=branch, apply=apply, gaps=gaps)
    if apply and not gaps:
        decision = LaneResolutionDecision(
            decision_id=f"lane-decision:{uuid.uuid4()}",
            disposition=cast("Any", disposition),
            observation=observation,
            evidence_refs=evidence_refs,
            chronicle_ref=chronicle_path,
            chronicle_digest=chronicle_digest,
            recovery_plan=recovery_plan,
            reason=reason,
            break_glass=break_glass,
        ).to_payload()
        validation = validate_schema_instance(
            "lane-resolution-decision.schema.json", decision, root=root
        )
        if not validation["ok"]:
            report.update(
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_decision_invalid"],
            )
            return report
        decision_path.resolve().parent.mkdir(parents=True, exist_ok=True)
        decision_path.resolve().write_text(
            json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        report.update(
            state="decision_recorded",
            decision=decision,
            decision_path=decision_path.resolve().as_posix(),
            chronicle_event=_chronicle_decision(decision),
        )
    report["mutation"] = _envelope(
        command="lane-resolution-plan",
        action="lane.resolution.decide",
        resource=branch,
        expected_state={"observation_digest": observation.digest() if not gaps else ""},
        report=report,
        apply=apply,
    )
    return report


def apply_lane_resolution(
    *,
    root: Path,
    decision_path: Path,
    confirm_irreversible: bool,
    apply: bool,
) -> dict[str, object]:
    """Recompute the decision observation, then apply the bounded disposition."""
    decision, gaps = _read_decision(decision_path, root=root)
    branch = str(decision.get("observation", {}).get("lane_ref") or "")
    observation, observation_gaps = _observe_lane(root, branch)
    gaps.extend(observation_gaps)
    if decision and observation.digest() != str(decision.get("observation_digest") or ""):
        gaps.append("lane_resolution_observation_stale")
    disposition = str(decision.get("disposition") or "")
    if disposition == "retire" and not confirm_irreversible:
        gaps.append("irreversible_confirmation_required")
    if disposition == "retire" and observation.dirty:
        gaps.append("dirty_lane_retirement_blocked")
    report = _report(branch=branch, apply=apply, gaps=list(dict.fromkeys(gaps)))
    if apply and not report["required_gaps"]:
        if disposition == "preserve":
            package = _preserve(root=root, observation=observation, decision=decision)
            report.update(state="preserved", preservation_package=package)
        elif disposition == "retire":
            _retire(root=root, observation=observation)
            report.update(state="retired")
        else:
            report.update(state="blocked_by_decision")
        receipt = _completion_receipt(
            decision=decision,
            observation=observation,
            state=str(report["state"]),
        )
        validation = validate_schema_instance(
            "lane-resolution-receipt.schema.json", receipt, root=root
        )
        if not validation["ok"]:
            report.update(
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_receipt_invalid"],
            )
            return report
        report["receipt"] = receipt
        report["chronicle_event"] = _chronicle_completion(decision, receipt)
    report["mutation"] = _envelope(
        command="lane-resolution-apply",
        action=f"lane.resolution.{disposition or 'unknown'}",
        resource=branch or decision_path.resolve().as_posix(),
        expected_state={
            "decision_id": str(decision.get("decision_id") or ""),
            "observation_digest": str(decision.get("observation_digest") or ""),
            "confirm_irreversible": confirm_irreversible,
        },
        report=report,
        apply=apply,
        confirmation=confirm_irreversible,
    )
    return report


def _observe_lane(root: Path, branch: str) -> tuple[LaneObservation, list[str]]:
    worktree = _worktree(root, branch)
    gaps: list[str] = []
    if not worktree:
        gaps.append("lane_resolution_target_missing")
        return _empty_observation(root, branch), gaps
    path = Path(worktree["worktree"])
    head = _git(root, "rev-parse", f"refs/heads/{branch}")
    dirty = bool(_git(path, "status", "--porcelain", check=False))
    tracked_digest = hashlib.sha256(
        _git(path, "diff", "--binary", "HEAD", "--", check=False).encode()
    ).hexdigest()
    untracked_digest = _untracked_digest(path)
    leases = [lease for lease in _leases(root) if lease.get("subject") == branch]
    ambiguous = len(leases) > 1
    lease = leases[0] if len(leases) == 1 else {}
    holder_ref = str(lease.get("holder_ref") or "")
    incarnation = str(lease.get("lane_incarnation_id") or "")
    if not incarnation:
        seed = f"{branch}\0{head}\0{path.resolve().as_posix()}"
        incarnation = f"decision-incarnation:{hashlib.sha256(seed.encode()).hexdigest()}"
    return (
        LaneObservation(
            lane_ref=branch,
            head=head,
            lane_incarnation_id=incarnation,
            holder_ref=holder_ref,
            path=path.resolve().as_posix(),
            dirty=dirty,
            foreign=not bool(holder_ref),
            orphan=not bool(leases),
            ambiguous=ambiguous,
            tracked_digest=tracked_digest,
            untracked_digest=untracked_digest,
        ),
        gaps,
    )


def _worktree(root: Path, branch: str) -> dict[str, str]:
    output = _git(root, "worktree", "list", "--porcelain", check=False)
    current: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    for line in [*output.splitlines(), ""]:
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    ref = f"refs/heads/{branch}"
    return next((row for row in rows if row.get("branch") == ref), {})


def _leases(root: Path) -> list[dict[str, Any]]:
    common = _git(root, "rev-parse", "--git-common-dir")
    common_path = Path(common) if Path(common).is_absolute() else root / common
    control_root = common_path.resolve().parent
    return active_leases(control_root / ".ethos" / "state" / "state.sqlite")


def _read_decision(path: Path, *, root: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
        observation = LaneObservation.model_validate(payload.get("observation"))
        LaneResolutionDecision(
            decision_id=payload.get("decision_id"),
            disposition=payload.get("disposition"),
            observation=observation,
            evidence_refs=tuple(payload.get("evidence_refs", [])),
            chronicle_ref=payload.get("chronicle_ref"),
            chronicle_digest=payload.get("chronicle_digest"),
            recovery_plan=payload.get("recovery_plan"),
            reason=payload.get("reason"),
            break_glass=bool(payload.get("break_glass")),
        )
    except (OSError, json.JSONDecodeError, ValidationError, TypeError):
        return {}, ["lane_resolution_decision_invalid"]
    validation = validate_schema_instance(
        "lane-resolution-decision.schema.json", payload, root=root
    )
    if not validation["ok"]:
        return cast("dict[str, Any]", payload), ["lane_resolution_decision_invalid"]
    if observation.digest() != payload.get("observation_digest"):
        return cast("dict[str, Any]", payload), ["lane_resolution_decision_digest_invalid"]
    return cast("dict[str, Any]", payload), []


def _local_artifact_path(root: Path, path: Path) -> bool:
    resolved = path.resolve()
    repository = root.resolve()
    try:
        relative = resolved.relative_to(repository)
    except ValueError:
        return True
    return relative.parts[:2] in {("build", "artifacts"), ("build", "evidence")}


def _untracked_digest(path: Path) -> str:
    inventory = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=path,
        check=False,
        capture_output=True,
    )
    if inventory.returncode != 0:
        return hashlib.sha256(b"unavailable").hexdigest()
    digest = hashlib.sha256()
    for raw in sorted(item for item in inventory.stdout.split(b"\0") if item):
        relative = raw.decode(errors="surrogateescape")
        digest.update(raw)
        digest.update(b"\0")
        file_path = path / relative
        digest.update(file_path.read_bytes() if file_path.is_file() else b"")
        digest.update(b"\0")
    return digest.hexdigest()


def _accepted_chronicle(
    root: Path, *, chronicle_ref: str, disposition: str
) -> tuple[str, str, list[str]]:
    if not chronicle_ref.strip():
        return "", "", ["lane_resolution_chronicle_required"]
    path = (root / chronicle_ref).resolve()
    try:
        relative = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return "", "", ["lane_resolution_chronicle_outside_repository"]
    if not relative.startswith("evidence/chronicle/") or not path.is_file():
        return relative, "", ["lane_resolution_chronicle_missing"]
    if f"lane_resolution/{disposition}" not in path.read_text(encoding="utf-8"):
        return relative, "", ["lane_resolution_chronicle_disposition_mismatch"]
    return relative, hashlib.sha256(path.read_bytes()).hexdigest(), []


def _preserve(
    *, root: Path, observation: LaneObservation, decision: dict[str, Any]
) -> dict[str, object]:
    relative = Path("build") / "artifacts" / "lane-resolution" / str(decision["decision_id"])
    package = root / relative
    package.mkdir(parents=True, exist_ok=True)
    bundle = package / "repository.bundle"
    _run(Path(observation.path), "git", "bundle", "create", bundle.as_posix(), observation.lane_ref)
    patch = package / "tracked.patch"
    completed = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--"],
        cwd=observation.path,
        check=False,
        capture_output=True,
    )
    patch.write_bytes(completed.stdout)
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=observation.path,
        check=False,
        capture_output=True,
    )
    if untracked.returncode != 0:
        raise ValueError("lane_resolution_untracked_inventory_failed")
    untracked_paths = [
        path.decode(errors="surrogateescape") for path in untracked.stdout.split(b"\0") if path
    ]
    archive = package / "untracked.tar"
    if untracked_paths:
        _run(Path(observation.path), "tar", "-cf", archive.as_posix(), "--", *untracked_paths)
    manifest = {
        "decision_id": decision["decision_id"],
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "observation_digest": observation.digest(),
        "bundle_sha256": _sha256(bundle),
        "patch_sha256": _sha256(patch),
        "untracked_archive_sha256": _sha256(archive) if archive.is_file() else "",
        "source_lease_transferred": False,
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"path": relative.as_posix(), "manifest": manifest}


def _retire(*, root: Path, observation: LaneObservation) -> None:
    ref = f"refs/heads/{observation.lane_ref}"
    delete = subprocess.run(
        ["git", "update-ref", "-d", ref, observation.head],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if delete.returncode != 0:
        raise ValueError("lane_resolution_branch_delete_failed")
    remove = subprocess.run(
        ["git", "worktree", "remove", "--force", observation.path],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if remove.returncode != 0:
        subprocess.run(
            ["git", "update-ref", ref, observation.head, "0" * 40], cwd=root, check=False
        )
        raise ValueError("lane_resolution_worktree_remove_failed")


def _completion_receipt(
    *, decision: dict[str, Any], observation: LaneObservation, state: str
) -> dict[str, object]:
    return {
        "receipt_id": f"lane-resolution-receipt:{uuid.uuid4()}",
        "decision_id": str(decision["decision_id"]),
        "disposition": str(decision["disposition"]),
        "completed": True,
        "state": state,
        "observation_digest": observation.digest(),
        "reconciliation_required": bool(decision.get("break_glass")),
        "mints_authority": False,
    }


def _chronicle_decision(decision: dict[str, Any]) -> dict[str, object]:
    return {
        "event_type": "decision",
        "subject_id": str(decision["observation"]["lane_ref"]),
        "decision": str(decision["disposition"]),
        "evidence_ids": list(decision["evidence_refs"]),
        "current_state_delta": "exceptional resolution accepted; effect pending recomputation",
    }


def _chronicle_completion(
    decision: dict[str, Any], receipt: dict[str, object]
) -> dict[str, object]:
    return {
        "event_type": "state_change",
        "subject_id": str(decision["observation"]["lane_ref"]),
        "decision": str(decision["disposition"]),
        "evidence_ids": [str(receipt["receipt_id"])],
        "current_state_delta": str(receipt["state"]),
    }


def _report(*, branch: str, apply: bool, gaps: list[str]) -> dict[str, object]:
    return {
        "ok": not gaps,
        "state": "planned" if not apply and not gaps else "blocked" if gaps else "applying",
        "branch": branch,
        "decision": {},
        "decision_path": "",
        "preservation_package": {},
        "receipt": {},
        "chronicle_event": {},
        "required_gaps": gaps,
    }


def _envelope(
    *,
    command: str,
    action: str,
    resource: str,
    expected_state: dict[str, object],
    report: dict[str, object],
    apply: bool,
    confirmation: bool = False,
) -> dict[str, object]:
    gaps = tuple(str(gap) for gap in cast("list[object]", report["required_gaps"]))
    return mutation_envelope(
        MutationRequest(command=command, apply=apply, authorized=confirmation, expect_head=None),
        action=action,
        resource=resource,
        expected_state=expected_state,
        verdict=cast("Any", "allow" if report["ok"] else "block"),
        required_gaps=gaps,
        state=str(report["state"]),
        evidence_boundary="accepted_chronicle_decision_and_recomputed_observation",
        enforcement_boundary="local_git_and_filesystem_transition",
        verifier_provenance="current_runner",
    )


def _empty_observation(root: Path, branch: str) -> LaneObservation:
    return LaneObservation(
        lane_ref=branch or "unknown",
        head="0" * 40,
        lane_incarnation_id="missing",
        path=root.resolve().as_posix(),
        dirty=True,
        foreign=True,
        orphan=True,
        ambiguous=True,
        tracked_digest=hashlib.sha256(b"").hexdigest(),
        untracked_digest=hashlib.sha256(b"").hexdigest(),
    )


def _git(root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    if check and completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "git_command_failed")
    return completed.stdout.strip()


def _run(root: Path, *args: str) -> None:
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "command_failed")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
