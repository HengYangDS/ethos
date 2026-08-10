"""Derive one immutable exact-CAS Commitment rebind request receipt."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.adapters.repo.commitment import changed_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid


class CommitmentRebindReceipt(BaseModel):
    """Immutable derived request whose digest excludes only itself."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: int = Field(default=1, ge=1, le=1)
    kind: str = Field(default="commitment-rebind-request", pattern="^commitment-rebind-request$")
    request: CommitmentRebindRequest
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> CommitmentRebindReceipt:
        if self.digest != canonical_json_digest(self.model_dump(mode="json", exclude={"digest"})):
            message = "commitment_rebind_receipt_digest_mismatch"
            raise ValueError(message)
        return self

    def canonical_json(self) -> str:
        """Return the stable persisted receipt bytes."""
        return self.model_dump_json(indent=None)


def derive_commitment_rebind(
    *,
    root: Path,
    target_commit: str,
    repair_change_identity: bool,
) -> dict[str, object]:
    """Observe one exact old/new generation and persist its request receipt."""
    repo = repository_root(root)
    branch = git_stdout(repo, "branch", "--show-current")
    lease = leases_by_branch(repo).get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if not actor:
        return _blocked(branch, "invocation_actor_missing")
    if actor != str(lease.get("holder_ref") or ""):
        return _blocked(branch, "lease_actor_mismatch")
    observed_targets: list[str] = []
    try:
        old = load_lease_bound_commitment(repo, lease=lease)
        if target_commit:
            target = _target_fields(
                repo,
                old=old,
                old_head=str(lease.get("expected_head") or ""),
                index_tree=git_stdout(repo, "write-tree"),
                target_commit=target_commit,
                repair_change_identity=repair_change_identity,
            )
            observed_targets = [target_commit]
        else:
            candidates = _compatible_dangling_targets(
                repo,
                old=old,
                old_head=str(lease.get("expected_head") or ""),
                index_tree=git_stdout(repo, "write-tree"),
                repair_change_identity=repair_change_identity,
            )
            observed_targets = [candidate for candidate, _fields in candidates]
            if not candidates:
                return _blocked(
                    branch,
                    "commitment_rebind_target_missing",
                    observed_targets=observed_targets,
                )
            if len(candidates) != 1:
                return _blocked(
                    branch,
                    "commitment_rebind_target_ambiguous",
                    observed_targets=observed_targets,
                )
            target_commit, target = candidates[0]
        request = CommitmentRebindRequest(
            branch=branch,
            holder_ref=actor,
            lease_id=str(lease.get("lease_id") or ""),
            expected_lane_incarnation_id=str(lease.get("lane_incarnation_id") or ""),
            expected_epoch=integer(lease.get("epoch")),
            expected_issued_at=str(lease.get("issued_at") or ""),
            expected_renewed_at=str(lease.get("renewed_at") or ""),
            expected_expires_at=str(lease.get("expires_at") or ""),
            expected_path_scope=tuple(string_sequence(lease.get("path_scope"))),
            expected_payload_sha256=str(lease.get("payload_sha256") or ""),
            expect_head=str(lease.get("expected_head") or ""),
            expected_tree=str(lease.get("expected_tree") or ""),
            expected_commitment_path=str(lease.get("base_commitment_path") or ""),
            expected_commitment_bytes_sha256=str(lease.get("base_commitment_bytes_sha256") or ""),
            expected_commitment_digest=str(lease.get("base_commitment_digest") or ""),
            expect_index_tree=git_stdout(repo, "write-tree"),
            expected_working_overlay_sha256=working_overlay_sha256(repo),
            target_commit=target_commit,
            new_commitment_path=target["base_commitment_path"],
            new_commitment_bytes_sha256=target["base_commitment_bytes_sha256"],
            new_commitment_digest=target["base_commitment_digest"],
            repair_change_identity=repair_change_identity,
            apply=False,
        )
        receipt = _receipt(request)
        payload = receipt.canonical_json().encode()
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        path = _receipt_path(repo, payload_sha256)
        write_content_addressed(
            path,
            payload,
            collision="commitment_rebind_receipt_collision",
        )
    except (OSError, TypeError, ValueError) as error:
        gap = str(error)
        return _blocked(branch, gap, observed_targets=observed_targets)
    return {
        "verdict": "pass",
        "state": "derived",
        "branch": branch,
        "request": request.model_dump(mode="json"),
        "receipt": {
            "path": path.as_posix(),
            "sha256": f"sha256:{payload_sha256}",
            "size_bytes": path.stat().st_size,
            "media_type": "application/json",
        },
        "observed_targets": observed_targets,
        "required_gaps": [],
        "next_action": f"ethos lane rebind-commitment --receipt {path} --apply --json",
    }


