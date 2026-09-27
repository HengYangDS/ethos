"""Installed brownfield adoption conformance without source-checkout authority."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

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
    return {"state": "passed", "authored_content_preserved": True, "planned_files": planned}
