from __future__ import annotations

from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.selection import runtime_python
from ethos.repository.release.identity import BuildIdentity


def _build() -> BuildIdentity:
    return BuildIdentity(
        product_version="0.2.0-alpha.1",
        distribution_version="0.2.0a1.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="development",
        acceptance_state="unaccepted",
    )


def test_runtime_identity_binds_interpreter_and_locked_dependency_closure() -> None:
    baseline = runtime_digest(
        wheel_sha256="c" * 64,
        build=_build(),
        environment=runtime_environment(
            python_abi="cpython-314",
            python_version="3.14.7",
            python_implementation="cpython",
            dependency_lock_sha256="d" * 64,
        ),
    )

    assert baseline != runtime_digest(
        wheel_sha256="c" * 64,
        build=_build(),
        environment=runtime_environment(
            python_abi="cpython-314",
            python_version="3.14.8",
            python_implementation="cpython",
            dependency_lock_sha256="d" * 64,
        ),
    )
    assert baseline != runtime_digest(
        wheel_sha256="c" * 64,
        build=_build(),
        environment=runtime_environment(
            python_abi="cpython-314",
            python_version="3.14.7",
            python_implementation="cpython",
            dependency_lock_sha256="e" * 64,
        ),
    )


def test_runtime_carrier_has_one_python_home_and_no_venv_alias() -> None:
    assert runtime_python.__doc__ == "Return the executable inside one owned interpreter home."
