"""Repository material observation for deterministic gate policy compilation."""

from __future__ import annotations

from pathlib import Path

import ethos
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.policy.code_subjects import CARRIER_ROLES
from ethos.repository.policy.gates import PRODUCT_PROVIDER_SOURCE
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.gates import source_paths_for_gates
from ethos.repository.profile import load_repository_profile


def resolve_gate_policy(
    root: Path | None = None,
    *,
    tree_ref: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
) -> ResolvedGatePolicy:
    """Observe repository materials and compile one content-bound gate policy."""
    return _resolve_policies(root, tree_ref, gate_ids, (full,))[0]


def resolve_proof_policies(
    root: Path, *, tree_ref: str
) -> tuple[tuple[str, ResolvedGatePolicy], ...]:
    """Compile both proof floors from one fresh observation of their combined inputs."""
    return tuple(
        zip(("full", "default"), _resolve_policies(root, tree_ref, (), (True, False)), strict=True)
    )


def _resolve_policies(
    root: Path | None, tree_ref: str | None, gate_ids: tuple[str, ...], floors: tuple[bool, ...]
) -> tuple[ResolvedGatePolicy, ...]:
    """Share material observation only within this requested policy compilation."""
    if root is None:
        return tuple(compile_gate_policy(gate_ids=gate_ids, full=full) for full in floors)
    profile = (
        load_committed_repository_profile(root, tree_ref)
        if tree_ref is not None
        else load_repository_profile(root)
    )
    registry_path = (
        profile.declaration.proof.gate_registry if profile.declaration is not None else None
    )
    registry_source = _material(root, tree_ref, registry_path) if registry_path else None
    repository_paths = _repository_paths(root, tree_ref)
    script_paths = _repository_script_paths(root, tree_ref, repository_paths)
    carrier_roles = _repository_carrier_roles(root, tree_ref, repository_paths)
    python = _repository_python(root)
    initial = tuple(
        compile_gate_policy(
            profile=profile,
            gate_registry_source=registry_source,
            repository_python=python,
            repository_paths=repository_paths,
            script_paths=script_paths,
            carrier_roles=carrier_roles,
            gate_ids=gate_ids,
            full=full,
        )
        for full in floors
    )
    materials = {
        relative: _material(root, tree_ref, relative)
        for relative in source_paths_for_gates(
            tuple(gate for policy in initial for gate in policy.gates)
        )
    }
    return tuple(
        compile_gate_policy(
            profile=profile,
            gate_registry_source=registry_source,
            source_materials=materials,
            repository_python=python,
            repository_paths=repository_paths,
            script_paths=script_paths,
            carrier_roles=carrier_roles,
            gate_ids=gate_ids,
            full=full,
        )
        for full in floors
    )


def _repository_paths(root: Path, tree_ref: str | None) -> tuple[str, ...]:
    """Observe tracked subjects at the selected Git identity, not from a profile claim."""
    arguments = ("ls-tree", "-r", "--name-only", "-z", tree_ref) if tree_ref else ("ls-files", "-z")
    completed = run_git(root, *arguments, check=tree_ref is not None, text=False, observation=True)
    if completed.returncode:
        return ()
    try:
        return tuple(path.decode("utf-8") for path in completed.stdout.split(b"\0") if path)
    except UnicodeDecodeError as error:
        message = "quality_subject_path_encoding_unknown"
        raise ValueError(message) from error


def _repository_script_paths(
    root: Path, tree_ref: str | None, repository_paths: tuple[str, ...]
) -> tuple[str, ...]:
    """Observe first-line shebangs from the exact Git tree or index in one query."""
    if not repository_paths and tree_ref is None:
        return ()
    arguments = (
        "grep",
        "-n",
        "-I",
        "-z",
        "-m",
        "1",
        "-e",
        "^#!",
        *((tree_ref,) if tree_ref else ("--cached",)),
        "--",
    )
    completed = run_git(root, *arguments, check=False, text=False, observation=True)
    if completed.returncode == 1 and not completed.stdout and not completed.stderr:
        return ()
    if completed.returncode or not completed.stdout:
        message = "quality_script_discovery_unknown"
        raise ValueError(message)
    data = completed.stdout
    prefix = f"{tree_ref}:".encode() if tree_ref else b""
    tracked = set(repository_paths)
    scripts: list[str] = []
    while data:
        try:
            raw_path, data = data.split(b"\0", 1)
            raw_line, data = data.split(b"\0", 1)
            content, data = data.split(b"\n", 1)
            path = raw_path.removeprefix(prefix).decode("utf-8")
        except (UnicodeError, ValueError) as error:
            message = "quality_script_discovery_invalid"
            raise ValueError(message) from error
        if (
            (prefix and not raw_path.startswith(prefix))
            or not raw_line.isdigit()
            or path not in tracked
            or not content.startswith(b"#!")
        ):
            message = "quality_script_discovery_invalid"
            raise ValueError(message)
        if raw_line == b"1":
            scripts.append(path)
    return tuple(sorted(set(scripts)))


def _repository_carrier_roles(
    root: Path, tree_ref: str | None, repository_paths: tuple[str, ...]
) -> tuple[tuple[str, str], ...]:
    """Read optional carrier roles from native Git attributes at the selected tree."""
    if not repository_paths:
        return ()
    arguments = (
        "check-attr",
        "-z",
        "--stdin",
        *(("--source", tree_ref) if tree_ref else ("--cached",)),
        "ethos-role",
    )
    completed = run_git(
        root,
        *arguments,
        stdin=b"\0".join(path.encode("utf-8") for path in repository_paths) + b"\0",
        check=False,
        text=False,
        observation=True,
    )
    values = completed.stdout.split(b"\0")
    if completed.returncode or values.pop() != b"" or len(values) != 3 * len(repository_paths):
        message = "quality_carrier_role_observation_unknown"
        raise ValueError(message)
    roles: list[tuple[str, str]] = []
    try:
        for index, path in enumerate(repository_paths):
            observed_path, attribute, value = values[3 * index : 3 * index + 3]
            if observed_path.decode("utf-8") != path or attribute != b"ethos-role":
                message = "quality_carrier_role_observation_invalid"
                raise ValueError(message)
            role = value.decode("utf-8")
            if role in CARRIER_ROLES:
                roles.append((path, role))
            elif role not in {"unspecified", "unset"}:
                message = f"quality_carrier_role_invalid:{path}"
                raise ValueError(message)
    except UnicodeError as error:
        message = "quality_carrier_role_observation_invalid"
        raise ValueError(message) from error
    return tuple(roles)


def _material(root: Path, tree_ref: str | None, relative: str) -> bytes | None:
    if relative.startswith(PRODUCT_PROVIDER_SOURCE):
        package = Path(ethos.__file__).resolve().parent
        path = package / relative.removeprefix(PRODUCT_PROVIDER_SOURCE)
        return path.read_bytes() if path.is_file() and not path.is_symlink() else None
    if tree_ref is not None:
        source = committed_file_bytes(root, tree_ref, relative)
        return source or None
    path = root / relative
    if path.is_symlink():
        return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved.read_bytes() if resolved.is_file() else None


def _repository_python(root: Path) -> str | None:
    candidates = (root / ".venv/bin/python", root / ".venv/Scripts/python.exe")
    return next((path.as_posix() for path in candidates if path.is_file()), None)
