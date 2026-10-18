"""Installed brownfield adoption conformance without source-checkout authority."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import LeaseRow
from ethos.adapters.store.state.lease.projection import lease_row
from ethos.adapters.store.state.lease.projection import lease_rows
from ethos.adapters.store.state.schema import state_database
from ethos.adapters.store.state.schema import state_schema_report
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path


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
    """Selection-independent repository bytes and native Lease semantics."""

    head: str
    configuration: tuple[str, ...]
    schema: tuple[str, ...]
    leases: tuple[LeaseRow, ...]
    files_sha256: tuple[tuple[str, str], ...]
    working_state: str


def seed_retained_state(repository: Path) -> None:
    """Give the disposable brownfield fixture real user bytes and Lease state."""
    authored = repository / "retained-user-data.txt"
    if authored.exists() or authored.is_symlink():
        message = "package_upgrade_retained_fixture_occupied"
        raise ValueError(message)
    authored.write_bytes(b"User-owned state: preserve\n")
    acquire_lease(
        state_database(repository),
        lease=LaneLease(
            lane_ref="work/retained-upgrade-fixture",
            holder_ref=HolderRef.parse("agent:test:package-only:retained"),
            generation=1,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )


def retained_repository(repository: Path) -> RetainedRepository:
    """Read the complete selected fixture without treating hooks as user config."""
    schema = state_schema_report(repository)
    rows = tuple(lease_row(row) for row in lease_rows(state_database(repository)))
    columns = schema["observed_columns"]
    if schema["observed_state"] != "current" or not isinstance(columns, list) or not rows:
        message = "package_upgrade_retained_state_missing"
        raise ValueError(message)
    configuration = run_git(repository, "config", "--local", "--null", "--list").stdout
    files = run_git(
        repository, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ).stdout.split("\0")
    return RetainedRepository(
        head=run_git(repository, "rev-parse", "HEAD").stdout.strip(),
        configuration=tuple(
            entry
            for entry in configuration.split("\0")
            if entry and not entry.startswith("core.hookspath\n")
        ),
        schema=tuple(str(column) for column in columns),
        leases=rows,
        files_sha256=tuple(
            (name, hashlib.sha256((repository / name).read_bytes()).hexdigest())
            for name in sorted(set(files))
            if name
        ),
        working_state=run_git(
            repository, "status", "--porcelain=v1", "--untracked-files=all", "-z"
        ).stdout,
    )
