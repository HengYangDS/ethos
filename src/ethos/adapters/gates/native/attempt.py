"""Capture declared native output once, preserving source and failed receipts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from stat import S_ISREG
from tempfile import TemporaryDirectory
from time import monotonic
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from ethos.adapters.gates.native.python import PythonRuntime
from ethos.adapters.gates.verification import NativeEvidence
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.materialization.input_resolution import runtime_wheel
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.evidence.observer import ObserverIdentity
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.contracts.gates import Gate
    from ethos.contracts.gates import NativeOutput


def _read_output(directory: Path, name: str) -> bytes:
    """Read one bounded regular output without following links outside the attempt."""
    path = directory / name
    for parent in path.relative_to(directory).parents:
        if (directory / parent).is_symlink():
            msg = "native_output_unsafe"
            raise ValueError(msg)
    before = path.lstat()
    if not S_ISREG(before.st_mode) or before.st_size > 32 * 1024 * 1024:
        msg = "native_output_unsafe"
        raise ValueError(msg)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            msg = "native_output_changed"
            raise ValueError(msg)
        data = stream.read(32 * 1024 * 1024 + 1)
        after = os.fstat(stream.fileno())
    if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        msg = "native_output_changed"
        raise ValueError(msg)
    if len(data) != before.st_size:
        msg = "native_output_changed"
        raise ValueError(msg)
    return data


def _retain(root: Path, execution: NativeExecution) -> str:
    """Use the existing content-addressed store for original reports and output."""
    evidence = execution.evidence
    if evidence is None:
        msg = "native_evidence_missing"
        raise ValueError(msg)
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "execution.json",
            json.dumps(
                {
                    "command": execution.declared_identity,
                    "argv": execution.argv,
                    "exit_code": execution.exit_code,
                    "head": evidence.head,
                    "tree": evidence.tree,
                    "subjects": evidence.subjects,
                    "policy_digest": canonical_json_digest(evidence.gate.to_dict()),
                    "gate": evidence.gate.to_dict(),
                    "output_root": evidence.output_root,
                    "gaps": evidence.gaps,
                    "observer": evidence.observer.to_payload() if evidence.observer else None,
                    "dependency_checks": [
                        output.model_dump(mode="json") for output, _ in evidence.dependency_checks
                    ],
                },
                sort_keys=True,
            ),
        )
        archive.writestr("stdout.txt", execution.stdout)
        archive.writestr("stderr.txt", execution.stderr)
        for index, (_output, content) in enumerate(evidence.dependency_checks):
            archive.writestr(f"dependency-checks/{index}.json", content)
        for output, content in evidence.outputs:
            archive.writestr("reports/" + output.path, content)
    content = payload.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    target = local_state_root(root) / "artifacts" / f"{digest}.zip"
    write_content_addressed(target, content, collision="native_evidence_identity_collision")
    return str(target)


def _capture_outputs(
    root: Path,
    gate: Gate,
    directory: Path,
    observer: ObserverIdentity | None,
    deadline: float,
) -> tuple[list[tuple[NativeOutput, bytes]], list[tuple[NativeOutput, bytes]], list[str]]:
    """Retain declared reports before qualifying the same supplied child."""
    outputs: list[tuple[NativeOutput, bytes]] = []
    checks: list[tuple[NativeOutput, bytes]] = []
    gaps: list[str] = []
    for output in gate.native_outputs:
        try:
            content = _read_output(directory, output.path)
            outputs.append((output, content))
            if output.format == "python-runtime-json":
                runtime = PythonRuntime.model_validate_json(content)
                runtime.require_observer(observer)
                check = runtime.qualify(root, output, deadline=deadline)
                checks.append((output, check))
                runtime.require_floor(root, check)
        except subprocess.TimeoutExpired:
            gaps.append("native_execution_timeout")
        except (OSError, ValueError) as error:
            reason = str(error) if isinstance(error, ValueError) else "native_output_missing"
            gaps.append(f"{reason}:{output.path}")
    return outputs, checks, gaps


def native_attempt(
    root: Path,
    gate: Gate,
    command: tuple[str, ...],
    *,
    timeout: float | None,
    env: Mapping[str, str] | None = None,
    remove_env: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], NativeEvidence]:
    """Bind reports before the sole launch; never select ambient or latest evidence."""
    tree, subjects = observe_quality_subjects(root)
    head = current_tracked_head(root)
    if run_git(root, "diff", "--quiet", head, "--", check=False).returncode:
        msg = "native_source_changed"
        raise ValueError(msg)
    with TemporaryDirectory(prefix="ethos-native-gate-") as temporary:
        directory = Path(temporary)
        argv = tuple(item.replace("{native_output}", str(directory)) for item in command)
        outputs: list[tuple[NativeOutput, bytes]] = []
        gaps: list[str] = []
        checks: list[tuple[NativeOutput, bytes]] = []
        observer = None
        supply_error = ""
        environment = {
            name: value
            for name, value in (env or {}).items()
            if name.casefold()
            not in {
                "ethos_native_output_dir",
                "ethos_native_observer_requirement",
                "ethos_native_observer_runtime_digest",
            }
        } | {"ETHOS_NATIVE_OUTPUT_DIR": str(directory)}
        deadline = monotonic() + (timeout if timeout is not None else 900)
        try:
            if any(output.format == "python-runtime-json" for output in gate.native_outputs):
                selected = current_runtime(Path(git_common_dir(root)))
                wheel = runtime_wheel(selected)
                observer = ObserverIdentity(
                    f"ethos @ {wheel.as_uri()}#sha256={selected.wheel_sha256}",
                    selected.digest,
                    selected.wheel_sha256,
                )
                environment.update(
                    ETHOS_NATIVE_OBSERVER_REQUIREMENT=observer.requirement,
                    ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST=observer.runtime_digest,
                )
        except (OSError, ValueError) as error:
            supply_error = str(error)
            gaps.append(supply_error)
        try:
            if supply_error:
                completed = subprocess.CompletedProcess(argv, 1, "", supply_error)
            else:
                completed = run_command(
                    root,
                    argv,
                    timeout=max(0, deadline - monotonic()) if timeout is not None else None,
                    env=environment,
                    remove_env=(
                        *remove_env,
                        "ETHOS_NATIVE_OUTPUT_DIR",
                        "ETHOS_NATIVE_OBSERVER_REQUIREMENT",
                        "ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST",
                    ),
                )
        except subprocess.TimeoutExpired as error:
            stdout = (
                error.stdout.decode(errors="replace")
                if isinstance(error.stdout, bytes)
                else error.stdout or ""
            )
            stderr = (
                error.stderr.decode(errors="replace")
                if isinstance(error.stderr, bytes)
                else error.stderr or ""
            )
            completed = subprocess.CompletedProcess(argv, 124, stdout, stderr)
            gaps.append("native_execution_timeout")
        if not supply_error:
            outputs, checks, output_gaps = _capture_outputs(
                root, gate, directory, observer, deadline
            )
            gaps.extend(output_gaps)
        try:
            observe_quality_subjects(root, expected_tree=tree)
            if current_tracked_head(root) != head:
                gaps.append("native_source_changed")
            if run_git(root, "diff", "--quiet", head, "--", check=False).returncode:
                gaps.append("native_source_changed")
        except (OSError, ValueError) as error:
            gaps.append(str(error))
        evidence = NativeEvidence(
            gate=gate,
            head=head,
            tree=tree,
            subjects=tuple(subject.path for subject in subjects),
            output_root=str(directory),
            outputs=tuple(outputs),
            gaps=tuple(gaps),
            artifact="",
            dependency_checks=tuple(checks),
            observer=observer,
        )
        return completed, evidence


def retained_execution(execution: NativeExecution) -> NativeExecution:
    """Keep the captured bytes and exact receipt after owned scratch disappears."""
    if execution.evidence is None:
        return execution
    artifact = _retain(execution.cwd, execution)
    return replace(execution, evidence=replace(execution.evidence, artifact=artifact))


def gate_attempt(
    root: Path,
    gate: Gate,
    command: tuple[str, ...],
    *,
    timeout: float | None,
    env: Mapping[str, str] | None = None,
    remove_env: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], NativeEvidence | None]:
    """Run one gate command; declared native outputs come from that same attempt."""
    if gate.native_outputs:
        return native_attempt(root, gate, command, timeout=timeout, env=env, remove_env=remove_env)
    return run_command(root, command, timeout=timeout, env=env, remove_env=remove_env), None


def gate_execution(
    root: Path,
    declared_identity: tuple[str, ...],
    command: tuple[str, ...],
    completed: subprocess.CompletedProcess[str],
    *,
    executable: str,
    evidence: NativeEvidence | None,
) -> NativeExecution:
    """Describe one gate attempt and keep its native evidence beyond owned scratch."""
    return retained_execution(
        NativeExecution(
            declared_identity=declared_identity,
            argv=completed.args if evidence is not None else command,
            cwd=root.resolve(),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            executable=executable,
            evidence=evidence,
        )
    )
