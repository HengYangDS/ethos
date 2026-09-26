"""Observe a clean proof executor without transferring authoring authority."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.dirty.change_provenance import index_content_sha256
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class ProofExecutionCarrier:
    """A transient exact-source fence; the executor never owns the proof."""

    authoring: Path
    execution: Path
    common_directory: str
    head: str
    tree: str
    branch: str
    lease: JsonObject
    index_sha256: str
    content_sha256: str

    @classmethod
    def capture(
        cls,
        authoring: Path,
        execution: Path,
        *,
        head: str,
        tree: str,
        lease: JsonObject,
        expect_head: str | None = None,
    ) -> ProofExecutionCarrier:
        """Capture authority and authoring bytes, then admit an exact detached executor."""
        if expect_head is not None and expect_head != head:
            message = "expected_head_mismatch"
            raise ValueError(message)
        root = authoring.resolve()
        result = cls(
            authoring=root,
            execution=execution.resolve(),
            common_directory=git_common_dir(root),
            head=head,
            tree=tree,
            branch=current_branch(root),
            lease=mutable_json(lease_generation(lease)),
            index_sha256=index_content_sha256(root),
            content_sha256=dirty_content_sha256(root),
        )
        result.recheck()
        return result

    def recheck(self) -> None:
        """Reject authority, index, content, or execution-source drift."""
        try:
            self._recheck_authoring()
            self._recheck_execution()
        except (OSError, subprocess.SubprocessError) as error:
            message = "proof_execution_carrier_observation_unavailable"
            raise ValueError(message) from error

    def _recheck_authoring(self) -> None:
        root = self.authoring
        if (
            not self.common_directory
            or git_common_dir(root) != self.common_directory
            or current_branch(root) != self.branch
            or current_tracked_head(root) != self.head
            or current_tree(root, self.head) != self.tree
        ):
            message = "proof_authoring_source_changed"
            raise ValueError(message)
        current_lease = leases_by_branch(root).get(self.branch, {})
        if mutable_json(lease_generation(current_lease)) != self.lease:
            message = "proof_lease_generation_stale"
            raise ValueError(message)
        if (
            index_content_sha256(root) != self.index_sha256
            or dirty_content_sha256(root) != self.content_sha256
        ):
            message = "proof_authoring_content_changed"
            raise ValueError(message)

    def _recheck_execution(self) -> None:
        root = self.execution
        if root == self.authoring or git_common_dir(root) != self.common_directory:
            message = "proof_execution_carrier_foreign"
            raise ValueError(message)
        registered = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in run_git(
                self.authoring, "worktree", "list", "--porcelain", "-z", observation=True
            ).stdout.split("\0")
            if line.startswith("worktree ")
        }
        toplevel = Path(git_stdout(root, "rev-parse", "--show-toplevel")).resolve()
        if root not in registered or toplevel != root:
            message = "proof_execution_carrier_unregistered"
            raise ValueError(message)
        if current_branch(root):
            message = "proof_execution_carrier_attached"
            raise ValueError(message)
        if current_tracked_head(root) != self.head or current_tree(root, self.head) != self.tree:
            message = "proof_execution_carrier_head_mismatch"
            raise ValueError(message)
        if observe_execution_source(root, self.head, self.tree) != {
            "worktree": self.tree,
            "index": self.tree,
        }:
            message = "proof_execution_carrier_dirty"
            raise ValueError(message)
