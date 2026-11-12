"""Compose a formed repository's foundation so its first commit passes the repository paradigm.

Formation authors only the carriers that no paradigm repair writes, applies the paradigm's own
repairs, and checks the composed candidate with Git's line endings, as its first proof will.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_attributes import checkout_line_endings
from ethos.adapters.repo.starter.generation import compose_starter
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.parameters import seconds
from ethos.repository.paradigm.repair import paradigm_repair_plan
from ethos.repository.paradigm.report import repository_paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_CONTRIBUTING = """# Contributing

ETHOS governs this repository. Run `ethos status --root . --json` and follow its `next` step;
[AGENTS.md](AGENTS.md) gives agents the same entry. Each change follows an accepted OpenSpec Change
under `openspec/` and lands after its proof passes.
"""
# A task-only owner: mise writes no lock until a tool is selected, which the ETHOS pin adds later.
_TOOLCHAIN = """[settings]
locked = true

[tasks.bootstrap]
description = "Install the locked tools"
run = "mise install --locked"

[tasks.check]
description = "Check the formatting without changing files"
run = "ethos lane format --check --json"

[tasks.fix]
description = "Apply the formatting in a Work Lane; pass --expect-head with the lane head"
run = "ethos lane format --apply --authorize --json"
"""


def git_init_arguments() -> tuple[str, ...]:
    """Initialize a candidate once, so the check and the history agree on its first branch."""
    return ("init", "-q", "--template=", "-b", load_repository_paradigm().branch.accepted)


def write_paradigm_carriers(candidate: Path) -> None:
    """Author what no repair writes, then write the paradigm's own repairs, all with LF."""
    toolchain = next(tool.carrier for tool in load_repository_paradigm().tool if tool.id == "mise")
    _write(candidate, "CONTRIBUTING.md", _CONTRIBUTING)
    _write(candidate, toolchain, _TOOLCHAIN)
    report = repository_paradigm_report(
        candidate, tracked_paths=_files(candidate), line_endings=None
    )
    gaps = [
        ParadigmGap(str(gap.get("obligation")), str(gap.get("carrier")), str(gap.get("repair")))
        for gap in map(string_mapping, object_sequence(report["gaps"]))
    ]
    for edit in paradigm_repair_plan(candidate, gaps).edits:
        if edit.after is None:
            (candidate / edit.path).unlink()
        else:
            _write(candidate, edit.path, edit.after)


def compose_conforming_starter(
    candidate: Path, starter: str, purpose: str
) -> tuple[dict[str, str], dict[str, str], list[str], str, str]:
    """Compose the starter and judge it by the shipped paradigm; a foundation gap refuses.

    The paradigm ships with formation, so a gap in the foundation is a product defect. A domain
    starter reports its gaps until it conforms.
    """
    outputs, starter_outputs, gap, detail = compose_starter(candidate, starter, purpose)
    if gap:
        return outputs, starter_outputs, [], gap, detail
    gaps = paradigm_gaps(candidate, tuple(sorted(outputs)))
    if gaps and starter == "foundation":
        return outputs, starter_outputs, gaps, "formation_starter_paradigm_gap", ", ".join(gaps)
    return outputs, starter_outputs, gaps, "", ""


def paradigm_gaps(candidate: Path, paths: tuple[str, ...]) -> list[str]:
    """Report the composed candidate's paradigm gaps with the line endings Git resolves."""
    initialized = run_git(candidate, *git_init_arguments(), check=False, timeout=seconds("git"))
    if initialized.returncode:
        message = f"formation_git_init_failed: {initialized.stderr.strip()}"
        raise OSError(message)
    report = repository_paradigm_report(
        candidate, tracked_paths=paths, line_endings=checkout_line_endings(candidate, paths)
    )
    return string_sequence(report["required_gaps"])


def _files(candidate: Path) -> tuple[str, ...]:
    """Name the candidate's regular files; it holds no Git metadata yet."""
    return tuple(
        sorted(
            path.relative_to(candidate).as_posix()
            for path in candidate.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(candidate).parts
        )
    )


def _write(candidate: Path, path: str, text: str) -> None:
    target = candidate / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
