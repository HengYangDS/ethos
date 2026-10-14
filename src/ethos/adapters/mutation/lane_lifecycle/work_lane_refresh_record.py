"""Persist one Work Lane's in-flight refresh so an interrupted rewrite can be restored."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from ethos.adapters.repo.merge.observation import git_path

if TYPE_CHECKING:
    from pathlib import Path

Oid = Annotated[str, Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")]
# Git resolves this inside the lane's private worktree directory.
_RECORD = "ethos/lane-refresh.json"


class PendingRefresh(BaseModel):
    """The branch and heads of one refresh that rewrites a detached lane."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    branch: str = Field(pattern=r"^\S+$")
    previous_head: Oid
    candidate_head: Oid


def write_pending_refresh(root: Path, record: PendingRefresh) -> None:
    """Atomically replace this worktree's pending refresh record."""
    path = git_path(root, _RECORD)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f".{path.name}.{os.getpid()}")
    staged.write_text(record.model_dump_json(), encoding="utf-8")
    staged.replace(path)


def read_pending_refresh(root: Path) -> PendingRefresh | None:
    """Return this worktree's pending refresh record, or None when it has none."""
    try:
        return PendingRefresh.model_validate_json(git_path(root, _RECORD).read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValidationError) as error:
        message = "refresh_base_pending_record_invalid"
        raise ValueError(message) from error


def clear_pending_refresh(root: Path) -> None:
    """Remove this worktree's pending refresh record."""
    git_path(root, _RECORD).unlink(missing_ok=True)
