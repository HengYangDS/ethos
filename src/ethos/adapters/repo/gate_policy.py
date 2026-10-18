"""Repository material observation for deterministic gate policy compilation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ethos
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.policy.code_subjects import CARRIER_ROLES
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.code_subjects import source_binding_gaps
from ethos.repository.policy.gates import PRODUCT_PROVIDER_SOURCE
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_declaration as compile_gate_declaration
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.gates import source_paths_for_gates
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from ethos.contracts.gates import GateRegistryDeclaration
    from ethos.contracts.proof.plan import AcceptancePurpose
    from ethos.repository.policy.code_subjects import CodeSubject


def resolve_committed_gate_declaration(root: Path, tree_ref: str) -> GateRegistryDeclaration:
    """Observe only the exact committed profile and its declared gate registry."""
    profile = load_committed_repository_profile(root, tree_ref)
    registry_path = profile.declaration.proof.gate_registry if profile.declaration else None
    declaration, _profile = compile_gate_declaration(
        profile,
        gate_registry_source=_material(root, tree_ref, registry_path) if registry_path else None,
    )
    return declaration


def resolve_gate_policy(
    root: Path | None = None,
    *,
    tree_ref: str | None = None,
    gate_ids: tuple[str, ...] = (),
    product_gate_ids: tuple[str, ...] = (),
    full: bool = False,
    acceptance_purpose: AcceptancePurpose = "repository",
) -> ResolvedGatePolicy:
    """Observe repository materials and compile one content-bound gate policy."""
    return _resolve_policies(
        root, tree_ref, gate_ids, (full,), acceptance_purpose, product_gate_ids
    )[0]


def resolve_proof_policies(
    root: Path, *, tree_ref: str, acceptance_purpose: AcceptancePurpose = "repository"
) -> tuple[tuple[str, ResolvedGatePolicy], ...]:
    """Compile both proof floors from one fresh observation of their combined inputs."""
    return tuple(
        zip(
            ("full", "default"),
            _resolve_policies(root, tree_ref, (), (True, False), acceptance_purpose),
            strict=True,
        )
    )


def _resolve_policies(
    root: Path | None,
    tree_ref: str | None,
    gate_ids: tuple[str, ...],
    floors: tuple[bool, ...],
    acceptance_purpose: AcceptancePurpose,
    product_gate_ids: tuple[str, ...] = (),
) -> tuple[ResolvedGatePolicy, ...]:
    """Share material observation only within this requested policy compilation."""
    if root is None:
        return tuple(
            compile_gate_policy(
                gate_ids=gate_ids,
                product_gate_ids=product_gate_ids,
                full=full,
                acceptance_purpose=acceptance_purpose,
            )
            for full in floors
        )
    profile = (
        load_committed_repository_profile(root, tree_ref)
        if tree_ref is not None
        else load_repository_profile(root)
    )
    registry_path = (
        profile.declaration.proof.gate_registry if profile.declaration is not None else None
    )
    registry_source = _material(root, tree_ref, registry_path) if registry_path else None
    entries = _repository_material_entries(root, tree_ref) if tree_ref is not None else None
    repository_paths = tuple(entries) if entries is not None else _repository_paths(root, tree_ref)
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
            product_gate_ids=product_gate_ids,
            full=full,
            acceptance_purpose=acceptance_purpose,
        )
        for full in floors
    )
    contracts = profile.declaration.proof.source_contracts if profile.declaration else ()
    selected = tuple(gate for policy in initial for gate in policy.gates)
    if contracts and entries is None:
        entries = _repository_material_entries(root, tree_ref)
    materials = _materials(
        root,
        tree_ref,
        source_paths_for_gates(
            selected, repository_paths=repository_paths, source_contracts=contracts
        ),
        entries=entries,
        regular_only=bool(contracts),
    )
    try:
        expanded = source_paths_for_gates(
            selected,
            repository_paths=repository_paths,
            source_contracts=contracts,
            source_materials=materials,
        )
    except (ValueError, UnicodeError):
        expanded = ()  # Final native binding reports the invalid source relationship.
    materials.update(
        _materials(
            root,
            tree_ref,
            tuple(relative for relative in expanded if relative not in materials),
            entries=entries,
            regular_only=bool(contracts),
        )
    )
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
            product_gate_ids=product_gate_ids,
            full=full,
            acceptance_purpose=acceptance_purpose,
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


def _repository_material_entries(root: Path, tree_ref: str | None) -> dict[str, tuple[str, str]]:
    """Observe paths, modes and object identities together from one exact native tree or index."""
    arguments = ("ls-tree", "-r", "-z", tree_ref) if tree_ref else ("ls-files", "--stage", "-z")
    result = run_git(root, *arguments, check=True, text=False, observation=True)
    entries: dict[str, tuple[str, str]] = {}
    for record in result.stdout.split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, middle, last = metadata.split()
            if tree_ref is not None or last == b"0":
                object_id = last if tree_ref is not None else middle
                entries[path.decode("utf-8")] = (mode.decode("ascii"), object_id.decode("ascii"))
    return entries


def _materials(
    root: Path,
    tree_ref: str | None,
    paths: tuple[str, ...],
    *,
    entries: dict[str, tuple[str, str]] | None,
    regular_only: bool,
) -> dict[str, bytes | None]:
    """Acquire selected committed bytes in one fresh typed batch, sharing identical blobs."""
    materials: dict[str, bytes | None] = {}
    objects: dict[str, str] = {}
    for relative in paths:
        if relative.startswith(PRODUCT_PROVIDER_SOURCE):
            materials[relative] = _material(root, None, relative)
            continue
        mode, object_id = entries.get(relative, ("", "")) if entries is not None else ("", "")
        if regular_only and mode not in {"100644", "100755"}:
            materials[relative] = None
        elif tree_ref is None or mode not in {"100644", "100755", "120000"}:
            materials[relative] = _material(root, tree_ref, relative)
        else:
            materials[relative] = None
            if object_id:
                objects[relative] = object_id
    object_ids = tuple(dict.fromkeys(objects.values()))
    blobs = dict(zip(object_ids, read_objects(root, object_ids), strict=True))
    materials.update((relative, blobs[object_id]) for relative, object_id in objects.items())
    return materials


def _material(root: Path, tree_ref: str | None, relative: str) -> bytes | None:
    if relative.startswith(PRODUCT_PROVIDER_SOURCE):
        package = Path(ethos.__file__).resolve().parent
        path = package / relative.removeprefix(PRODUCT_PROVIDER_SOURCE)
        return path.read_bytes() if path.is_file() and not path.is_symlink() else None
    if tree_ref is not None:
        observed = run_git(
            root, "show", f"{tree_ref}:{relative}", check=False, text=False, observation=True
        )
        return observed.stdout if observed.returncode == 0 else None
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


def observe_quality_subjects(
    root: Path, *, expected_tree: str = "", language: str = ""
) -> tuple[str, tuple[CodeSubject, ...]]:
    """Bind observed code subjects to the exact committed source tree."""
    head = current_tracked_head(root)
    if not head:
        message = "source_head_missing"
        raise ValueError(message)
    paths = _repository_paths(root, head)
    profile = load_committed_repository_profile(root, head)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    source_kinds = profile.declaration.proof.source_kinds if profile.declaration else {}
    subjects = observed_code_subjects(
        paths,
        script_paths=_repository_script_paths(root, head, paths),
        roles=dict(_repository_carrier_roles(root, head, paths)),
        source_kinds=source_kinds,
    )
    if language:
        subjects = tuple(subject for subject in subjects if subject.language == language)
        if not subjects:
            message = f"{language}_sources_missing"
            raise ValueError(message)
    if gaps := source_binding_gaps(subjects):
        raise ValueError(gaps[0])
    if any(not (root / subject.path).is_file() for subject in subjects):
        message = "code_source_unavailable"
        raise ValueError(message)
    if (
        subjects
        and run_git(
            root,
            "diff",
            "--quiet",
            head,
            "--",
            *(subject.path for subject in subjects),
            check=False,
        ).returncode
    ):
        message = "code_source_changed"
        raise ValueError(message)
    tree = current_tree(root, head)
    if expected_tree and expected_tree != tree:
        message = "code_source_changed"
        raise ValueError(message)
    return tree, subjects
