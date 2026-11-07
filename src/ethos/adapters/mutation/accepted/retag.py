"""Re-create a repaired release tag on its replacement commit, as its original, with a receipt."""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import TypedDict

from filelock import FileLock

from ethos.adapters.actor import process_issuer
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit.creation import create_signed_tag
from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import repaired_object_provenance
from ethos.adapters.repo.commit.signature import signature_record_coordinates
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.release import release_branch_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    from collections.abc import Mapping

RETAG_PREDICATE = "release:mapped-retag"
_SIGNATURE = "-----BEGIN SSH SIGNATURE-----"


class RetagData(TypedDict):
    """The admitted re-tags, each refused tag with its gaps, and the batch's plan digest."""

    planned: dict[str, dict[str, str]]
    refused: dict[str, list[str]]
    plan_digest: str


class RetagReport(TypedDict):
    """One `land --retag` batch, in the shape `land` reports a release."""

    verdict: Literal["pass", "block"]
    state: str
    required_gaps: list[str]
    next_action: str
    data: RetagData


def mapped_retag(
    root: Path,
    *,
    tags: tuple[str, ...],
    original_tags: Mapping[str, str] | None = None,
    apply: bool = False,
    authorized: bool = False,
    expect_plan_digest: str = "",
) -> RetagReport:
    """Preview, or apply under the previewed digest, one batch of mapped release re-tags."""
    root = root.resolve()
    if apply and not authorized:
        return _report(root, ["authorization_required"], {}, {}, "")
    requests = Path(git_common_dir(root)) / "ethos/requests/release-retag"
    requests.mkdir(parents=True, exist_ok=True)
    with FileLock(requests / ".lock", mode=0o600, timeout=seconds("lock")):
        planned: dict[str, dict[str, str]] = {}
        refused: dict[str, list[str]] = {}
        for tag in dict.fromkeys(tags):
            item, gaps = _plan_one(root, tag, (original_tags or {}).get(tag, ""), requests)
            if gaps:
                refused[tag] = gaps
            else:
                planned[tag] = item
        digest = canonical_json_digest({tag: item["recreated"] for tag, item in planned.items()})
        gaps = [f"release_retag_refused:{tag}" for tag in refused]
        if apply and expect_plan_digest != digest:
            gaps.append("release_retag_plan_digest_mismatch")
        if gaps or not apply:
            return _report(root, gaps, planned, refused, digest, originals=original_tags)
        # Each moved tag records its receipt at once, so an interrupted batch leaves no
        # re-created tag without the receipt that publication reads.
        for tag, item in planned.items():
            receipt = _apply_one(root, tag, item)
            record_attestations(root, (receipt,))
            shutil.rmtree(requests / tag, ignore_errors=True)
            item["receipt"] = receipt.id
        return _report(root, [], planned, {}, digest, applied=True)


