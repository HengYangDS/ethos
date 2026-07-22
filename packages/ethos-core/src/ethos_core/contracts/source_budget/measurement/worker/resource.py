"""Canonical descriptor for future source-budget worker resource supervision."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

WORKER_RESOURCE_PROFILE_ID = "ethos-source-budget-worker-resource-profile-v1"


class WorkerResourceProfileDescriptor(BaseModel):
    """Immutable resource intent without supervisor or platform behavior."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-worker-resource-profile-descriptor-v1"] = Field(
        alias="schema"
    )
    id: Literal["ethos-source-budget-worker-resource-profile-v1"]
    cpu_soft_seconds: Literal[5]
    cpu_hard_seconds: Literal[6]
    wall_seconds: Literal[8]
    rss_bytes: Literal[134217728]
    sample_interval_ms: Literal[10]
    linux_address_space_bytes: Literal[536870912]
    darwin_vms_growth_bytes: Literal[536870912]
    nofile: Literal[32]
    nproc: Literal[1]
    core_bytes: Literal[0]
    regular_file_bytes: Literal[0]
    term_grace_ms: Literal[100]
    stderr_bytes: Literal[0]
    private_home_tmp_cwd: Literal[True]
    isolated_python_flags: tuple[Literal["-I"], Literal["-B"], Literal["-X"], Literal["utf8"]]
    close_file_descriptors: Literal[True]
    start_new_session: Literal[True]

    @field_validator(
        "cpu_soft_seconds",
        "cpu_hard_seconds",
        "wall_seconds",
        "rss_bytes",
        "sample_interval_ms",
        "linux_address_space_bytes",
        "darwin_vms_growth_bytes",
        "nofile",
        "nproc",
        "core_bytes",
        "regular_file_bytes",
        "term_grace_ms",
        "stderr_bytes",
        mode="before",
    )
    @classmethod
    def validate_exact_integer(cls, value: object) -> object:
        """Reject equal-but-non-integer resource values."""
        if type(value) is not int:
            raise ValueError("worker resource descriptor integers must be exact")
        return value

    @field_validator(
        "private_home_tmp_cwd",
        "close_file_descriptors",
        "start_new_session",
        mode="before",
    )
    @classmethod
    def validate_exact_true(cls, value: object) -> object:
        """Reject truthy wire values other than the boolean singleton."""
        if value is not True:
            raise ValueError("worker resource descriptor booleans must be exact")
        return value


def worker_resource_profile_descriptor() -> WorkerResourceProfileDescriptor:
    """Return the complete resource descriptor without enforcement behavior."""
    return WorkerResourceProfileDescriptor(
        schema="ethos-source-budget-worker-resource-profile-descriptor-v1",
        id=WORKER_RESOURCE_PROFILE_ID,
        cpu_soft_seconds=5,
        cpu_hard_seconds=6,
        wall_seconds=8,
        rss_bytes=134217728,
        sample_interval_ms=10,
        linux_address_space_bytes=536870912,
        darwin_vms_growth_bytes=536870912,
        nofile=32,
        nproc=1,
        core_bytes=0,
        regular_file_bytes=0,
        term_grace_ms=100,
        stderr_bytes=0,
        private_home_tmp_cwd=True,
        isolated_python_flags=("-I", "-B", "-X", "utf8"),
        close_file_descriptors=True,
        start_new_session=True,
    )


def worker_resource_profile_descriptor_digest(
    descriptor: WorkerResourceProfileDescriptor,
) -> str:
    """Return canonical compact sorted-key JSON SHA-256 for one descriptor."""
    if type(descriptor) is not WorkerResourceProfileDescriptor:
        raise ValueError("worker resource profile descriptor must be canonical")
    expected_fields = set(WorkerResourceProfileDescriptor.model_fields)
    if set(vars(descriptor)) != expected_fields or descriptor.model_fields_set != expected_fields:
        raise ValueError("worker resource profile descriptor must be canonical")
    canonical = WorkerResourceProfileDescriptor.model_validate(descriptor.model_dump(mode="python"))
    encoded = json.dumps(
        canonical.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
