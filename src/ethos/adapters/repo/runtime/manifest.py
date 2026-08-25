"""Canonical identity model for one immutable Python runtime carrier."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity


@dataclass(frozen=True, slots=True)
class RuntimeEnvironment:
    """Interpreter and dependency closure bound by a runtime identity."""

    python_abi: str
    python_version: str
    python_implementation: str
    dependency_lock_sha256: str
    platform: str


def runtime_environment(
    *,
    python_abi: str,
    python_version: str,
    python_implementation: str,
    dependency_lock_sha256: str,
    platform_name: str | None = None,
) -> RuntimeEnvironment:
    """Construct and validate one platform-qualified runtime environment."""
    environment = RuntimeEnvironment(
        python_abi=python_abi,
        python_version=python_version,
        python_implementation=python_implementation,
        dependency_lock_sha256=dependency_lock_sha256,
        platform=platform_name or platform.system().lower(),
    )
    if (
        not environment.python_abi
        or not environment.python_version
        or not environment.python_implementation
        or len(environment.dependency_lock_sha256) != 64
        or set(environment.dependency_lock_sha256) - set("0123456789abcdef")
        or not environment.platform
    ):
        message = "hook_runtime_environment_invalid"
        raise ValueError(message)
    return environment


def runtime_digest(
    *,
    wheel_sha256: str,
    build: BuildIdentity,
    environment: RuntimeEnvironment,
) -> str:
    """Return the content address for one build/interpreter/lock combination."""
    payload = {
        "schema_version": 4,
        "wheel_sha256": wheel_sha256,
        **{key: value for key, value in build.projection().items() if key != "schema_version"},
        **runtime_environment_projection(environment),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def runtime_environment_projection(environment: RuntimeEnvironment) -> dict[str, str]:
    """Project runtime-environment identity into a manifest payload."""
    return {
        "python_abi": environment.python_abi,
        "python_version": environment.python_version,
        "python_implementation": environment.python_implementation,
        "dependency_lock_sha256": environment.dependency_lock_sha256,
        "platform": environment.platform,
    }
