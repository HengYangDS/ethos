"""The installed pre-commit hook in a clone of the product repository at the candidate head.

The product repository builds its own runtime from its locked environment, so its clone selects
the delivered runtime with `--runtime`, and accepts only the development identity of its accepted
head. Its hook admits a staged edit only in a Work Lane whose lease holder is the invoking actor
and whose paths one Change covers. A release head has no active Change, so the lane stages a new
one beside its edit, and `ETHOS_CHANGE` selects it among any that the head carries.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.repo.runtime.filesystem import runtime_python
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage

if TYPE_CHECKING:
    from collections.abc import Mapping

    from tools.ci.delivery.acceptance.adopter import CommandRunner

_ACTOR = "agent:test:package-only:product-hook"
_CHANGE = "installed-hook-admission"
_REFUSAL = "pre_commit_text_layout:.gitignore:1"
# Each document keeps every section of its official template; otherwise the Change covers only
# the repair of its own documents and the staged edit stays uncovered.
_DOCUMENTS = {
    ".openspec.yaml": "schema: spec-driven\nskip_specs: true\n",
    "proposal.md": """# Proposal

## Why

Admit.

## What Changes

- Nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

None.
""",
    "design.md": """# Design

## Context

Admit.

## Goals / Non-Goals

None.

## Decisions

None.

## Risks / Trade-offs

None.
""",
    "tasks.md": "# Tasks\n\n## 1. Admission\n\n- [ ] 1.1 Admit.\n",
}


@observe_stage("product_hook")
def prove_product_hook(
    runtime: Path,
    source: Path,
    *,
    head: str,
    work: Path,
    environment: Mapping[str, str],
    run: CommandRunner,
    accepted: str = "",
) -> dict[str, object]:
    """Require the hook to admit a conforming edit and refuse a `.gitignore` led by a blank line.

    The accepted branch holds the runtime's source commit, `head` unless named; the candidate and
    its Work Lane start at `head`. The hook runs in the lease holder's committing environment, and
    the runner refuses a failed command with its output, so a refused admission names its gap.
    """
    clone, branch = work / "product", load_repository_paradigm().branch
    python, change = runtime_python(runtime / "python"), f"openspec/changes/{_CHANGE}"
    work.mkdir()
    run("git", "clone", "--quiet", "--shared", "--no-checkout", str(source), str(clone), cwd=work)
    run("git", "checkout", "--quiet", "-B", branch.accepted, accepted or head, cwd=clone)
    candidate = ("-B", branch.candidate, str(work / "candidate"), head)
    run("git", "worktree", "add", "--quiet", *candidate, cwd=clone)
    committing = {**environment, "ETHOS_ACTOR": _ACTOR, "ETHOS_CHANGE": _CHANGE}
    runtime_acceptance.activate_from_runtime(
        python, clone, environment=committing, installed_runtime=runtime
    )
    start = ("lane", "start", _CHANGE, "--holder-ref", _ACTOR, "--root", str(clone), "--apply")
    command = (str(python), *PYTHON_FLAGS, "-m", "ethos.cli", *start, "--json")
    code, started, diagnostic = invoke(clone, command, environment=committing)
    if code or not isinstance(data := started.get("data"), dict):
        message = f"package_product_hook_lane_failed:{diagnostic}"
        raise RuntimeError(message)
    lane = Path(str(data["path"]))
    (lane / change).mkdir(parents=True)
    for name, text in _DOCUMENTS.items():
        (lane / change / name).write_text(text, encoding="utf-8", newline="\n")
    ignore, hook = lane / ".gitignore", ("git", "hook", "run", "pre-commit")
    incumbent = ignore.read_bytes()
    ignore.write_bytes(incumbent + b"/admitted/\n")
    run("git", "add", "--", ".gitignore", change, cwd=lane)
    run(*hook, cwd=lane, env=committing)
    ignore.write_bytes(b"\n" + incumbent)
    run("git", "add", "--", ".gitignore", cwd=lane)
    try:
        run(*hook, cwd=lane, env=committing)
    except RuntimeError as refusal:
        if _REFUSAL not in str(refusal):
            raise
        return {"state": "passed", "head": head, "admitted": True, "refused": _REFUSAL}
    message = "package_product_hook_refusal_missing"
    raise RuntimeError(message)
