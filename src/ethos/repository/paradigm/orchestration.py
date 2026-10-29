"""Native orchestration of the repository paradigm.

Gates and CI steps run native tool commands or toolchain-owner tasks. A gate or step
that runs a tracked repository script is shell orchestration; a step, or a gate's
shell interpreter argument, that holds a shell program instead of one command is
inline shell. One command may continue its arguments over several lines, redirect its
output and quote any text; a Forge expression is resolved before the shell runs.

A CI step may keep a shell program only as an official installer or operating-system
glue that the retention record names by Forge file, job and the SHA-256 of its parsed
text. Each job a record lists must still carry that text; review, not the paradigm,
judges whether the record's evidence shows the glue is necessary.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import tomllib
from typing import TYPE_CHECKING
from typing import NamedTuple

import yaml

from ethos.contracts.gates import GateRegistryDeclaration
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.paradigm.pipelines import forge_pipeline_files
from ethos.repository.paradigm.scripts import is_script
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm
    from ethos.contracts.paradigm.declaration import StepRetention

_CONTROL_WORDS = frozenset({"case", "for", "if", "select", "until", "while"})
_SHELLS = frozenset({"bash", "cmd", "dash", "ksh", "powershell", "pwsh", "sh", "zsh"})
_SHELL_PROGRAM_FLAGS = frozenset({"-c", "-Command", "/c", "/C"})
_GITLAB_STEPS = ("before_script", "script", "after_script")
_RECORD_FIELDS = (
    "file",
    "jobs",
    "sha256",
    "class",
    "owner",
    "reason",
    "platforms",
    "evidence",
)
_DIGEST = re.compile(r"[0-9a-f]{64}")


class CiStep(NamedTuple):
    """One CI step: the carrier naming its position, its job and the text the Forge runs."""

    carrier: str
    job: str
    command: str


class _RetainedStep(NamedTuple):
    """One complete retention record entry, by its position in the record."""

    position: int
    file: str
    jobs: tuple[str, ...]
    sha256: str


class _ForgeLoader(yaml.SafeLoader):
    """Read Forge YAML, keeping a tagged node such as GitLab's !reference unread."""


_ForgeLoader.add_multi_constructor("!", lambda _loader, _suffix, _node: None)


def orchestration_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report CI steps and gates that run repository scripts or hold unrecorded programs."""
    scripts = sorted(path for path in tracked if is_script(paradigm, root, path))
    retention = paradigm.pipelines.retention
    records, record_gaps = _retained_steps(retention, root, tracked)
    admitted = {(entry.file, job, entry.sha256) for entry in records for job in entry.jobs}
    matched: set[tuple[str, str, str]] = set()
    repair = _inline_repair(retention.record)
    for forge, path in forge_pipeline_files(paradigm, tracked):
        for step in ci_steps(forge, path, tracked_text(root, path, tracked) or ""):
            script = next((entry for entry in scripts if entry in step.command), "")
            key = (path, step.job, _text_digest(step.command))
            # Retention owns a step as a whole by file, job and digest, whatever shape it reads as.
            if not script and key in admitted:
                matched.add(key)
                continue
            yield from _command_gaps(
                step.carrier, script, inline=inline_shell(step.command), repair=repair
            )
    for carrier, command in _gate_commands(paradigm, root, tracked):
        joined = " ".join(command)
        script = next((entry for entry in scripts if entry in joined), "")
        yield from _command_gaps(carrier, script, inline=_shell_program(command), repair=repair)
    yield from record_gaps
    for entry in records:
        for job in entry.jobs:
            if (entry.file, job, entry.sha256) not in matched:
                yield ParadigmGap(
                    "retained-step",
                    f"{retention.record}:step[{entry.position}].{job}",
                    f"re-record the edited step after re-justifying it, or remove {job} from "
                    "this record when the job no longer needs a retained shell program",
                )


def ci_steps(forge: str, path: str, text: str) -> list[CiStep]:
    """Return each CI step of one Forge's pipeline file with its job and position."""
    reader = _STEP_READERS.get(forge)
    try:
        document = yaml.load(text, Loader=_ForgeLoader)
    except yaml.YAMLError:
        return []
    if reader is None or not isinstance(document, dict):
        return []
    return list(reader(path, document))


