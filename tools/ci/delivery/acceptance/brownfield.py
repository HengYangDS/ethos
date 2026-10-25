"""Installed brownfield adoption conformance without source-checkout authority."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.mutation.carrier_edit import apply_carrier_edits
from ethos.adapters.repo.dirty.change_provenance import index_content_sha256
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import LeaseRow
from ethos.adapters.store.state.lease.projection import lease_row
from ethos.adapters.store.state.lease.projection import lease_rows
from ethos.adapters.store.state.schema import state_database
from ethos.adapters.store.state.schema import state_schema_report
from ethos.repository.paradigm.repair import CarrierEdit
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


def prove_brownfield(
    executable: Path,
    work: Path,
    *,
    environment: Mapping[str, str],
    run: Callable[..., str],
) -> dict[str, object]:
    """Add only two bindings to an authored Git repository."""
    git = shutil.which("git", path=environment.get("PATH"))
    if git is None:
        message = "installed_brownfield_git_unavailable"
        raise RuntimeError(message)
    root = work / "brownfield-adopter"
    env = dict(environment)
    run(git, "init", "--quiet", "--initial-branch=dev", str(root), cwd=work)
    for key, value in (
        ("user.name", "Brownfield Contributor"),
        ("user.email", "brownfield@example.invalid"),
        ("commit.gpgsign", "false"),
    ):
        run(git, "config", key, value, cwd=root)
    authored = {
        "README.md": b"# Existing project\n",
        "domain/logic.txt": b"authored domain content\n",
    }
    for relative, content in authored.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    run(git, "add", "--", *authored, cwd=root)
    run(git, "commit", "--quiet", "-m", "chore: authored base", cwd=root)
    head = run(git, "rev-parse", "HEAD", cwd=root, env=env)
    command = (str(executable), "adopt", "--root", str(root))
    code, preview, _detail = invoke(root, (*command, "--json"), environment=environment)
    data = preview.get("data")
    planned = [".ethos/profile.toml", "openspec/config.yaml"]
    preview_preserved = (
        run(git, "rev-parse", "HEAD", cwd=root, env=env) == head
        and all((root / relative).read_bytes() == content for relative, content in authored.items())
        and not any((root / relative).exists() for relative in planned)
        and not run(git, "status", "--porcelain", "--untracked-files=all", cwd=root, env=env)
    )
    if (
        code
        or preview.get("verdict") != "pass"
        or not isinstance(data, dict)
        or data.get("planned_files") != planned
        or not isinstance(data.get("plan_digest"), str)
        or not preview_preserved
    ):
        message = "installed_brownfield_preview_invalid"
        raise RuntimeError(message)
    code, applied, _detail = invoke(
        root,
        (
            *command,
            "--apply",
            "--authorize",
            "--expect-head",
            head,
            "--expect-plan-digest",
            data["plan_digest"],
            "--json",
        ),
        environment=environment,
    )
    if code or applied.get("verdict") != "pass":
        message = "installed_brownfield_apply_invalid"
        raise RuntimeError(message)
    observed_status = run(
        git, "status", "--porcelain", "--untracked-files=all", cwd=root, env=env
    ).splitlines()
    preserved = (
        run(git, "rev-parse", "HEAD", cwd=root, env=env) == head
        and all((root / relative).read_bytes() == content for relative, content in authored.items())
        and observed_status == [f"?? {relative}" for relative in planned]
    )
    if not preserved:
        message = "installed_brownfield_authored_content_changed"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "authored_content_preserved": True,
        "planned_files": planned,
    }


@dataclass(frozen=True, slots=True)
class RetainedRepository:
    """Immutable authored checkout state and its registered repository family."""

    head: str
    configuration: tuple[str, ...]
    schema: tuple[str, ...]
    leases: tuple[LeaseRow, ...]
    files_sha256: tuple[tuple[str, str | None], ...]
    file_modes: tuple[tuple[str, int | None], ...]
    index_sha256: str
    working_state: str
    worktree_configuration: tuple[str, ...]
    worktree_registration: str = ""
    linked_worktrees: tuple[tuple[str, RetainedRepository], ...] = ()


def seed_retained_state(
    repository: Path,
    *,
    python: Path,
    environment: Mapping[str, str],
) -> Path:
    """Admit one leased fixture through the installed owner before authoring dirty state."""
    authored = repository / "retained-user-data.txt"
    if authored.exists() or authored.is_symlink():
        message = "package_upgrade_retained_fixture_occupied"
        raise ValueError(message)
    run_git(repository, "ls-files", "--error-unmatch", "--", "README.md")
    holder = "agent:test:package-only:retained"
    code, started, detail = invoke(
        repository,
        (
            str(python),
            "-B",
            "-I",
            "-m",
            "ethos.cli",
            "lane",
            "start",
            "retained-upgrade-fixture",
            "--holder-ref",
            holder,
            "--root",
            str(repository),
            "--apply",
            "--json",
        ),
        environment={**environment, "ETHOS_ACTOR": holder},
    )
    data = started.get("data")
    if code or started.get("verdict") != "pass" or not isinstance(data, dict):
        message = f"package_upgrade_retained_lane_failed:{detail}"
        raise RuntimeError(message)
    if not isinstance(data.get("path"), str):
        message = "package_upgrade_retained_lane_path_missing"
        raise TypeError(message)
    lane = Path(data["path"])
    run_git(repository, "config", "extensions.worktreeConfig", "true")
    run_git(lane, "config", "--worktree", "retained.fixture", "user-owned configuration")
    authored.write_bytes(b"User-owned state: preserve\n")
    indexed = lane / "retained-index.txt"
    indexed.write_bytes(b"Retained staged bytes\n")
    if os.name != "nt":
        indexed.chmod(0o755)
    run_git(lane, "add", "--", indexed.name)
    run_git(lane, "update-index", "--chmod=+x", "--", indexed.name)
    indexed.write_bytes(b"Retained working bytes\n")
    (lane / "README.md").unlink()
    (lane / "retained-untracked.txt").write_bytes(b"Retained untracked user bytes\n")
    return lane


def retained_repository(repository: Path) -> RetainedRepository:
    """Observe native common state and every linked checkout without caching authority."""
    schema = state_schema_report(repository)
    rows = tuple(lease_row(row) for row in lease_rows(state_database(repository)))
    columns = schema["observed_columns"]
    if schema["observed_state"] != "current" or not isinstance(columns, list) or not rows:
        message = "package_upgrade_retained_state_missing"
        raise ValueError(message)
    configuration = _retained_configuration(repository, "--local")
    declared_columns = tuple(str(column) for column in columns)
    registration = run_git(repository, "worktree", "list", "--porcelain", "-z").stdout
    paths = tuple(
        Path(entry.removeprefix("worktree "))
        for entry in registration.split("\0")
        if entry.startswith("worktree ")
    )
    linked = tuple(
        (str(path), _retained_checkout(path, configuration, declared_columns, rows))
        for path in paths
        if path.resolve() != repository.resolve()
    )
    observed = _retained_checkout(repository, configuration, declared_columns, rows)
    if run_git(repository, "worktree", "list", "--porcelain", "-z").stdout != registration:
        message = "package_upgrade_retained_worktrees_changed"
        raise ValueError(message)
    return replace(observed, worktree_registration=registration, linked_worktrees=linked)


def prove_retained_authoring(
    lane: Path, *, python: Path, environment: Mapping[str, str]
) -> dict[str, object]:
    """Migrate real retained identities, preserve intent and write through installed admission."""
    before = retained_repository(lane)
    [lease] = before.leases
    source = run_git(lane, "branch", "--show-current").stdout.strip()
    if not source.startswith(("task/", "work/")) or lease.lane_ref != source:
        message = "package_retained_legacy_topic_missing"
        raise RuntimeError(message)
    target = "work/" + source.partition("/")[2]
    env = {**environment, "ETHOS_ACTOR": lease.holder_ref}
    env.pop("ETHOS_CHANGE", None)
    prefix = (str(python), "-B", "-I", "-m", "ethos.cli")
    repair = (*prefix, "lane", "repair-paradigm", "--root", str(lane))
    if source != target:
        for options, state in (((), "ready_to_rename"), (("--apply",), "topic_identity_migrated")):
            code, report, detail = invoke(lane, (*repair, *options, "--json"), environment=env)
            if code or (report.get("verdict"), report.get("state")) != ("pass", state):
                message = f"package_retained_topic_migration_failed:{detail}"
                raise RuntimeError(message)
            if not options and retained_repository(lane) != before:
                message = "package_retained_topic_preview_mutated"
                raise RuntimeError(message)
    rows = (replace(lease, lane_ref=target, generation=lease.generation + (source != target)),)
    expected = replace(
        before,
        leases=rows,
        worktree_registration=before.worktree_registration.replace(
            f"branch refs/heads/{source}\0", f"branch refs/heads/{target}\0"
        ),
        linked_worktrees=tuple(
            (path, replace(checkout, leases=rows)) for path, checkout in before.linked_worktrees
        ),
    )
    if retained_repository(lane) != expected:
        message = "package_retained_topic_state_changed"
        raise RuntimeError(message)
    change = _prove_retained_change(lane, prefix, environment=env)
    return {
        **change,
        "source_topic": source,
        "target_topic": target,
        "lease_generation": rows[0].generation,
        "topic_migration": "migrated" if source != target else "not_required",
    }


def _prove_retained_change(
    lane: Path, prefix: tuple[str, ...], *, environment: Mapping[str, str]
) -> dict[str, object]:
    """Qualify one native Change move independently of topic-renaming authority."""
    before = retained_repository(lane)
    env = dict(environment)
    old, new = "smoke-change-20261008", "smoke-change"
    source_root, target_root = (f"openspec/changes/{name}" for name in (old, new))
    originals = {
        path.relative_to(lane / source_root).as_posix(): (path.read_bytes(), path.stat().st_mode)
        for path in (lane / source_root).rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    edits = tuple(
        edit
        for relative, (content, _mode) in originals.items()
        for edit in (
            CarrierEdit(f"{source_root}/{relative}", content.decode(), None),
            CarrierEdit(f"{target_root}/{relative}", None, content.decode()),
        )
    )
    preview = apply_carrier_edits(root=lane, edits=edits)
    if preview["verdict"] != "pass":
        message = f"package_retained_change_patch_unavailable:{preview['required_gaps']}"
        raise RuntimeError(message)
    patch = str(preview["patch"])
    paths = tuple(edit.path for edit in edits)
    patch_file = lane.parent / "retained-change.patch"
    patch_file.write_text(patch, encoding="utf-8", newline="\n")
    request = (
        *prefix,
        "lane",
        "prewrite",
        *paths,
        "--patch",
        str(patch_file),
        "--root",
        str(lane),
        "--editor-root",
        str(lane),
        "--require-editor-root",
        "--json",
    )
    collision = lane / target_root / "proposal.md"
    collision.parent.mkdir()
    collision.write_bytes(b"Existing independent intent\n")
    occupied = retained_repository(lane)
    try:
        _code, report, detail = invoke(lane, request, environment=env)
        if report.get("verdict") != "block" or retained_repository(lane) != occupied:
            message = f"package_retained_change_collision_not_preserved:{detail}"
            raise RuntimeError(message)
    finally:
        collision.unlink()
        collision.parent.rmdir()
    code, report, detail = invoke(lane, request, environment=env)
    if code or report.get("verdict") != "pass" or retained_repository(lane) != before:
        message = f"package_retained_change_prewrite_failed:{detail}"
        raise RuntimeError(message)
    indexed = sorted(
        entry.replace(f"\t{source_root}/", f"\t{target_root}/", 1)
        for entry in run_git(lane, "ls-files", "--stage", "-z").stdout.split("\0")
        if entry
    )
    run_git(lane, "apply", "--index", "-", stdin=patch, env=env)
    run_git(
        lane,
        "commit",
        "--only",
        "-m",
        "fix: migrate retained change identity",
        "--",
        *paths,
        env=env,
    )
    run_git(lane, "verify-commit", "HEAD", env=env)
    if (
        (lane / source_root).exists()
        or indexed
        != sorted(
            entry
            for entry in run_git(lane, "ls-files", "--stage", "-z").stdout.split("\0")
            if entry
        )
        or originals
        != {
            relative: (
                (lane / target_root / relative).read_bytes(),
                (lane / target_root / relative).stat().st_mode,
            )
            for relative in originals
        }
    ):
        message = "package_retained_change_identity_changed_intent"
        raise RuntimeError(message)
    after = retained_repository(lane)
    expected = replace(
        before,
        head=after.head,
        index_sha256=after.index_sha256,
        files_sha256=tuple(
            sorted(
                (
                    name.replace(source_root, target_root, 1)
                    if name.startswith(source_root + "/")
                    else name,
                    value,
                )
                for name, value in before.files_sha256
            )
        ),
        file_modes=tuple(
            sorted(
                (
                    name.replace(source_root, target_root, 1)
                    if name.startswith(source_root + "/")
                    else name,
                    value,
                )
                for name, value in before.file_modes
            )
        ),
        worktree_registration=before.worktree_registration.replace(
            f"worktree {lane.as_posix()}\0HEAD {before.head}\0",
            f"worktree {lane.as_posix()}\0HEAD {after.head}\0",
        ),
    )
    if after != expected:
        message = "package_retained_change_modified_unrelated_state"
        raise RuntimeError(message)
    _prove_renewed_authoring(lane, prefix, new, environment=env)
    if retained_repository(lane) != expected:
        message = "package_retained_authoring_restore_changed_state"
        raise RuntimeError(message)
    patch_file.unlink()
    return {
        "state": "passed",
        "source_change": old,
        "target_change": new,
        "tasks_sha256": hashlib.sha256(originals["tasks.md"][0]).hexdigest(),
        "collision_preserved": True,
        "unrelated_index_preserved": True,
        "renewed_authoring": "admitted_write_and_restore",
    }


def _prove_renewed_authoring(
    lane: Path, prefix: tuple[str, ...], change: str, *, environment: Mapping[str, str]
) -> None:
    """Exercise new writing and exact restoration through separate fresh admissions."""
    target_root = f"openspec/changes/{change}"
    proposal = lane / target_root / "proposal.md"
    content = proposal.read_bytes()
    write = (
        *prefix,
        "lane",
        "prewrite",
        proposal.relative_to(lane).as_posix(),
        "--root",
        str(lane),
        "--editor-root",
        str(lane),
        "--require-editor-root",
        "--json",
    )
    env = {**environment, "ETHOS_CHANGE": change}
    for postimage in (content + b"\nRetained authoring acceptance exercised.\n", content):
        code, report, detail = invoke(lane, write, environment=env)
        if code or report.get("verdict") != "pass":
            message = f"package_retained_renewed_authoring_failed:{detail}"
            raise RuntimeError(message)
        proposal.write_bytes(postimage)
        if proposal.read_bytes() != postimage:
            message = "package_retained_renewed_authoring_readback_failed"
            raise RuntimeError(message)


def _retained_configuration(repository: Path, scope: str) -> tuple[str, ...]:
    result = run_git(repository, "config", scope, "--null", "--get-regexp", ".", check=False)
    if result.returncode == 1 and not result.stdout:
        return ()
    result.check_returncode()
    configuration = result.stdout
    return tuple(
        entry
        for entry in configuration.split("\0")
        if entry and not entry.startswith("core.hookspath\n")
    )


def _retained_checkout(
    repository: Path,
    configuration: tuple[str, ...],
    columns: tuple[str, ...],
    rows: tuple[LeaseRow, ...],
) -> RetainedRepository:
    files = run_git(
        repository, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ).stdout
    entries = tuple(
        (name, *_retained_file(repository / name))
        for name in sorted(set(files.split("\0")))
        if name
    )
    return RetainedRepository(
        head=run_git(repository, "rev-parse", "HEAD").stdout.strip(),
        configuration=configuration,
        schema=columns,
        leases=rows,
        files_sha256=tuple((name, digest) for name, digest, _mode in entries),
        file_modes=tuple((name, mode) for name, _digest, mode in entries),
        index_sha256=index_content_sha256(repository),
        working_state=run_git(
            repository, "status", "--porcelain=v1", "--untracked-files=all", "-z"
        ).stdout,
        worktree_configuration=_retained_configuration(repository, "--worktree"),
    )


def _retained_file(path: Path) -> tuple[str | None, int | None]:
    try:
        state = path.lstat()
    except FileNotFoundError:
        return None, None
    if stat.S_ISLNK(state.st_mode):
        # Preserve raw target spelling; Path.readlink normalizes its returned path.
        content = os.fsencode(os.readlink(path, dir_fd=None))
    elif stat.S_ISREG(state.st_mode):
        content = path.read_bytes()
    else:
        message = "package_upgrade_retained_file_invalid"
        raise ValueError(message)
    return hashlib.sha256(content).hexdigest(), stat.S_IMODE(state.st_mode)