def mapped_retag_move(root: Path, *, ref: str, old: str, new: str) -> bool:
    """Return whether this exact tag move re-creates a verified mapped original, as planned."""
    tag = ref.removeprefix("refs/tags/")
    request = Path(git_common_dir(root)) / "ethos/requests/release-retag" / tag / "plan.json"
    try:
        planned = json.loads(request.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not ref.startswith("refs/tags/") or not isinstance(planned, dict):
        return False
    resolved, gaps = _resolve(root, tag, str(planned.get("original") or ""), expected=old)
    resolved.pop("tagger", None)
    resolved.pop("message", None)
    return not gaps and {**resolved, "recreated": new} == planned and _verified(root, new)


def _plan_one(
    root: Path, tag: str, original: str, requests: Path
) -> tuple[dict[str, str], list[str]]:
    """Resolve one tag, then sign its re-created object and record the request."""
    item, gaps = _resolve(root, tag, original)
    if gaps:
        return {}, gaps
    try:
        recreated = create_signed_tag(
            root,
            name=tag,
            head=item["mapped_target"],
            staging=requests / tag,
            tagger=item.pop("tagger"),
            message=item.pop("message"),
        )
    except ValueError:
        return {}, ["release_retag_signer_untrusted"]
    if not _verified(root, recreated):
        return {}, ["release_retag_signer_untrusted"]
    item["recreated"] = recreated
    (requests / tag / "plan.json").write_text(json.dumps(item, sort_keys=True), encoding="utf-8")
    return item, []


def _resolve(
    root: Path, tag: str, original: str, *, expected: str | None = None
) -> tuple[dict[str, str], list[str]]:
    """Read the original tag and map its target, without creating any object."""
    current = ref_head(root, f"refs/tags/{tag}") if expected is None else expected
    current = "" if current == zero_oid(root) else current
    original = original or current
    if original and not _is_tag(root, original):
        _restore_original(root, original)
    if not original or not _is_tag(root, original):
        return {}, ["release_retag_original_missing"]
    if current and current != original:
        return {}, ["release_retag_name_occupied"]
    tagger, message, names = _tag_parts(root, original)
    old = str(observe_git_object(root, original, "annotated-tag")["peeled_commit"])
    if names != [tag]:
        return {}, ["release_retag_original_missing"]
    try:
        repair = _mapping(root, old)
    except ValueError:
        return {}, ["release_retag_mapping_unverified"]
    if repair is None:
        return {}, ["release_retag_target_not_mapped"]
    return {
        "original": original,
        "original_target": old,
        "mapped_target": str(repair["mapped"]),
        "expected": current or zero_oid(root),
        "mapping_attestation_id": str(repair["attestation_id"]),
        "tagger": tagger,
        "message": message,
    }, []


def _restore_original(root: Path, original: str) -> None:
    """Restore a pruned original from a completed repair's backup bundle that lists it.

    The bundle must still hash to the digest its repair record bound. `git bundle unbundle`
    writes objects only, never refs, and the object id authenticates the restored tag.
    """
    _selected, members = read_attestation_set(root)
    for path, digest in filter(None, map(_bound_backup, members)):
        try:
            intact = hashlib.sha256(path.read_bytes()).hexdigest() == digest
        except OSError:
            continue
        listed = run_git(root, "bundle", "list-heads", str(path), check=False).stdout.split()
        if intact and original in listed:
            run_git(
                root, "bundle", "unbundle", str(path), check=False, timeout=seconds("git_history")
            )
            return


def _bound_backup(record: Attestation) -> tuple[Path, str] | None:
    """Return the backup bundle a valid history repair record bound, with its digest."""
    if record.predicate != RESULT:
        return None
    try:
        history = signature_record_coordinates(record).get("history")
    except ValueError:
        return None
    backup = history.get("backup") if isinstance(history, dict) else None
    if not isinstance(backup, dict) or not backup.get("path") or not backup.get("sha256"):
        return None
    return Path(str(backup["path"])), str(backup["sha256"])


def _verified(root: Path, oid: str) -> bool:
    """A re-created tag must verify under the trust anchor in force."""
    return not observe_git_object(root, oid, "annotated-tag")["required_gaps"]


def _mapping(root: Path, old: str) -> dict[str, object] | None:
    """Return the completed repair that replaced this commit, with its mapped successor."""
    accepted = ref_head(root, release_branch_policy(root).accepted_branch)
    repair = repaired_object_provenance(root, old=old, new=accepted)
    mapping = repair.get("mapping") if repair is not None else None
    mapped = mapping.get(old) if isinstance(mapping, dict) else None
    if repair is None or not isinstance(mapped, str) or mapped == old:
        return None
    return {**repair, "mapped": mapped}


def _is_tag(root: Path, oid: str) -> bool:
    kind = run_git(root, "cat-file", "-t", oid, check=False)
    return kind.returncode == 0 and kind.stdout.strip() == "tag"


def _tag_parts(root: Path, oid: str) -> tuple[str, str, list[str]]:
    """Return the original tagger line, the message without its signature, and the tag names."""
    raw = run_git(root, "cat-file", "tag", oid).stdout
    header, _, body = raw.partition("\n\n")
    lines = header.splitlines()
    tagger = next((line[7:] for line in lines if line.startswith("tagger ")), "")
    names = [line[4:] for line in lines if line.startswith("tag ")]
    return tagger, body.split(_SIGNATURE, 1)[0], names


def _apply_one(root: Path, tag: str, item: Mapping[str, str]) -> Attestation:
    """Move the tag ref by exact CAS under its own ref intent, then issue the receipt."""
    ref = f"refs/tags/{tag}"
    effect = GitEffect(
        updates={ref: GitRefUpdate(expected=item["expected"], desired=item["recreated"])},
        assertions={},
    )
    actor = process_issuer()
    plan = compile_observed_git_effect(
        root,
        None,
        effect,
        head=item["mapped_target"],
        policy={"operation": "release.retag", "actor": actor},
        values={"release_retag": dict(item), "root": root.as_posix()},
    )
    execute_git_effect(root, plan, issuer=actor)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": RETAG_PREDICATE,
            "verifier": "ethos:release-retag",
            "subject": f"git:annotated-tag:{item['recreated']}",
            "issued_at": datetime.now(UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": RETAG_PREDICATE,
                "body": {
                    "tag": tag,
                    "original_tag": item["original"],
                    "original_target": item["original_target"],
                    "mapped_target": item["mapped_target"],
                    "mapping_attestation_id": item["mapping_attestation_id"],
                },
            },
            "relations": (),
            "advisories": (),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect.digest(),
            "evidence_refs": (f"git:local:{ref}:{item['recreated']}",),
            "mints_authority": False,
        }
    )


def _report(
    root: Path,
    gaps: list[str],
    planned: Mapping[str, Mapping[str, str]],
    refused: Mapping[str, list[str]],
    digest: str,
    *,
    applied: bool = False,
    originals: Mapping[str, str] | None = None,
) -> RetagReport:
    """Report one batch as `land` reports a release: the apply command follows a clean preview."""
    command = shlex.join(
        (
            "ethos",
            "land",
            *(f"--retag={tag}" for tag in planned),
            *(
                f"--original-tag={tag}={oid}"
                for tag, oid in (originals or {}).items()
                if tag in planned
            ),
            "--apply",
            "--authorize",
            f"--expect-plan-digest={digest}",
            "--root",
            str(root),
            "--json",
        )
    )
    return {
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "retagged" if applied else "ready_to_retag",
        "required_gaps": list(dict.fromkeys(gaps)),
        "next_action": "" if gaps or applied or not planned else command,
        "data": {
            "planned": {tag: dict(item) for tag, item in planned.items()},
            "refused": {tag: list(item) for tag, item in refused.items()},
            "plan_digest": digest,
        },
    }