def _inline_repair(record: str) -> str:
    return (
        "make the step invoke one native command or toolchain-owner task; move a sequence into a "
        "task, environment into the Forge's variables and a directory change into its "
        "working-directory key; record only an official installer or necessary operating-system "
        f"glue in {record}"
    )


def _text_digest(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def retained_step_keys(
    paradigm: RepositoryParadigm, files: Mapping[str, str]
) -> frozenset[tuple[str, str, str]]:
    """Return the Forge file, job and text digest of each step a complete record entry keeps."""
    retention = paradigm.pipelines.retention
    if retention.record not in files:
        return frozenset()
    records, _gaps = _record_entries(retention, files[retention.record])
    return frozenset((entry.file, job, entry.sha256) for entry in records for job in entry.jobs)


def retained_step_texts(
    paradigm: RepositoryParadigm, path: str, text: str, keys: frozenset[tuple[str, str, str]]
) -> frozenset[str]:
    """Return the step texts of one pipeline file that retention keeps in every job running them."""
    forge = next((forge for forge, _path in forge_pipeline_files(paradigm, (path,))), None)
    if not keys or forge is None:
        return frozenset()
    retained: set[str] = set()
    unretained: set[str] = set()
    for step in ci_steps(forge, path, text):
        key = (path, step.job, _text_digest(step.command))
        (retained if key in keys else unretained).add(step.command)
    return frozenset(retained - unretained)


def _retained_steps(
    retention: StepRetention, root: Path, tracked: frozenset[str]
) -> tuple[list[_RetainedStep], list[ParadigmGap]]:
    """Read the complete record entries and report the record or any entry that is not."""
    if retention.record not in tracked:
        return [], []
    return _record_entries(retention, tracked_text(root, retention.record, tracked))


def _record_entries(
    retention: StepRetention, text: str | None
) -> tuple[list[_RetainedStep], list[ParadigmGap]]:
    """Parse the record's entries, reporting an unreadable record or any incomplete entry."""
    try:
        document = tomllib.loads(text) if text is not None else None
    except tomllib.TOMLDecodeError:
        document = None
    entries = document.get("step") if isinstance(document, dict) else None
    if not isinstance(document, dict) or set(document) - {"step"} or not isinstance(entries, list):
        unreadable = ParadigmGap(
            "retained-step",
            retention.record,
            f"write {retention.record} as TOML [[step]] tables",
        )
        return [], [unreadable]
    records: list[_RetainedStep] = []
    gaps: list[ParadigmGap] = []
    for index, entry in enumerate(entries):
        record = _retained_step(retention, index, entry)
        if record is None:
            gaps.append(
                ParadigmGap(
                    "retained-step",
                    f"{retention.record}:step[{index}]",
                    f"give each [[step]] exactly {', '.join(_RECORD_FIELDS[:-1])} and "
                    f"{_RECORD_FIELDS[-1]}: distinct jobs and platforms, a class from "
                    f"{', '.join(retention.classes)}, platforms from "
                    f"{', '.join(retention.platforms)}, and the lowercase SHA-256 of the step text",
                )
            )
        else:
            records.append(record)
    return records, gaps


def _retained_step(retention: StepRetention, index: int, entry: object) -> _RetainedStep | None:
    """Return one entry when it is complete and uses catalogued values, otherwise None."""
    if not isinstance(entry, dict) or tuple(sorted(entry)) != tuple(sorted(_RECORD_FIELDS)):
        return None
    texts = [entry[name] for name in ("file", "owner", "reason", "evidence")]
    if not all(isinstance(text, str) and text.strip() for text in texts):
        return None
    jobs, platforms = entry["jobs"], entry["platforms"]
    if not (
        _distinct_names(jobs)
        and _distinct_names(platforms)
        and set(platforms) <= set(retention.platforms)
        and entry["class"] in retention.classes
        and isinstance(entry["sha256"], str)
        and _DIGEST.fullmatch(entry["sha256"])
    ):
        return None
    return _RetainedStep(index, entry["file"], tuple(jobs), entry["sha256"])


def _distinct_names(values: object) -> bool:
    return (
        isinstance(values, list)
        and bool(values)
        and all(isinstance(value, str) and value.strip() for value in values)
        and len(set(values)) == len(values)
    )


def inline_shell(command: str) -> bool:
    """Return whether one step's text is a shell program rather than one command."""
    text = command.replace("\\\n", " ")
    quote = ""
    index = 0
    while index < len(text):
        character = text[index]
        if quote == "'":
            quote = "" if character == "'" else quote
        elif character == "\\":
            index += 1
        elif character == "`" or text.startswith("$(", index):
            return True
        elif quote:
            quote = "" if character == '"' else quote
        elif character in "'\"":
            quote = character
        elif (skipped := _skipped(text, index)) is not None:
            index = skipped
        elif _separates(text, index):
            return True
        index += 1
    first = text.split(maxsplit=1)
    return bool(first) and first[0] in _CONTROL_WORDS


def _skipped(text: str, index: int) -> int | None:
    """Return where an unquoted Forge expression or comment ends, if one starts here."""
    if text.startswith("${{", index):
        end = text.find("}}", index)
        return len(text) if end < 0 else end + 1
    if text[index] == "#" and (index == 0 or text[index - 1].isspace()):
        end = text.find("\n", index)
        return len(text) if end < 0 else end - 1
    return None


def _separates(text: str, index: int) -> bool:
    """Return whether an unquoted character separates, chains or backgrounds commands."""
    character = text[index]
    if character in ";|" or (character == "&" and _background(text, index)):
        return True
    return character == "\n" and bool(text[index + 1 :].strip())


def _background(command: str, index: int) -> bool:
    """Return whether an ampersand chains or backgrounds commands, not redirects output."""
    before, after = command[index - 1 : index], command[index + 1 : index + 2]
    return after == "&" or (before not in "<>" and after != ">")


def _command_gaps(carrier: str, script: str, *, inline: bool, repair: str) -> Iterator[ParadigmGap]:
    if script:
        yield ParadigmGap(
            "shell-orchestration",
            carrier,
            f"replace {script} with a native command or toolchain-owner task",
        )
    elif inline:
        yield ParadigmGap("inline-shell", carrier, repair)


def _github_steps(path: str, document: dict[object, object]) -> Iterator[CiStep]:
    jobs = document.get("jobs")
    for job, body in jobs.items() if isinstance(jobs, dict) else ():
        steps = body.get("steps") if isinstance(body, dict) else None
        for index, step in enumerate(steps if isinstance(steps, list) else ()):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield CiStep(f"{path}:jobs.{job}.steps[{index}]", str(job), step["run"])


def _gitlab_steps(path: str, document: dict[object, object]) -> Iterator[CiStep]:
    for job, body in document.items():
        if not isinstance(body, dict):
            continue
        for key in _GITLAB_STEPS:
            entries = body.get(key)
            listed = [entries] if isinstance(entries, str) else entries
            for index, entry in enumerate(listed if isinstance(listed, list) else ()):
                if isinstance(entry, str):
                    yield CiStep(f"{path}:{job}.{key}[{index}]", str(job), entry)


_STEP_READERS = {"github": _github_steps, "gitlab": _gitlab_steps}


def _gate_commands(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[tuple[str, tuple[str, ...]]]:
    """Return the command of every declared gate, from the profile or its gate registry."""
    declaration = load_repository_profile(root).declaration
    proof = declaration.proof if declaration else None
    if proof is None:
        return
    profile = f"{paradigm.binding.root}/profile.toml"
    for gate in proof.gates:
        yield f"{profile}:proof.gates.{gate.id}", tuple(gate.command)
    registry = proof.gate_registry
    text = tracked_text(root, registry, tracked) if registry else None
    if text is None:
        return
    try:
        declared = GateRegistryDeclaration.model_validate(tomllib.loads(text))
    except ValueError:
        return  # The gate registry owner reports an unreadable or invalid registry.
    for gate in declared.gates:
        yield f"{registry}:gates.{gate.id}", tuple(gate.command)


def _shell_program(command: tuple[str, ...]) -> bool:
    """Return whether a gate hands a program to a shell interpreter."""
    return (
        bool(command)
        and posixpath.basename(command[0]) in _SHELLS
        and any(word in _SHELL_PROGRAM_FLAGS for word in command[1:])
    )
