"""Observed Python and dependency-lock inputs for runtime materialization."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import runtime_environment

if TYPE_CHECKING:
    from pathlib import Path


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def observe_python_facts(python: Path) -> dict[str, str]:
    """Observe the exact ABI, version, implementation, and prefixes of Python."""
    script = (
        "import json,platform,sys;print(json.dumps({"
        "'python_abi':sys.implementation.cache_tag or '',"
        "'python_version':platform.python_version(),"
        "'python_implementation':sys.implementation.name,"
        "'architecture':platform.machine(),"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"
    )
    completed = subprocess.run(
        (python.as_posix(), "-B", "-I", "-c", script),
        capture_output=True,
        check=False,
        text=True,
    )
    try:
        facts = {key: str(value) for key, value in json.loads(completed.stdout).items()}
    except (AttributeError, TypeError, ValueError) as error:
        _fail("hook_runtime_python_abi_invalid", error)
    required = (
        "python_abi",
        "python_version",
        "python_implementation",
        "architecture",
        "prefix",
        "base_prefix",
    )
    if completed.returncode or not all(facts.get(key) for key in required):
        _fail("hook_runtime_python_abi_invalid")
    return facts


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one exact materialization input."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe_runtime_environment(
    source: Path,
    interpreter: Path,
    *,
    python_facts: dict[str, str] | None = None,
) -> RuntimeEnvironment:
    """Bind runtime environment identity to Python facts and the dependency lock."""
    facts = python_facts or observe_python_facts(interpreter)
    return runtime_environment(
        python_abi=facts["python_abi"],
        python_version=facts["python_version"],
        python_implementation=facts["python_implementation"],
        dependency_lock_sha256=file_sha256(source / "uv.lock"),
        architecture_name=facts["architecture"],
    )
