"""Immutable contracts for resumable Work Lane retirement."""

from __future__ import annotations

import operator
from pathlib import Path
from pathlib import PurePosixPath
from typing import Annotated
from typing import ClassVar
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.outcome import refuse
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject

RetirementEffect = Literal["remove_worktree", "delete_ref", "revoke_lease"]
CarrierState = Literal["expected", "absent", "moved", "unavailable"]
AcceptedState = Literal["expected", "advanced", "absent", "moved", "unavailable"]


class _ContentNode(BaseModel):
    """One exact literal filesystem node, without following its target."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    kind: Literal["directory", "file", "symlink"]
    identity: FrozenTuple[Annotated[str, Field(pattern=r"^(?:0|-?[1-9][0-9]*)$")]] = Field(
        min_length=8, max_length=8
    )
    sha256: str = Field(default="", pattern=r"^[a-f0-9]{64}$")
    target: str = Field(default="", min_length=1)

    @model_validator(mode="after")
    def validate_payload(self) -> Self:
        fields = {"kind", "identity"}
        if self.kind != "directory":
            fields.add("sha256" if self.kind == "file" else "target")
        if self.model_fields_set != fields:
            refuse("retirement_content_node_invalid")
        return self


class ReviewedManifest(BaseModel):
    """Every literal node of one reviewed worktree, kept apart from its request by digest."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["lane-retirement-manifest"] = "lane-retirement-manifest"
    entries: dict[str, _ContentNode] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_tree(self) -> Self:
        marker = self.entries.get(".git")
        if marker is None or marker.kind != "file":
            refuse("retirement_content_tree_invalid")
        for name in self.entries:
            path = PurePosixPath(name)
            parent = self.entries.get(path.parent.as_posix())
            if (
                not name
                or name == "."
                or path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != name
                or (path.name == ".git" and name != ".git")
                or (
                    path.parent != PurePosixPath()
                    and (parent is None or parent.kind != "directory")
                )
            ):
                refuse("retirement_content_tree_invalid")
        return self

    def totals(self) -> dict[str, dict[str, int]]:
        """Count each top-level name's directories, files and symlinks and sum its file sizes."""
        totals: dict[str, dict[str, int]] = {}
        for name, node in self.entries.items():
            counts = totals.setdefault(
                PurePosixPath(name).parts[0],
                {"directories": 0, "files": 0, "symlinks": 0, "file_bytes": 0},
            )
            counts[{"directory": "directories", "file": "files"}.get(node.kind, "symlinks")] += 1
            if node.kind == "file":
                counts["file_bytes"] += int(node.identity[4])
        return totals


class _ManifestTotals(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    directories: int = Field(ge=0)
    files: int = Field(ge=0)
    symlinks: int = Field(ge=0)
    file_bytes: int = Field(ge=0)


class _ManifestReference(BaseModel):
    """The digest, size and per-root totals by which a request binds its reviewed manifest."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=1)
    totals: dict[str, _ManifestTotals] = Field(min_length=1)


class _ReviewedContent(BaseModel):
    """A literal tree's root, native index and manifest reference, selected for disposal review."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: _ContentNode
    index_path: str
    index: _ContentNode
    manifest: _ManifestReference

    @model_validator(mode="after")
    def validate_tree(self) -> Self:
        marker = self.manifest.totals.get(".git")
        if (
            self.root.kind != "directory"
            or self.index.kind != "file"
            or not Path(self.index_path).is_absolute()
            or marker is None
            or (marker.directories, marker.files, marker.symlinks) != (0, 1, 0)
        ):
            refuse("retirement_content_tree_invalid")
        return self


class LinkedRetirementRequest(BaseModel):
    """Exact request for one linked Work Lane retirement transition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    branch: str | None = None
    path: str | None = None
    expect_head: str | None = None
    absorbed_by: str = ""
    reason: str = ""
    authorize: bool = False
    apply: bool = False


class RetirementObservation(BaseModel):
    """Fresh native state for the carriers owned by one retirement."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    worktree_state: CarrierState
    ref_state: CarrierState
    lease_state: CarrierState
    accepted_state: AcceptedState = "expected"


class RetirementOperation(BaseModel):
    """One immutable terminal intent for a Work Lane retirement."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["lane-retirement-operation"] = "lane-retirement-operation"
    repository_common_dir: str = Field(min_length=1)
    repository_identity: str = ""
    control_root: str = Field(min_length=1)
    execution_root: str = ""
    mode: Literal["landed", "superseded", "abandon"]
    branch: str
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    accepted_branch: str = Field(min_length=1)
    accepted_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    worktree_path: str = ""
    worktree_initial: Literal["linked", "unbound"]
    lease_state: Literal["valid", "expired", "missing"]
    lease: JsonObject
    authority: JsonObject
    reason: JsonObject
    git_plan: JsonObject
    reviewed_content: JsonObject = Field(default_factory=dict, exclude_if=operator.not_)
    effects: FrozenTuple[RetirementEffect] = ()

    @field_validator("reviewed_content", mode="before")
    @classmethod
    def validate_reviewed_content(cls, value: object) -> object:
        if value:
            _ReviewedContent.model_validate(value)
        return value

    @model_validator(mode="after")
    def derive_effects(self) -> Self:
        if not self.branch and (
            self.mode != "abandon"
            or self.worktree_initial != "linked"
            or not self.reviewed_content
            or self.lease_state != "missing"
            or self.lease
            or self.git_plan
        ):
            refuse("retirement_detached_resources_invalid")
        expected = (
            *(("remove_worktree",) if self.worktree_initial == "linked" else ()),
            *(("delete_ref",) if self.branch else ()),
            *(("revoke_lease",) if self.lease_state != "missing" else ()),
        )
        if self.effects and self.effects != expected:
            refuse("retirement_operation_effects_invalid")
        if self.worktree_initial == "linked" and not self.worktree_path:
            refuse("retirement_operation_worktree_path_missing")
        if self.mode == "abandon" and not self.reason:
            refuse("lane_abandonment_reason_invalid")
        if self.reviewed_content and (self.mode != "abandon" or self.worktree_initial != "linked"):
            refuse("retirement_reviewed_content_invalid")
        if not self.execution_root:
            object.__setattr__(self, "execution_root", self.control_root)
        object.__setattr__(self, "effects", expected)
        return self


class UninspectableProcess(BaseModel):
    """A process that denied every /proc entry the open-file observer read."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    pid: int = Field(ge=1)
    uid: int = Field(ge=0)
    command: str


class OpenFileBoundary(BaseModel):
    """The processes one open-file observation covered and those it could not inspect."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    observation_boundary: Literal["inspectable processes of the invoking user"] = (
        "inspectable processes of the invoking user"
    )
    # None where the platform omits uninspectable processes without a record.
    uninspectable_processes: FrozenTuple[UninspectableProcess] | None


class RetirementProgress(BaseModel):
    """Pure projection of one operation against current native carriers."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["lane-retirement-progress"] = "lane-retirement-progress"
    request_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    state: Literal["ready", "partial_transition", "terminal"]
    observation: RetirementObservation
    completed_effects: FrozenTuple[RetirementEffect]
    remaining_effects: FrozenTuple[RetirementEffect]
    # The open-file observation of the content admission behind this snapshot.
    open_file_observation: OpenFileBoundary | None = None