def load_commitment_rebind_receipt(
    root: Path,
    receipt_path: str,
    receipt_sha256: str = "",
) -> CommitmentRebindReceipt:
    """Load one receipt only from the repository's content-addressed store."""
    repo = repository_root(root)
    path = Path(receipt_path).resolve()
    store = _receipt_store(repo).resolve()
    if not path.is_relative_to(store) or path.parent != store or path.suffix != ".json":
        message = "commitment_rebind_receipt_path_invalid"
        raise ValueError(message)
    try:
        raw = path.read_bytes()
    except OSError as error:
        message = "commitment_rebind_receipt_missing"
        raise ValueError(message) from error
    digest = hashlib.sha256(raw).hexdigest()
    expected = receipt_sha256.removeprefix("sha256:") or path.stem
    if digest != expected or path.stem != expected:
        message = "commitment_rebind_receipt_sha256_mismatch"
        raise ValueError(message)
    try:
        receipt = CommitmentRebindReceipt.model_validate_json(raw)
    except ValueError as error:
        message = "commitment_rebind_receipt_invalid"
        raise ValueError(message) from error
    return receipt


def _receipt(request: CommitmentRebindRequest) -> CommitmentRebindReceipt:
    payload = {
        "schema_version": 1,
        "kind": "commitment-rebind-request",
        "request": request.model_dump(mode="json"),
    }
    return CommitmentRebindReceipt.model_validate(
        payload | {"digest": canonical_json_digest(payload)}
    )


def _compatible_dangling_targets(
    repo: Path,
    *,
    old: Commitment,
    old_head: str,
    index_tree: str,
    repair_change_identity: bool,
) -> list[tuple[str, dict[str, str]]]:
    completed = run_git(
        repo,
        "fsck",
        "--unreachable",
        "--no-reflogs",
        "--no-progress",
        check=False,
        observation=True,
    )
    object_ids = sorted(
        {
            parts[2]
            for line in completed.stdout.splitlines()
            if len(parts := line.split()) == 3
            and parts[:2] in (["unreachable", "commit"], ["dangling", "commit"])
        }
    )
    candidates: list[tuple[str, dict[str, str]]] = []
    for object_id in object_ids:
        try:
            fields = _target_fields(
                repo,
                old=old,
                old_head=old_head,
                index_tree=index_tree,
                target_commit=object_id,
                repair_change_identity=repair_change_identity,
            )
        except ValueError:
            continue
        candidates.append((object_id, fields))
    return candidates


def _target_fields(
    repo: Path,
    *,
    old: Commitment,
    old_head: str,
    index_tree: str,
    target_commit: str,
    repair_change_identity: bool,
) -> dict[str, str]:
    parents = run_git(repo, "rev-list", "--parents", "-n", "1", target_commit).stdout.split()
    if parents != [target_commit, old_head] or current_tree(repo, target_commit) != index_tree:
        message = "commitment_rebind_target_incompatible"
        raise ValueError(message)
    fields = changed_commitment_fields(
        repo,
        old_head=old_head,
        new_head=target_commit,
        commitment_id=old.id,
        old_digest=old.digest(),
        allow_identity_repair=repair_change_identity,
    )
    new = load_commitment(
        repo,
        carrier=fields["base_commitment_path"],
        tree_ref=target_commit,
        expected_digest=fields["base_commitment_digest"],
    )
    identity_repair = malformed_change_identity_repair_valid(
        carrier=fields["base_commitment_path"],
        old_id=old.id,
        old_digest=old.digest(),
        new=new,
    )
    if identity_repair != repair_change_identity:
        message = "commitment_rebind_target_incompatible"
        raise ValueError(message)
    return fields


def _receipt_store(repo: Path) -> Path:
    return Path(git_common_dir(repo)) / "ethos" / "requests" / "commitment-rebind"


def _receipt_path(repo: Path, digest: str) -> Path:
    return _receipt_store(repo) / f"{digest}.json"


def _blocked(
    branch: str,
    gap: str,
    *,
    observed_targets: list[str] | None = None,
) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "request": {},
        "receipt": {},
        "observed_targets": observed_targets or [],
        "required_gaps": [gap],
        "next_action": "",
    }
